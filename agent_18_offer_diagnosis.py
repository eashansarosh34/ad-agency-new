"""
AGENT 18 — Offer Diagnosis
==============================

The hardest thing to say to a client, and the most valuable:
sometimes the reason leads aren't converting isn't the ad creative or
the targeting. It's the offer itself — the price, the positioning, the
friction in the process after someone clicks.

This agent detects that gap — high interest (good CTR, good lead volume)
but poor downstream conversion — and names it plainly instead of letting
you keep optimizing an ad that was never the real problem.

This is the thing that builds decade-long relationships. Any agency can
say "let's try a different creative." Only a strategic partner tells you
"actually your ads are working fine — let's talk about your offer."

Reads from: leads_db.json, performance_log.json
"""

import os
import json
import requests
from datetime import datetime, timezone, timedelta

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
LEADS_DB_PATH = os.environ.get("LEADS_DB_PATH", "leads_db.json")
PERFORMANCE_LOG = os.environ.get("PERFORMANCE_LOG", "performance_log.json")
DIAGNOSIS_LOG = "offer_diagnoses.json"

# Thresholds that trigger an offer diagnosis
CTR_HEALTHY_MIN = 1.5          # % — if CTR is above this, the ad is doing its job
LEAD_QUALIFIED_RATE_LOW = 0.30  # if <30% of leads qualify, offer may be attracting wrong audience
LEAD_QUALIFIED_RATE_OK = 0.60   # 60%+ = healthy qualification rate
CPL_RISING_PCT = 0.25           # if CPL rose 25%+ without creative change, signal to check offer


def load_json_file(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def compute_qualification_rate(leads_db):
    all_leads = list(leads_db.values()) if isinstance(leads_db, dict) else leads_db
    if not all_leads:
        return None, 0, 0
    with_reply = [l for l in all_leads if l.get("last_reply")]
    qualified = [l for l in all_leads if l.get("status") == "qualified"]
    total = len(all_leads)
    qual_rate = len(qualified) / total if total else None
    return qual_rate, len(qualified), total


def diagnose(client_id, ctr, cpl, cpl_previous=None, extra_context=""):
    leads_db = load_json_file(LEADS_DB_PATH)
    if isinstance(leads_db, dict):
        client_leads = {k: v for k, v in leads_db.items() if v.get("client_id", client_id) == client_id}
    else:
        client_leads = {}

    qual_rate, qualified, total_leads = compute_qualification_rate(client_leads)

    signals = []
    diagnosis_type = "healthy"

    cpl_rising = cpl_previous and ((cpl - cpl_previous) / cpl_previous) > CPL_RISING_PCT
    ctr_healthy = ctr >= CTR_HEALTHY_MIN

    if ctr_healthy and cpl_rising:
        signals.append(f"CTR is healthy ({ctr:.1f}%) — people are clicking your ad. But CPL rose {(cpl-cpl_previous)/cpl_previous:.0%}. The ad isn't the issue.")
        diagnosis_type = "offer_or_landing"

    if qual_rate is not None and qual_rate < LEAD_QUALIFIED_RATE_LOW and total_leads >= 5:
        signals.append(f"Only {qual_rate:.0%} of {total_leads} leads are qualifying ({qualified} qualified). High volume, low quality usually means the offer is attracting the wrong people.")
        diagnosis_type = "offer_audience_mismatch"

    if ctr_healthy and qual_rate is not None and qual_rate < LEAD_QUALIFIED_RATE_LOW:
        signals.append("Ads are generating interest but leads aren't converting — the gap is almost always in the offer or what happens after the click, not the creative.")

    prompt_data = {
        "client_id": client_id,
        "ctr": ctr,
        "cpl": cpl,
        "cpl_previous": cpl_previous,
        "qualification_rate": qual_rate,
        "total_leads": total_leads,
        "qualified_leads": qualified,
        "signals": signals,
        "extra_context": extra_context,
    }

    recommendation = None
    if ANTHROPIC_API_KEY and signals:
        try:
            prompt = f"""You are a strategic marketing advisor reviewing a client campaign.

Data:
{json.dumps(prompt_data, indent=2)}

The signals above suggest the issue may NOT be the ads — it may be the offer, pricing,
or what happens after someone clicks/enquires.

Write a SHORT, direct message (3-4 sentences) for the account manager to send or say to
the client that:
1. Acknowledges what IS working (the ads)
2. Names the real potential issue honestly (not the ads — something else)
3. Proposes ONE specific diagnostic action this week (e.g. "let's look at what happens
   to leads after they click", "what does your current price/offer look like vs competitors")

Plain language. No jargon. No hedging. This is the conversation that builds trust."""
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                         "Content-Type": "application/json"},
                json={"model": "claude-sonnet-4-6", "max_tokens": 200,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=20,
            )
            resp.raise_for_status()
            recommendation = "".join(b.get("text", "") for b in resp.json().get("content", []) if b.get("type") == "text")
        except Exception as e:
            recommendation = f"(live recommendation unavailable: {e})"

    if not recommendation and signals:
        recommendation = ("Your ads are working — people are clicking and enquiring. "
                         "But the conversion rate from lead to customer suggests the issue might be in the offer, pricing, "
                         "or what happens after someone contacts you. Let's look at that process this week before changing the ads.")

    result = {
        "client_id": client_id, "diagnosed_at": datetime.now(timezone.utc).isoformat(),
        "diagnosis_type": diagnosis_type, "signals": signals, "recommendation": recommendation,
        "data": {"ctr": ctr, "cpl": cpl, "cpl_previous": cpl_previous,
                 "qual_rate": qual_rate, "total_leads": total_leads},
    }

    existing = []
    if os.path.exists(DIAGNOSIS_LOG):
        with open(DIAGNOSIS_LOG, "r") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []
    existing.append(result)
    with open(DIAGNOSIS_LOG, "w") as f:
        json.dump(existing, f, indent=2)

    return result


if __name__ == "__main__":
    import sys
    # Test with realistic "ads working but leads not converting" scenario
    result = diagnose(
        client_id="SunCap",
        ctr=3.2,
        cpl=390,
        cpl_previous=280,
        extra_context="Client is asking why leads aren't becoming customers despite good click volumes"
    )
    print(f"\n[offer-diagnosis] Client: {result['client_id']}")
    print(f"Diagnosis type: {result['diagnosis_type']}")
    if result["signals"]:
        print("Signals detected:")
        for s in result["signals"]:
            print(f"  • {s}")
        print(f"\nWhat to say to the client:")
        print(f"  {result['recommendation']}")
    else:
        print("No offer issues detected — campaign appears healthy.")
