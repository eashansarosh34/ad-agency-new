"""
AGENT 02c — Follower Growth Optimizer
=========================================

What this is: Agent 02's exact pause/boost logic, pointed at a different
number. Instead of cost-per-lead, this watches cost-per-Instagram-profile-
visit — the real, legitimate metric behind growing a following (Meta added
native support for optimizing toward this in 2026 under the Engagement
objective; profile visits are the genuine precursor to real follows, not
a vanity proxy for them).

IMPORTANT — read before using:
  The exact field name Meta uses for "profile visit" inside the Insights
  API's actions array is new enough (2026 rollout) that it's worth
  confirming against one real response before trusting this blindly.
  RESULT_ACTION_TYPE below is a best-current-guess, deliberately made
  configurable rather than hardcoded — once you have a real campaign
  running, fetch one real insights response and check actual action_type
  values in the response, then set the env var to match exactly.

Before this can run for real, you need the same Meta credentials as
Agent 02 — access token, ad account ID — for the actress's account
specifically, granted the same partner-access way every other client was.

SAFETY DEFAULT: DRY_RUN = True, identical pattern to every other agent.
"""

import os
import json
import requests
from datetime import datetime, timedelta, timezone

API_VERSION = "v21.0"
BASE_URL = os.environ.get("META_API_URL", f"https://graph.facebook.com/{API_VERSION}")
META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "PASTE_YOUR_TOKEN_HERE")
META_AD_ACCOUNT_ID = os.environ.get("META_AD_ACCOUNT_ID", "act_XXXXXXXXXXXX")

# Best-current-guess — VERIFY against a real Insights response before trusting it.
# Likely candidates Meta may use: "onsite_conversion.ig_profile_visit", "ig_profile_visits",
# or it may simply appear as a custom "profile_visit" action_type — check and correct.
RESULT_ACTION_TYPE = os.environ.get("RESULT_ACTION_TYPE", "onsite_conversion.ig_profile_visit")

DRY_RUN = True

RULES = {
    "lookback_days": 7,
    "min_spend_to_judge": 50,
    "pause_if_cost_above_avg_by": 1.5,
    "boost_if_cost_below_avg_by": 0.7,
    "budget_boost_pct": 0.20,
    "max_budget_boost_pct_total": 1.0,
}

LOG_FILE = "agent_02c_actions.json"


def fetch_ad_insights(days):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    until = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = f"{BASE_URL}/{META_AD_ACCOUNT_ID}/insights"
    params = {
        "access_token": META_ACCESS_TOKEN, "level": "ad",
        "fields": "ad_id,ad_name,adset_id,spend,actions,ctr",
        "time_range": json.dumps({"since": since, "until": until}), "limit": 200,
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json().get("data", [])

    ads = []
    unrecognized_action_types_seen = set()
    for row in data:
        spend = float(row.get("spend", 0))
        visits = 0
        for action in row.get("actions", []):
            if action.get("action_type") == RESULT_ACTION_TYPE:
                visits += int(action.get("value", 0))
            else:
                unrecognized_action_types_seen.add(action.get("action_type"))
        cost_per_visit = (spend / visits) if visits > 0 else None
        ads.append({
            "ad_id": row["ad_id"], "ad_name": row.get("ad_name", ""),
            "adset_id": row.get("adset_id"), "spend": spend, "visits": visits,
            "cost_per_visit": cost_per_visit, "ctr": float(row.get("ctr", 0)),
        })

    if unrecognized_action_types_seen:
        print(f"[agent-02c] NOTE: saw these other action types in the response — "
              f"if profile visits show as 0 unexpectedly, one of these might be the real "
              f"field name to use instead: {unrecognized_action_types_seen}")
    return ads


def evaluate_ads(ads):
    judgeable = [a for a in ads if a["spend"] >= RULES["min_spend_to_judge"] and a["cost_per_visit"] is not None]
    if not judgeable:
        return [], []
    avg_cost = sum(a["cost_per_visit"] for a in judgeable) / len(judgeable)
    to_pause, to_boost = [], []
    for ad in judgeable:
        if ad["cost_per_visit"] >= avg_cost * RULES["pause_if_cost_above_avg_by"]:
            to_pause.append({**ad, "avg_cost": avg_cost, "reason": f"Cost/visit {ad['cost_per_visit']:.0f} vs avg {avg_cost:.0f}"})
        elif ad["cost_per_visit"] <= avg_cost * RULES["boost_if_cost_below_avg_by"]:
            to_boost.append({**ad, "avg_cost": avg_cost, "reason": f"Cost/visit {ad['cost_per_visit']:.0f} vs avg {avg_cost:.0f}"})
    return to_pause, to_boost


def pause_ad(ad_id, ad_name, reason):
    log_action("pause", ad_id, ad_name, reason)
    if DRY_RUN:
        print(f"[DRY RUN] Would PAUSE ad '{ad_name}' ({ad_id}) — {reason}")
        return
    url = f"{BASE_URL}/{ad_id}"
    response = requests.post(url, data={"access_token": META_ACCESS_TOKEN, "status": "PAUSED"}, timeout=30)
    response.raise_for_status()
    print(f"PAUSED ad '{ad_name}' ({ad_id}) — {reason}")


def boost_adset_budget(adset_id, ad_name, reason):
    log_action("boost", adset_id, ad_name, reason)
    if DRY_RUN:
        print(f"[DRY RUN] Would BOOST budget for ad set behind '{ad_name}' ({adset_id}) by "
              f"{RULES['budget_boost_pct']*100:.0f}% — {reason}")
        return
    url = f"{BASE_URL}/{adset_id}"
    current = requests.get(url, params={"access_token": META_ACCESS_TOKEN, "fields": "daily_budget"}, timeout=30).json()
    current_budget = int(current.get("daily_budget", 0))
    new_budget = min(int(current_budget * (1 + RULES["budget_boost_pct"])),
                      int(current_budget * (1 + RULES["max_budget_boost_pct_total"])))
    response = requests.post(url, data={"access_token": META_ACCESS_TOKEN, "daily_budget": new_budget}, timeout=30)
    response.raise_for_status()
    print(f"BOOSTED ad set {adset_id} budget {current_budget} -> {new_budget} — {reason}")


def log_action(action_type, target_id, name, reason):
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "action": action_type,
             "target_id": target_id, "name": name, "reason": reason, "dry_run": DRY_RUN}
    existing = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []
    existing.append(entry)
    with open(LOG_FILE, "w") as f:
        json.dump(existing, f, indent=2)


def main():
    print(f"--- Agent 02c run: {datetime.now(timezone.utc).isoformat()} (DRY_RUN={DRY_RUN}) ---")
    print(f"Watching action_type: {RESULT_ACTION_TYPE}")
    ads = fetch_ad_insights(RULES["lookback_days"])
    print(f"Fetched {len(ads)} ads from the last {RULES['lookback_days']} days.")

    to_pause, to_boost = evaluate_ads(ads)
    if not to_pause and not to_boost:
        print("No ads met the threshold for action this cycle. No changes made.")
        return

    for ad in to_pause:
        pause_ad(ad["ad_id"], ad["ad_name"], ad["reason"])
    for ad in to_boost:
        boost_adset_budget(ad["adset_id"], ad["ad_name"], ad["reason"])
    print(f"--- Run complete: {len(to_pause)} paused, {len(to_boost)} boosted ---")


if __name__ == "__main__":
    main()
