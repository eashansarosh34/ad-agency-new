"""
AGENT 26 — Post-Click Conversion Tracking
=============================================

The question this answers: "Am I just throwing ads at people, or do I
actually know who's looking, clicking, and buying?"

Meta already tracks the click. What most small agencies DON'T track is
what happens AFTER — did the person land on the page, scroll, add to
cart, buy? That's the Meta Pixel + Conversions API. This agent reads
that funnel data and tells you where people drop off, so you optimize
the leak, not just the ad.

  Ad seen -> clicked -> landed -> engaged -> converted
  Most agencies see only the first two. This sees all five, and tells
  you which step is losing people.

SETUP THE CLIENT NEEDS FIRST (one-time, this agent reads the result):
  1. A Meta Pixel created in Events Manager (business.facebook.com/events_manager)
  2. The pixel installed on their website/landing page (a snippet of code,
     or via Google Tag Manager, or a Shopify/WordPress plugin — easiest)
  3. Standard events defined: PageView, ViewContent, AddToCart, Lead, Purchase
  For lead-form campaigns with no website, the "Lead" event fires natively
  inside Meta — no pixel needed. Pixel matters when there's a site/checkout.

This agent then reads the funnel and finds the leak.
"""

import os
import json
import requests
from datetime import datetime, timedelta, timezone

META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")
META_AD_ACCOUNT_ID = os.environ.get("META_AD_ACCOUNT_ID", "act_XXXX")
META_API_URL = os.environ.get("META_API_URL", "https://graph.facebook.com/v21.0")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# The funnel steps we track, in order. Meta action_types that map to each.
FUNNEL_STEPS = [
    ("Saw the ad", ["impressions"]),
    ("Clicked", ["link_click", "clicks"]),
    ("Landed on page", ["landing_page_view"]),
    ("Engaged (viewed content)", ["view_content", "onsite_conversion.view_content"]),
    ("Added to cart", ["add_to_cart", "onsite_conversion.add_to_cart"]),
    ("Converted (lead/purchase)", ["lead", "purchase", "onsite_conversion.purchase",
                                    "onsite_conversion.lead_grouped"]),
]


def fetch_funnel(days=7):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    until = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    resp = requests.get(f"{META_API_URL}/{META_AD_ACCOUNT_ID}/insights", params={
        "access_token": META_ACCESS_TOKEN,
        "fields": "impressions,clicks,actions",
        "time_range": json.dumps({"since": since, "until": until}),
    }, timeout=30)
    resp.raise_for_status()
    rows = resp.json().get("data", [])
    if not rows:
        return None
    row = rows[0]

    actions = {a["action_type"]: int(a.get("value", 0)) for a in row.get("actions", [])}
    actions["impressions"] = int(row.get("impressions", 0))
    actions["clicks"] = int(row.get("clicks", 0))

    funnel = []
    for step_name, action_types in FUNNEL_STEPS:
        count = max((actions.get(at, 0) for at in action_types), default=0)
        funnel.append({"step": step_name, "count": count})
    return funnel


def analyze_funnel(funnel):
    """Find the biggest drop-off — the leak to fix."""
    print(f"\n{'='*55}")
    print("CONVERSION FUNNEL — where people actually go")
    print(f"{'='*55}")

    biggest_drop = {"from": None, "to": None, "drop_pct": 0}
    for i, step in enumerate(funnel):
        count = step["count"]
        if count == 0 and i > 0:
            continue
        bar = "█" * min(int(count / max(funnel[0]["count"], 1) * 30), 30) if funnel[0]["count"] else ""
        pct_of_top = (count / funnel[0]["count"] * 100) if funnel[0]["count"] else 0
        print(f"  {step['step']:<28} {count:>8,}  {bar} {pct_of_top:.1f}%")

        if i > 0:
            prev = funnel[i-1]["count"]
            if prev > 0 and count > 0:
                drop = (prev - count) / prev
                if drop > biggest_drop["drop_pct"]:
                    biggest_drop = {"from": funnel[i-1]["step"], "to": step["step"],
                                    "drop_pct": drop}

    print(f"{'='*55}")
    if biggest_drop["from"]:
        print(f"\n  🔍 Biggest drop-off: {biggest_drop['drop_pct']:.0%} of people are lost")
        print(f"     between '{biggest_drop['from']}' and '{biggest_drop['to']}'")
        print(f"     → This is where to focus. {_diagnose_drop(biggest_drop)}")
    return biggest_drop


def _diagnose_drop(drop):
    f, t = drop["from"], drop["to"]
    if "Clicked" in f and "Landed" in t:
        return "People click but don't land — slow page load, or a broken/mismatched link."
    if "Landed" in f and "Engaged" in t:
        return "They land but leave fast — the page doesn't match the ad's promise, or loads poorly."
    if "Engaged" in f and "cart" in t.lower():
        return "Interest but no cart adds — price shock, unclear value, or weak product page."
    if "cart" in f.lower() and "Converted" in t:
        return "Cart abandonment — checkout friction, unexpected shipping cost, or no trust signals."
    if "Saw" in f and "Clicked" in t:
        return "Low click rate — the ad creative or hook isn't compelling enough. This is an AD problem."
    return "Investigate what changes between these two steps."


if __name__ == "__main__":
    if not META_ACCESS_TOKEN:
        # Demo with realistic mock funnel showing a landing-page leak
        print("[Demo mode — no token set, using illustrative numbers]")
        mock_funnel = [
            {"step": "Saw the ad", "count": 45000},
            {"step": "Clicked", "count": 1350},
            {"step": "Landed on page", "count": 620},       # big drop here — the leak
            {"step": "Engaged (viewed content)", "count": 480},
            {"step": "Added to cart", "count": 95},
            {"step": "Converted (lead/purchase)", "count": 38},
        ]
        analyze_funnel(mock_funnel)
    else:
        funnel = fetch_funnel()
        if funnel:
            analyze_funnel(funnel)
        else:
            print("No funnel data available yet.")
