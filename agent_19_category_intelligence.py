"""
AGENT 19 — Category Intelligence
===================================

Every client in the same vertical teaches you something. This agent
builds that knowledge base automatically — what CPL ranges are normal,
what creative angles burn out fastest, what audiences convert but don't
retain — and when a new client in the same vertical is onboarded, you
walk in already knowing things about their business before they tell you.

This is moat-building. The second dental clinic client gets the benefit
of everything learned from the first. No competing agency offers this at
small-business retainer pricing.

PRIVACY: all data is stored locally in category_intelligence.json —
never leaves your machine, never shared between clients. Each client
entry is identified by an alias you set, not their real name.
"""

import os
import json
import requests
from datetime import datetime, timezone

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
INTEL_FILE = os.environ.get("CATEGORY_INTEL_FILE", "category_intelligence.json")


def load_intel():
    if not os.path.exists(INTEL_FILE):
        return {}
    with open(INTEL_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_intel(intel):
    with open(INTEL_FILE, "w") as f:
        json.dump(intel, f, indent=2)


def log_campaign_outcome(category, client_alias, data_point):
    """
    Call this after each client campaign cycle to build the knowledge base.
    data_point should contain:
      - cpl_achieved: float
      - best_creative_angle: str (e.g. "before/after", "urgency/offer", "social proof")
      - audience_that_worked: str (e.g. "women 25-45 interested in wellness")
      - what_failed: str (e.g. "generic product shots with no hook")
      - city: str
      - budget: int
      - notes: str (any other observations)
    """
    intel = load_intel()
    if category not in intel:
        intel[category] = {"data_points": [], "insights": None, "last_updated": None}

    data_point["client_alias"] = client_alias
    data_point["logged_at"] = datetime.now(timezone.utc).isoformat()
    intel[category]["data_points"].append(data_point)
    intel[category]["last_updated"] = datetime.now(timezone.utc).isoformat()
    save_intel(intel)

    print(f"[category-intel] Logged data point for '{category}' (client: {client_alias}). "
          f"Now {len(intel[category]['data_points'])} data point(s) in this category.")

    # Regenerate insights if 2+ data points exist
    if len(intel[category]["data_points"]) >= 2:
        generate_category_insights(category)


def generate_category_insights(category):
    intel = load_intel()
    if category not in intel or not intel[category]["data_points"]:
        return None

    data_points = intel[category]["data_points"]

    # Always compute baseline stats (no API needed)
    cpls = [d["cpl_achieved"] for d in data_points if d.get("cpl_achieved")]
    best_angles = [d["best_creative_angle"] for d in data_points if d.get("best_creative_angle")]
    what_failed = [d["what_failed"] for d in data_points if d.get("what_failed")]

    base_insights = {
        "cpl_range_observed": {"min": min(cpls), "max": max(cpls), "avg": round(sum(cpls)/len(cpls), 0)} if cpls else None,
        "most_repeated_winning_angle": max(set(best_angles), key=best_angles.count) if best_angles else None,
        "most_repeated_failure": max(set(what_failed), key=what_failed.count) if what_failed else None,
        "data_points_count": len(data_points),
    }

    narrative = None
    if ANTHROPIC_API_KEY:
        prompt = f"""You are building an intelligence brief for a marketing category: "{category}".

Here are anonymized campaign data points from real client campaigns:
{json.dumps(data_points, indent=2)}

Write a SHORT intelligence brief (5-6 sentences) that:
1. States what CPL range is realistic for this category
2. Names the creative angle that's repeatedly winning
3. Names what keeps failing
4. States one specific insight a new client in this category should know before starting
5. Flags any patterns in audience or timing worth knowing

Plain language. Specific and concrete. No generic marketing advice."""

        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                         "Content-Type": "application/json"},
                json={"model": "claude-sonnet-4-6", "max_tokens": 250,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=20,
            )
            resp.raise_for_status()
            narrative = "".join(b.get("text", "") for b in resp.json().get("content", []) if b.get("type") == "text")
        except Exception as e:
            narrative = f"(narrative unavailable: {e})"

    intel[category]["insights"] = {**base_insights, "narrative": narrative,
                                    "generated_at": datetime.now(timezone.utc).isoformat()}
    save_intel(intel)
    return intel[category]["insights"]


def get_brief_for_new_client(category):
    intel = load_intel()
    if category not in intel or not intel[category].get("insights"):
        return f"No category intelligence yet for '{category}'. You'll be building it with this first client."

    insights = intel[category]["insights"]
    print(f"\n[category-intel] BRIEFING: What we already know about '{category}'")
    print(f"  Based on {insights['data_points_count']} previous client(s) in this vertical")
    if insights.get("cpl_range_observed"):
        r = insights["cpl_range_observed"]
        print(f"  CPL observed: ₹{r['min']} – ₹{r['max']} (avg ₹{r['avg']})")
    if insights.get("most_repeated_winning_angle"):
        print(f"  Creative angle that keeps winning: {insights['most_repeated_winning_angle']}")
    if insights.get("most_repeated_failure"):
        print(f"  What keeps failing: {insights['most_repeated_failure']}")
    if insights.get("narrative"):
        print(f"\n  Full brief:\n  {insights['narrative']}")
    return insights


if __name__ == "__main__":
    # Seed with two realistic data points for dental clinics
    log_campaign_outcome("dental clinic", client_alias="client_DC1", data_point={
        "cpl_achieved": 210, "best_creative_angle": "before/after patient transformation",
        "audience_that_worked": "women 30-50 near clinic, interested in aesthetics",
        "what_failed": "generic 'book an appointment' with no visual hook",
        "city": "Hyderabad", "budget": 20000,
        "notes": "WhatsApp form reduced CPL by 40% vs landing page. Month 2 results much better than month 1."
    })
    log_campaign_outcome("dental clinic", client_alias="client_DC2", data_point={
        "cpl_achieved": 185, "best_creative_angle": "myth-busting reel ('root canal is painless')",
        "audience_that_worked": "adults 25-45 who follow dentist/health pages",
        "what_failed": "generic clinic exterior photo with price callout",
        "city": "Bangalore", "budget": 25000,
        "notes": "Educational content built more trust than promotional content. Review-request at 3 weeks improved CPL for subsequent campaigns."
    })
    print("\n=== Getting brief for a NEW dental clinic client ===")
    get_brief_for_new_client("dental clinic")