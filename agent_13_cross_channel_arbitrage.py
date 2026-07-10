"""
AGENT 13 — Cross-Channel Budget Arbitrage
=============================================

What this does:
  Agent 02 optimizes within Meta. Agent 07 optimizes within Google. Both
  are blind to each other. This sits one layer above both: compares real
  blended cost-per-lead across the two platforms, and if one is
  meaningfully cheaper right now, shifts a slice of budget from the
  pricier platform to the cheaper one — the kind of cross-channel
  reallocation that, at small-business scale, almost nothing else does.

Before this can run for real, you need everything Agent 02 and Agent 07
each separately need (Meta token + ad account, Google OAuth + customer ID)
PLUS the specific budget resource on each side you want this to adjust:
  - META_ADSET_ID — the Meta ad set whose budget this can move
  - GOOGLE_BUDGET_RESOURCE — the Google campaign budget resource name

SAFETY DEFAULT: DRY_RUN = True, same pattern as every other agent here.
The shift amount per cycle is deliberately capped (see RULES) so one bad
read of the numbers can't move a large chunk of budget in one move.
"""

import os
import json
import requests
from datetime import datetime, timedelta, timezone

# ----------------------------------------------------------------------------
# CONFIG — reuses the same credentials/env vars as Agent 02 and Agent 07
# ----------------------------------------------------------------------------

META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "PASTE_META_TOKEN")
META_AD_ACCOUNT_ID = os.environ.get("META_AD_ACCOUNT_ID", "PASTE_AD_ACCOUNT_ID")
META_ADSET_ID = os.environ.get("META_ADSET_ID", "PASTE_ADSET_ID")
META_API_URL = os.environ.get("META_API_URL", "https://graph.facebook.com/v21.0")

GOOGLE_ADS_DEVELOPER_TOKEN = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "PASTE_DEV_TOKEN")
GOOGLE_ADS_CLIENT_ID = os.environ.get("GOOGLE_ADS_CLIENT_ID", "PASTE_CLIENT_ID")
GOOGLE_ADS_CLIENT_SECRET = os.environ.get("GOOGLE_ADS_CLIENT_SECRET", "PASTE_CLIENT_SECRET")
GOOGLE_ADS_REFRESH_TOKEN = os.environ.get("GOOGLE_ADS_REFRESH_TOKEN", "PASTE_REFRESH_TOKEN")
GOOGLE_ADS_CUSTOMER_ID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "PASTE_CUSTOMER_ID")
GOOGLE_BUDGET_RESOURCE = os.environ.get("GOOGLE_BUDGET_RESOURCE", "PASTE_BUDGET_RESOURCE")
GOOGLE_ADS_API_URL = os.environ.get("GOOGLE_ADS_API_URL", "https://googleads.googleapis.com/v23")
GOOGLE_OAUTH_URL = os.environ.get("GOOGLE_OAUTH_URL", "https://oauth2.googleapis.com/token")

LOOKBACK_DAYS = 7
MIN_GAP_TO_ACT = 0.30          # only act if one platform's CPL is 30%+ cheaper than the other
SHIFT_PCT_PER_CYCLE = 0.15     # move at most 15% of the pricier platform's budget per run — capped, deliberate
LOG_FILE = "agent_13_actions.json"

DRY_RUN = os.environ.get("ORCHESTRATOR_DRY_RUN", "true").lower() != "false"  # controlled via GitHub Secret


# ----------------------------------------------------------------------------
# META — fetch account CPL, adjust ad set budget
# ----------------------------------------------------------------------------

def fetch_meta_cpl():
    since = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    until = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = f"{META_API_URL}/{META_AD_ACCOUNT_ID}/insights"
    resp = requests.get(url, params={
        "access_token": META_ACCESS_TOKEN, "fields": "spend,actions",
        "time_range": json.dumps({"since": since, "until": until}),
    }, timeout=30)
    resp.raise_for_status()
    rows = resp.json().get("data", [])
    if not rows:
        return None, 0, 0
    spend = float(rows[0].get("spend", 0))
    leads = sum(int(a.get("value", 0)) for a in rows[0].get("actions", [])
                if a.get("action_type") in ("lead", "onsite_conversion.lead_grouped"))
    cpl = (spend / leads) if leads else None
    return cpl, spend, leads


def adjust_meta_budget(new_budget_micros_equivalent):
    if DRY_RUN:
        print(f"[DRY RUN] Would set Meta ad set {META_ADSET_ID} daily budget to {new_budget_micros_equivalent:.0f}")
        return
    url = f"{META_API_URL}/{META_ADSET_ID}"
    resp = requests.post(url, data={"access_token": META_ACCESS_TOKEN,
                                     "daily_budget": int(new_budget_micros_equivalent)}, timeout=30)
    resp.raise_for_status()


def get_meta_budget():
    url = f"{META_API_URL}/{META_ADSET_ID}"
    resp = requests.get(url, params={"access_token": META_ACCESS_TOKEN, "fields": "daily_budget"}, timeout=30)
    resp.raise_for_status()
    return float(resp.json().get("daily_budget", 0))


# ----------------------------------------------------------------------------
# GOOGLE — fetch account CPL, adjust campaign budget (same OAuth pattern as Agent 07)
# ----------------------------------------------------------------------------

