"""
AGENT 02 — Media Buying & Optimization Agent
==============================================

What this does:
  Connects to a client's Meta Ads account, pulls performance data for active
  ads, and applies optimization rules automatically: pausing ads that are
  burning budget with a bad cost-per-lead, and shifting budget toward ads
  that are converting well. Run it on a schedule (e.g. every 6-12 hours via
  cron) and it keeps the account tuned without you touching it manually.

Before this can run for real, you need:
  1. A client onboarded via the onboarding checklist (Advertiser-level
     partner access to their Meta ad account — see that doc).
  2. A Meta access token with `ads_management` and `ads_read` permissions.
     Generate one via your Meta Business app at developers.facebook.com
     (Marketing API product). For anything beyond testing, this needs to be
     a long-lived System User token, not a personal one that expires.
  3. The client's Ad Account ID (format: act_XXXXXXXXXXXX).
  4. `pip install requests --break-system-packages`

SAFETY DEFAULT: this script runs in DRY_RUN mode by default. It will fetch
real data and print exactly what it *would* do, but will not pause ads or
change budgets until you explicitly set DRY_RUN = False. Run it in dry-run
for at least a few cycles on a new account before trusting it live — and
always keep a hard ceiling on the campaign's overall daily budget set
directly in Meta as a backstop, independent of this script.
"""

import os
import json
import requests
from datetime import datetime, timedelta, timezone

# ----------------------------------------------------------------------------
# CONFIG — fill these in per client, or load from environment variables
# ----------------------------------------------------------------------------

ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "PASTE_YOUR_TOKEN_HERE")
AD_ACCOUNT_ID = os.environ.get("META_AD_ACCOUNT_ID", "act_XXXXXXXXXXXX")
API_VERSION = "v21.0"
BASE_URL = os.environ.get("META_API_URL", f"https://graph.facebook.com/{API_VERSION}")
CLIENT_NAME = os.environ.get("CLIENT_NAME", "Client")

DRY_RUN = True  # <-- flip to False only once you trust this on a live account

# Budget Guardian — set BUDGET_CEILING to your client's agreed hard cap.
# When total spend hits this, all ads pause automatically and the client
# gets a WhatsApp alert. 0 means no ceiling (disabled).
BUDGET_CEILING = float(os.environ.get("BUDGET_CEILING", "0"))
BUDGET_CEILING_WHATSAPP = os.environ.get("BUDGET_CEILING_WHATSAPP", "") or os.environ.get("CLIENT_WHATSAPP", "")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")

RULES = {
    "lookback_days": 7,
    "min_spend_to_judge": 50,
    "pause_if_cpl_above_avg_by": 1.5,
    "boost_if_cpl_below_avg_by": 0.7,
    "budget_boost_pct": 0.20,
    "max_budget_boost_pct_total": 1.0,
}

LOG_FILE = "agent_02_actions.json"


def check_budget_ceiling(ads):
    if not BUDGET_CEILING:
        return False
    total_spend = sum(a["spend"] for a in ads)
    if total_spend < BUDGET_CEILING:
        print(f"[budget-guardian] Spend ₹{total_spend:.0f} within ceiling ₹{BUDGET_CEILING:.0f}. OK.")
        return False
    print(f"[budget-guardian] ⚠ CEILING HIT: ₹{total_spend:.0f} >= ₹{BUDGET_CEILING:.0f}. Pausing all ads.")
    for ad in ads:
        if DRY_RUN:
            print(f"[DRY RUN] Would PAUSE ad '{ad['ad_name']}' — budget ceiling reached")
        else:
            try:
                requests.post(f"{BASE_URL}/{ad['ad_id']}",
                    data={"access_token": ACCESS_TOKEN, "status": "PAUSED"}, timeout=30).raise_for_status()
                print(f"PAUSED ad '{ad['ad_name']}' — budget ceiling reached")
            except Exception as e:
                print(f"Could not pause ad {ad['ad_id']}: {e}")
    if BUDGET_CEILING_WHATSAPP and WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID:
        msg = (f"Hi! Your {CLIENT_NAME} campaign just hit the ₹{BUDGET_CEILING:.0f} limit you set. "
               f"All ads are paused. Let me know if you want to continue or adjust the limit.")
        if DRY_RUN:
            print(f"[DRY RUN] Would WhatsApp {BUDGET_CEILING_WHATSAPP}: {msg}")
        else:
            try:
                requests.post(f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/messages",
                    headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"},
                    json={"messaging_product": "whatsapp", "to": BUDGET_CEILING_WHATSAPP,
                          "type": "text", "text": {"body": msg}}, timeout=15)
            except Exception as e:
                print(f"WhatsApp alert failed ({e}) — ceiling was still enforced")

    try:
        from agent_22_human_escalation import escalate
        escalate("budget", CLIENT_NAME,
                 f"Budget Guardian: spend hit ₹{BUDGET_CEILING:.0f} ceiling, all ads auto-paused",
                 details={"ceiling": BUDGET_CEILING, "ads_paused": len(ads)}, notify_client=True)
    except ImportError:
        pass  # Agent 22 not present — Budget Guardian still works standalone

    return True


# ----------------------------------------------------------------------------
# DATA FETCHING
# ----------------------------------------------------------------------------

