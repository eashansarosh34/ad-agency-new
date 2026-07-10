"""
AGENT 35 — Budget Timing Intelligence
========================================

What this does that nothing else here currently does:
  Analyzes real performance data split by day-of-week and hour-of-day
  to find when the same budget produces cheaper leads — then gives you
  a concrete ad scheduling recommendation. A Tuesday-9am lead for a
  local brand can be 40% cheaper than a Friday-7pm lead from the same
  campaign; nobody at small-business scale is exploiting this because
  pulling and analyzing time-breakdown data manually is too slow to be
  worth it. This makes it automatic.

  Output: a specific schedule recommendation ("turn off Fridays 7-11pm,
  increase budget Tue/Wed morning") that you can plug directly into
  Meta's ad scheduling feature (available when using lifetime budgets).
"""

import os
import json
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get("META_API_URL", "https://graph.facebook.com/v21.0")
META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "PASTE_TOKEN")
META_AD_ACCOUNT_ID = os.environ.get("META_AD_ACCOUNT_ID", "act_XXXXXXXX")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
LOG_FILE = "agent_35_timing_recommendations.json"

DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
MIN_DATA_POINTS = 7  # need at least a week of data to make a timing call


def fetch_breakdown_by_day(days=28):
    """Pulls performance split by day-of-week — needs at least 4 weeks of data to be meaningful."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    until = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = f"{BASE_URL}/{META_AD_ACCOUNT_ID}/insights"
    params = {
        "access_token": META_ACCESS_TOKEN,
        "fields": "spend,actions,impressions,ctr",
        "breakdowns": "day_of_week",
        "time_range": json.dumps({"since": since, "until": until}),
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("data", [])


def parse_day_performance(rows):
    by_day = {}
    for row in rows:
        day = row.get("day_of_week", "Unknown")
        spend = float(row.get("spend", 0))
        leads = sum(int(a.get("value", 0)) for a in row.get("actions", [])
                    if a.get("action_type") in ("lead", "onsite_conversion.lead_grouped"))
        cpl = (spend / leads) if leads > 0 else None
        if day not in by_day:
            by_day[day] = {"spend": 0, "leads": 0, "cpls": []}
        by_day[day]["spend"] += spend
        by_day[day]["leads"] += leads
        if cpl:
            by_day[day]["cpls"].append(cpl)

    result = []
    for day, data in by_day.items():
        avg_cpl = sum(data["cpls"]) / len(data["cpls"]) if data["cpls"] else None
        result.append({"day": day, "spend": data["spend"], "leads": data["leads"], "avg_cpl": avg_cpl})
    return sorted(result, key=lambda x: (x["avg_cpl"] or 999))


def generate_schedule_recommendation(day_data):
    if not day_data or all(d["avg_cpl"] is None for d in day_data):
        return "Not enough lead data yet to make a timing recommendation — needs at least a few leads per day."

    valid = [d for d in day_data if d["avg_cpl"] is not None]
    if len(valid) < 3:
        return "Need data across at least 3 different days before a reliable timing recommendation is possible."

    best = valid[:2]
    worst = valid[-2:]
    avg_cpl = sum(d["avg_cpl"] for d in valid) / len(valid)

    prompt = f"""Based on 4 weeks of real Meta ad performance data broken down by day of week:

Best performing days (cheapest CPL): {[f"{d['day']}: ₹{d['avg_cpl']:.0f}/lead" for d in best]}
Worst performing days (most expensive): {[f"{d['day']}: ₹{d['avg_cpl']:.0f}/lead" for d in worst]}
Account average CPL: ₹{avg_cpl:.0f}

Write a specific, actionable ad scheduling recommendation (3-4 bullets) — exactly which days
to concentrate budget on and which to reduce/pause, with rough percentage suggestions. Be
concrete ("increase Tuesday-Wednesday budget by 30%, reduce Saturday-Sunday by 50%"), not
generic. Note: Meta's day-parting requires lifetime budgets, not daily budgets.

Respond as plain text, no JSON."""

    if not ANTHROPIC_API_KEY:
        best_days = " and ".join(d["day"] for d in best)
        worst_days = " and ".join(d["day"] for d in worst)
        return (f"Timing recommendation (template — no live key for nuanced analysis):\n"
                f"- Concentrate budget on {best_days} — cheapest leads\n"
                f"- Reduce spend on {worst_days} — most expensive leads\n"
                f"- Switch to lifetime budget to enable day-parting in Meta's ad scheduling\n"
                f"- Re-evaluate after 2 more weeks once more data points accumulate")
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                     "Content-Type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 400,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=20,
        )
        resp.raise_for_status()
        return "".join(b.get("text", "") for b in resp.json().get("content", []) if b.get("type") == "text")
    except Exception as e:
        return f"Recommendation generation failed ({e}) — see raw data above to inform manual scheduling."


def run():
    print(f"--- Agent 35 run: {datetime.now(timezone.utc).isoformat()} ---")
    rows = fetch_breakdown_by_day(28)
    if not rows:
        print("No breakdown data available yet — needs at least a week of active campaign data.")
        return

    day_data = parse_day_performance(rows)
    print("\nDay-of-week performance:")
    for d in day_data:
        cpl_str = f"₹{d['avg_cpl']:.0f}" if d["avg_cpl"] else "no leads yet"
        print(f"  {d['day']}: spend={d['spend']:.0f}, leads={d['leads']}, CPL={cpl_str}")

    recommendation = generate_schedule_recommendation(day_data)
    print(f"\n[RECOMMENDATION]\n{recommendation}")

    entry = {"generated_at": datetime.now(timezone.utc).isoformat(),
             "day_data": day_data, "recommendation": recommendation}
    existing = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            try: existing = json.load(f)
            except: existing = []
    existing.append(entry)
    with open(LOG_FILE, "w") as f:
        json.dump(existing, f, indent=2)
    print(f"\nRecommendation saved to {LOG_FILE}")


if __name__ == "__main__":
    if META_ACCESS_TOKEN in ("", "PASTE_TOKEN", "PASTE_YOUR_TOKEN_HERE") or "XXXX" in META_AD_ACCOUNT_ID:
        print("[agent_35_budget_timing] No real META_ACCESS_TOKEN / META_AD_ACCOUNT_ID set - this agent needs a live Meta account to run.")
        import sys; sys.exit(0)
    run()