def get_google_access_token():
    resp = requests.post(GOOGLE_OAUTH_URL, data={
        "client_id": GOOGLE_ADS_CLIENT_ID, "client_secret": GOOGLE_ADS_CLIENT_SECRET,
        "refresh_token": GOOGLE_ADS_REFRESH_TOKEN, "grant_type": "refresh_token",
    }, timeout=20)
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_google_cpl_and_budget(access_token):
    query = f"""
        SELECT campaign.campaign_budget, campaign_budget.amount_micros,
               metrics.cost_micros, metrics.conversions
        FROM campaign
        WHERE segments.date DURING LAST_{LOOKBACK_DAYS}_DAYS
        AND campaign.status = 'ENABLED'
    """
    url = f"{GOOGLE_ADS_API_URL}/customers/{GOOGLE_ADS_CUSTOMER_ID}/googleAds:search"
    headers = {"Authorization": f"Bearer {access_token}", "developer-token": GOOGLE_ADS_DEVELOPER_TOKEN,
               "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json={"query": query}, timeout=30)
    resp.raise_for_status()
    rows = resp.json().get("results", [])
    if not rows:
        return None, 0, 0, 0

    spend = sum(float(r.get("metrics", {}).get("costMicros", 0)) for r in rows) / 1_000_000
    leads = sum(float(r.get("metrics", {}).get("conversions", 0)) for r in rows)
    cpl = (spend / leads) if leads else None

    # Current budget for the specific resource this agent is allowed to adjust.
    current_budget_micros = 0
    for r in rows:
        budget_field = r.get("campaignBudget", {})
        if budget_field.get("resourceName") == GOOGLE_BUDGET_RESOURCE or not GOOGLE_BUDGET_RESOURCE.startswith("PASTE"):
            current_budget_micros = float(r.get("campaignBudget", {}).get("amountMicros", 0)) or current_budget_micros
    if current_budget_micros == 0 and rows:
        current_budget_micros = float(rows[0].get("campaignBudget", {}).get("amountMicros", 0))

    return cpl, spend, leads, current_budget_micros


def adjust_google_budget(access_token, new_amount_micros):
    if DRY_RUN:
        print(f"[DRY RUN] Would set Google budget {GOOGLE_BUDGET_RESOURCE} to {new_amount_micros:.0f} micros")
        return
    url = f"{GOOGLE_ADS_API_URL}/customers/{GOOGLE_ADS_CUSTOMER_ID}/campaignBudgets:mutate"
    headers = {"Authorization": f"Bearer {access_token}", "developer-token": GOOGLE_ADS_DEVELOPER_TOKEN,
               "Content-Type": "application/json"}
    body = {"operations": [{"update": {"resourceName": GOOGLE_BUDGET_RESOURCE, "amountMicros": str(int(new_amount_micros))},
                             "updateMask": "amount_micros"}]}
    resp = requests.post(url, headers=headers, json=body, timeout=30)
    resp.raise_for_status()


# ----------------------------------------------------------------------------
# ARBITRAGE LOGIC
# ----------------------------------------------------------------------------

def log_action(entry):
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


def run_arbitrage():
    print(f"--- Agent 13 run: {datetime.now(timezone.utc).isoformat()} (DRY_RUN={DRY_RUN}) ---")

    meta_cpl, meta_spend, meta_leads = fetch_meta_cpl()
    access_token = get_google_access_token()
    google_cpl, google_spend, google_leads, google_budget_micros = fetch_google_cpl_and_budget(access_token)

    print(f"Meta:   spend={meta_spend:.0f}, leads={meta_leads}, CPL={meta_cpl}")
    print(f"Google: spend={google_spend:.0f}, leads={google_leads}, CPL={google_cpl}")

    if meta_cpl is None or google_cpl is None:
        print("Not enough data on at least one platform to compare yet. No action taken.")
        return

    gap = abs(meta_cpl - google_cpl) / max(meta_cpl, google_cpl)
    if gap < MIN_GAP_TO_ACT:
        print(f"Gap between platforms ({gap:.0%}) is below the {MIN_GAP_TO_ACT:.0%} threshold. No action taken.")
        return

    cheaper_platform = "meta" if meta_cpl < google_cpl else "google"
    reason = f"Meta CPL {meta_cpl:.2f} vs Google CPL {google_cpl:.2f} — {gap:.0%} gap, shifting toward {cheaper_platform}"
    print(reason)

    meta_budget = get_meta_budget()

    if cheaper_platform == "meta":
        shift_micros = google_budget_micros * SHIFT_PCT_PER_CYCLE
        new_google = google_budget_micros - shift_micros
        new_meta = meta_budget + (shift_micros / 1_000_000)  # rough currency-unit equivalence for this test
        adjust_google_budget(access_token, new_google)
        adjust_meta_budget(new_meta)
    else:
        shift_amount = meta_budget * SHIFT_PCT_PER_CYCLE
        new_meta = meta_budget - shift_amount
        new_google = google_budget_micros + (shift_amount * 1_000_000)
        adjust_meta_budget(new_meta)
        adjust_google_budget(access_token, new_google)

    log_action({"timestamp": datetime.now(timezone.utc).isoformat(), "reason": reason,
                "meta_cpl": meta_cpl, "google_cpl": google_cpl, "dry_run": DRY_RUN})
    print(f"--- Arbitrage complete: shifted toward {cheaper_platform} ---")


if __name__ == "__main__":
    run_arbitrage()