def fetch_ad_insights(days):
    """Pull per-ad performance: spend, leads, CPL, CTR for the lookback window."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    until = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    url = f"{BASE_URL}/{AD_ACCOUNT_ID}/insights"
    params = {
        "access_token": ACCESS_TOKEN,
        "level": "ad",
        "fields": "ad_id,ad_name,adset_id,spend,actions,ctr",
        "time_range": json.dumps({"since": since, "until": until}),
        "limit": 200,
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json().get("data", [])

    ads = []
    for row in data:
        spend = float(row.get("spend", 0))
        leads = 0
        for action in row.get("actions", []):
            if action.get("action_type") in ("lead", "onsite_conversion.lead_grouped"):
                leads += int(action.get("value", 0))
        cpl = (spend / leads) if leads > 0 else None
        ads.append({
            "ad_id": row["ad_id"],
            "ad_name": row.get("ad_name", ""),
            "adset_id": row.get("adset_id"),
            "spend": spend,
            "leads": leads,
            "cpl": cpl,
            "ctr": float(row.get("ctr", 0)),
        })
    return ads


# ----------------------------------------------------------------------------
# DECISION LOGIC
# ----------------------------------------------------------------------------

def evaluate_ads(ads):
    """Decide which ads to pause and which ad sets to boost, based on RULES."""
    judgeable = [a for a in ads if a["spend"] >= RULES["min_spend_to_judge"] and a["cpl"] is not None]

    if not judgeable:
        return [], []

    avg_cpl = sum(a["cpl"] for a in judgeable) / len(judgeable)

    to_pause = []
    to_boost = []

    for ad in judgeable:
        if ad["cpl"] >= avg_cpl * RULES["pause_if_cpl_above_avg_by"]:
            to_pause.append({**ad, "avg_cpl": avg_cpl, "reason": f"CPL {ad['cpl']:.0f} vs account avg {avg_cpl:.0f}"})
        elif ad["cpl"] <= avg_cpl * RULES["boost_if_cpl_below_avg_by"]:
            to_boost.append({**ad, "avg_cpl": avg_cpl, "reason": f"CPL {ad['cpl']:.0f} vs account avg {avg_cpl:.0f}"})

    return to_pause, to_boost


# ----------------------------------------------------------------------------
# ACTIONS (these touch real money — guarded by DRY_RUN)
# ----------------------------------------------------------------------------

def pause_ad(ad_id, ad_name, reason):
    log_action("pause", ad_id, ad_name, reason)
    if DRY_RUN:
        print(f"[DRY RUN] Would PAUSE ad '{ad_name}' ({ad_id}) — {reason}")
        return
    url = f"{BASE_URL}/{ad_id}"
    response = requests.post(url, data={"access_token": ACCESS_TOKEN, "status": "PAUSED"}, timeout=30)
    response.raise_for_status()
    print(f"PAUSED ad '{ad_name}' ({ad_id}) — {reason}")


def boost_adset_budget(adset_id, ad_name, reason):
    log_action("boost", adset_id, ad_name, reason)
    if DRY_RUN:
        print(f"[DRY RUN] Would BOOST budget for ad set behind '{ad_name}' ({adset_id}) by "
              f"{RULES['budget_boost_pct']*100:.0f}% — {reason}")
        return

    # Fetch current budget first, then increase it within the allowed cap.
    url = f"{BASE_URL}/{adset_id}"
    current = requests.get(url, params={"access_token": ACCESS_TOKEN, "fields": "daily_budget"}, timeout=30).json()
    current_budget = int(current.get("daily_budget", 0))
    new_budget = int(current_budget * (1 + RULES["budget_boost_pct"]))
    cap = int(current_budget * (1 + RULES["max_budget_boost_pct_total"]))
    new_budget = min(new_budget, cap)

    response = requests.post(url, data={"access_token": ACCESS_TOKEN, "daily_budget": new_budget}, timeout=30)
    response.raise_for_status()
    print(f"BOOSTED ad set {adset_id} budget {current_budget} -> {new_budget} — {reason}")


def log_action(action_type, target_id, name, reason):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action_type,
        "target_id": target_id,
        "name": name,
        "reason": reason,
        "dry_run": DRY_RUN,
    }
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


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------

def main():
    print(f"--- Agent 02 run: {datetime.now(timezone.utc).isoformat()} (DRY_RUN={DRY_RUN}) ---")
    ads = fetch_ad_insights(RULES["lookback_days"])
    print(f"Fetched {len(ads)} ads from the last {RULES['lookback_days']} days.")

    if check_budget_ceiling(ads):
        print("Budget ceiling enforced. No further optimization this cycle.")
        return

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
    import sys as _sys
    _tok = ACCESS_TOKEN if "ACCESS_TOKEN" in dir() else META_ACCESS_TOKEN
    _acct = AD_ACCOUNT_ID if "AD_ACCOUNT_ID" in dir() else META_AD_ACCOUNT_ID
    if _tok in ("", "PASTE_TOKEN", "PASTE_YOUR_TOKEN_HERE") or "XXXX" in _acct:
        print("[agent_02_media_optimizer] No real Meta token/account set - this agent needs live credentials to run.")
        _sys.exit(0)
    main()
