"""
AGENT 07 — Google Ads Optimizer
==================================

What this does:
  Same job as Agent 02, second platform: pulls campaign performance from
  Google Ads, pauses campaigns with a clearly bad cost-per-conversion, and
  shifts budget toward campaigns beating the account average.

Before this can run for real, you need (this setup is genuinely more
involved than Meta's — budget real time for it):
  1. A Google Ads Developer Token — apply via the API Center inside a
     Google Ads "manager" (MCC) account. Test accounts work immediately;
     a real production account needs Google to approve at least Basic
     access, which is a real review, not instant.
  2. OAuth2 credentials: create an OAuth Client ID + Secret in Google
     Cloud Console, then run Google's one-time consent flow to get a
     Refresh Token (this exchanges once for ongoing access — see Google's
     "Obtain a refresh token" guide).
  3. Your Customer ID (the account ID, digits only, no dashes) and, if
     it's managed through an MCC, the MCC's Customer ID as the
     login-customer-id header.
  4. `pip install requests --break-system-packages`

API VERSION NOTE: Google moved to a monthly release cadence in 2026 —
versions sunset roughly every 6 months now, not 18-24. The version string
below (v23) was current as of mid-2026; check developers.google.com/google-ads/api/docs/release-notes
before relying on this long-term, and update API_VERSION if it's sunset.

SAFETY DEFAULT: DRY_RUN = True, same as Agent 02 — reads real data, prints
what it would change, touches nothing until you explicitly disable it.
"""

import os
import json
import requests
from datetime import datetime, timedelta, timezone

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------

GOOGLE_ADS_DEVELOPER_TOKEN = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "PASTE_DEV_TOKEN")
GOOGLE_ADS_CLIENT_ID = os.environ.get("GOOGLE_ADS_CLIENT_ID", "PASTE_CLIENT_ID")
GOOGLE_ADS_CLIENT_SECRET = os.environ.get("GOOGLE_ADS_CLIENT_SECRET", "PASTE_CLIENT_SECRET")
GOOGLE_ADS_REFRESH_TOKEN = os.environ.get("GOOGLE_ADS_REFRESH_TOKEN", "PASTE_REFRESH_TOKEN")
GOOGLE_ADS_CUSTOMER_ID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "PASTE_CUSTOMER_ID")
GOOGLE_ADS_LOGIN_CUSTOMER_ID = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "")  # MCC id, optional

API_VERSION = "v23"
BASE_URL = os.environ.get("GOOGLE_ADS_API_URL", f"https://googleads.googleapis.com/{API_VERSION}")
OAUTH_TOKEN_URL = os.environ.get("GOOGLE_OAUTH_URL", "https://oauth2.googleapis.com/token")

DRY_RUN = True  # <-- flip to False only once you trust this on a live account

RULES = {
    "lookback_days": 7,
    "min_cost_to_judge": 50,             # in account currency units — don't judge on too little spend
    "pause_if_cpa_above_avg_by": 1.5,
    "boost_if_cpa_below_avg_by": 0.7,
    "budget_boost_pct": 0.20,
    "max_budget_boost_pct_total": 1.0,
}

LOG_FILE = "agent_07_actions.json"


# ----------------------------------------------------------------------------
# AUTH — Google Ads uses OAuth2 refresh tokens, not a long-lived bearer token
# ----------------------------------------------------------------------------

def get_access_token():
    if "PASTE_" in GOOGLE_ADS_REFRESH_TOKEN and "localhost" not in OAUTH_TOKEN_URL:
        raise RuntimeError("OAuth credentials not set — see the setup notes at the top of this file.")
    response = requests.post(OAUTH_TOKEN_URL, data={
        "client_id": GOOGLE_ADS_CLIENT_ID,
        "client_secret": GOOGLE_ADS_CLIENT_SECRET,
        "refresh_token": GOOGLE_ADS_REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }, timeout=20)
    response.raise_for_status()
    return response.json()["access_token"]


def auth_headers(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": GOOGLE_ADS_DEVELOPER_TOKEN,
        "Content-Type": "application/json",
    }
    if GOOGLE_ADS_LOGIN_CUSTOMER_ID:
        headers["login-customer-id"] = GOOGLE_ADS_LOGIN_CUSTOMER_ID
    return headers


# ----------------------------------------------------------------------------
# DATA FETCHING — Google Ads Query Language (GAQL), not REST query params
# ----------------------------------------------------------------------------

def fetch_campaign_performance(access_token, days):
    query = f"""
        SELECT campaign.id, campaign.name, campaign.resource_name,
               campaign.campaign_budget, campaign_budget.amount_micros,
               metrics.cost_micros, metrics.clicks, metrics.impressions, metrics.conversions
        FROM campaign
        WHERE segments.date DURING LAST_{days}_DAYS
        AND campaign.status = 'ENABLED'
    """
    url = f"{BASE_URL}/customers/{GOOGLE_ADS_CUSTOMER_ID}/googleAds:search"
    response = requests.post(url, headers=auth_headers(access_token), json={"query": query}, timeout=30)
    response.raise_for_status()
    rows = response.json().get("results", [])

    campaigns = []
    for row in rows:
        cost = float(row.get("metrics", {}).get("costMicros", 0)) / 1_000_000
        conversions = float(row.get("metrics", {}).get("conversions", 0))
        cpa = (cost / conversions) if conversions > 0 else None
        campaigns.append({
            "campaign_id": row["campaign"]["id"],
            "campaign_name": row["campaign"].get("name", ""),
            "resource_name": row["campaign"]["resourceName"],
            "budget_resource": row["campaign"].get("campaignBudget", ""),
            "budget_micros": int(row.get("campaignBudget", {}).get("amountMicros", 0)),
            "cost": cost,
            "conversions": conversions,
            "cpa": cpa,
            "clicks": int(row.get("metrics", {}).get("clicks", 0)),
            "impressions": int(row.get("metrics", {}).get("impressions", 0)),
        })
    return campaigns


# ----------------------------------------------------------------------------
# DECISION LOGIC — same shape as Agent 02
# ----------------------------------------------------------------------------

def evaluate_campaigns(campaigns):
    judgeable = [c for c in campaigns if c["cost"] >= RULES["min_cost_to_judge"] and c["cpa"] is not None]
    if not judgeable:
        return [], []

    avg_cpa = sum(c["cpa"] for c in judgeable) / len(judgeable)
    to_pause, to_boost = [], []

    for c in judgeable:
        if c["cpa"] >= avg_cpa * RULES["pause_if_cpa_above_avg_by"]:
            to_pause.append({**c, "avg_cpa": avg_cpa, "reason": f"CPA {c['cpa']:.2f} vs account avg {avg_cpa:.2f}"})
        elif c["cpa"] <= avg_cpa * RULES["boost_if_cpa_below_avg_by"]:
            to_boost.append({**c, "avg_cpa": avg_cpa, "reason": f"CPA {c['cpa']:.2f} vs account avg {avg_cpa:.2f}"})

    return to_pause, to_boost


# ----------------------------------------------------------------------------
# ACTIONS — Google Ads mutate calls (resource + fieldMask, not full overwrite)
# ----------------------------------------------------------------------------

def pause_campaign(access_token, campaign):
    log_action("pause", campaign["campaign_id"], campaign["campaign_name"], campaign["reason"])
    if DRY_RUN:
        print(f"[DRY RUN] Would PAUSE campaign '{campaign['campaign_name']}' ({campaign['campaign_id']}) — {campaign['reason']}")
        return

    url = f"{BASE_URL}/customers/{GOOGLE_ADS_CUSTOMER_ID}/campaigns:mutate"
    body = {"operations": [{"update": {"resourceName": campaign["resource_name"], "status": "PAUSED"},
                             "updateMask": "status"}]}
    response = requests.post(url, headers=auth_headers(access_token), json=body, timeout=30)
    response.raise_for_status()
    print(f"PAUSED campaign '{campaign['campaign_name']}' — {campaign['reason']}")


def boost_campaign_budget(access_token, campaign):
    log_action("boost", campaign["campaign_id"], campaign["campaign_name"], campaign["reason"])
    if DRY_RUN:
        print(f"[DRY RUN] Would BOOST budget for '{campaign['campaign_name']}' by "
              f"{RULES['budget_boost_pct']*100:.0f}% — {campaign['reason']}")
        return

    current = campaign["budget_micros"]
    new_budget = int(current * (1 + RULES["budget_boost_pct"]))
    cap = int(current * (1 + RULES["max_budget_boost_pct_total"]))
    new_budget = min(new_budget, cap)

    url = f"{BASE_URL}/customers/{GOOGLE_ADS_CUSTOMER_ID}/campaignBudgets:mutate"
    body = {"operations": [{"update": {"resourceName": campaign["budget_resource"], "amountMicros": str(new_budget)},
                             "updateMask": "amount_micros"}]}
    response = requests.post(url, headers=auth_headers(access_token), json=body, timeout=30)
    response.raise_for_status()
    print(f"BOOSTED budget for '{campaign['campaign_name']}' {current} -> {new_budget} micros")


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


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------

def main():
    print(f"--- Agent 07 run: {datetime.now(timezone.utc).isoformat()} (DRY_RUN={DRY_RUN}) ---")
    access_token = get_access_token()
    campaigns = fetch_campaign_performance(access_token, RULES["lookback_days"])
    print(f"Fetched {len(campaigns)} campaigns from the last {RULES['lookback_days']} days.")

    to_pause, to_boost = evaluate_campaigns(campaigns)
    if not to_pause and not to_boost:
        print("No campaigns met the threshold for action this cycle. No changes made.")
        return

    for c in to_pause:
        pause_campaign(access_token, c)
    for c in to_boost:
        boost_campaign_budget(access_token, c)

    print(f"--- Run complete: {len(to_pause)} paused, {len(to_boost)} boosted ---")


if __name__ == "__main__":
    main()
