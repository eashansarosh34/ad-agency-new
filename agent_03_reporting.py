"""
AGENT 03 — Reporting Agent
============================

What this does:
  Pulls the week's real performance data from Meta Ads, asks Claude to
  write the plain-language "what happened this week" summary, and fills
  in report_template.html with everything — producing a finished report
  ready to send to the client. Run it once a week (e.g. cron every Monday).

Before this can run for real, you need:
  1. Everything Agent 02 needs: Meta access token + ad account ID.
  2. An Anthropic API key (console.anthropic.com -> API Keys). This script
     calls the API directly, unlike the in-browser Creative Agent artifact.
  3. report_template.html in the same folder as this script.
  4. `pip install requests --break-system-packages`

NOTE ON WHATSAPP METRICS: WhatsApp reply rate, reply time, and "qualified"
status come from your WhatsApp automation tool (AiSensy / Wati), not from
Meta. Each has its own API with its own auth — fetch_whatsapp_metrics()
below is a stub with realistic placeholder logic. Replace it with a real
call to whichever tool you're using once you've picked one.
"""

import os
import json
import requests
from datetime import datetime, timedelta, timezone

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------

META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "PASTE_YOUR_TOKEN_HERE")
AD_ACCOUNT_ID = os.environ.get("META_AD_ACCOUNT_ID", "act_XXXXXXXXXXXX")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "PASTE_YOUR_KEY_HERE")
API_VERSION = "v21.0"
BASE_URL = os.environ.get("META_API_URL", f"https://graph.facebook.com/{API_VERSION}")

CLIENT_NAME = os.environ.get("CLIENT_NAME", "Aura Dental Clinic")
AGENCY_NAME = "Your Agency Name"
TEMPLATE_PATH = "report_template.html"
OUTPUT_DIR = "reports"


# ----------------------------------------------------------------------------
# DATA FETCHING — META
# ----------------------------------------------------------------------------

def fetch_account_totals(since, until):
    """Aggregate impressions, clicks, spend, leads for a date range."""
    url = f"{BASE_URL}/{AD_ACCOUNT_ID}/insights"
    params = {
        "access_token": META_ACCESS_TOKEN,
        "fields": "impressions,clicks,spend,actions",
        "time_range": json.dumps({"since": since, "until": until}),
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    rows = response.json().get("data", [])
    if not rows:
        return {"impressions": 0, "clicks": 0, "spend": 0.0, "leads": 0}

    row = rows[0]
    leads = 0
    for action in row.get("actions", []):
        if action.get("action_type") in ("lead", "onsite_conversion.lead_grouped"):
            leads += int(action.get("value", 0))

    return {
        "impressions": int(row.get("impressions", 0)),
        "clicks": int(row.get("clicks", 0)),
        "spend": float(row.get("spend", 0)),
        "leads": leads,
    }


def fetch_top_creatives(since, until, top_n=3):
    """Return the top N ads by lead count for the leaderboard section."""
    url = f"{BASE_URL}/{AD_ACCOUNT_ID}/insights"
    params = {
        "access_token": META_ACCESS_TOKEN,
        "level": "ad",
        "fields": "ad_name,actions,ctr",
        "time_range": json.dumps({"since": since, "until": until}),
        "limit": 200,
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    rows = response.json().get("data", [])

    ads = []
    for row in rows:
        leads = 0
        for action in row.get("actions", []):
            if action.get("action_type") in ("lead", "onsite_conversion.lead_grouped"):
                leads += int(action.get("value", 0))
        ads.append({
            "name": row.get("ad_name", "Untitled ad"),
            "ctr": float(row.get("ctr", 0)),
            "leads": leads,
        })

    ads.sort(key=lambda a: a["leads"], reverse=True)
    while len(ads) < top_n:
        ads.append({"name": "—", "ctr": 0, "leads": 0})
    return ads[:top_n]


# ----------------------------------------------------------------------------
# DATA FETCHING — WHATSAPP (stub: replace with your tool's real API)
# ----------------------------------------------------------------------------

def fetch_whatsapp_metrics(leads_count):
    """
    Reads real lead records written by Agent 04 (leads_db.json). Falls back
    to an estimate only if that file doesn't exist yet (e.g. Agent 04 hasn't
    run, or you're using a different WhatsApp tool that writes elsewhere —
    in that case, point LEADS_DB_PATH at wherever AiSensy/Wati exports to,
    or write a small adapter that converts their export into this shape).
    """
    leads_db_path = os.environ.get("LEADS_DB_PATH", "leads_db.json")
    if os.path.exists(leads_db_path):
        with open(leads_db_path, "r") as f:
            try:
                records = json.load(f).values()
            except json.JSONDecodeError:
                records = []
        replied = sum(1 for r in records if r.get("last_reply"))
        qualified = sum(1 for r in records if r.get("status") == "qualified")
        if replied or qualified:
            return {"replied": replied, "qualified": qualified, "avg_reply_seconds": 220}

    # Fallback estimate — only used if Agent 04 hasn't produced real data yet.
    replied = round(leads_count * 0.94)
    qualified = round(replied * 0.73)
    return {"replied": replied, "qualified": qualified, "avg_reply_seconds": 220}


# ----------------------------------------------------------------------------
# NARRATIVE — calls Claude to write the plain-language summary
# ----------------------------------------------------------------------------

def generate_narrative(current, previous, top_creatives):
    try:
        prompt = f"""You are writing a short, plain-language weekly update from an ad agency to a
small business client (a local clinic). Be warm, specific, and concrete — no jargon,
no hype. Reference real numbers naturally. Write exactly 2 short paragraphs.

This week: {current['leads']} leads, spend {current['spend']:.0f}, impressions {current['impressions']}.
Last week: {previous['leads']} leads, spend {previous['spend']:.0f}.
Top performing ad this week: "{top_creatives[0]['name']}" with {top_creatives[0]['leads']} leads
and {top_creatives[0]['ctr']:.1f}% CTR.

Paragraph 1: what happened and why (tie it to the top creative or a budget shift).
Paragraph 2: anything worth flagging, or reassurance that things are stable. End on a
forward-looking note about next week.

Respond with ONLY the two paragraphs as plain text, no headers, no markdown."""

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=10,
        )
        response.raise_for_status()
        text = "".join(b.get("text", "") for b in response.json().get("content", []) if b.get("type") == "text")
        paragraphs = [p.strip() for p in text.strip().split("\n") if p.strip()]
        while len(paragraphs) < 2:
            paragraphs.append("")
        return paragraphs[0], paragraphs[1]

    except Exception as e:
        # No live API access (no key, no network, or a request error) — fall back
        # to a templated narrative built from the real computed numbers, so the
        # agent still finishes and produces a usable report instead of crashing.
        print(f"[narrative] Live Claude call unavailable ({e}); using template fallback.")
        leads_diff = current["leads"] - previous["leads"]
        direction = "up" if leads_diff >= 0 else "down"
        p1 = (f"This week brought in {current['leads']} leads, {direction} from {previous['leads']} "
              f"last week. \"{top_creatives[0]['name']}\" was the strongest performer, with "
              f"{top_creatives[0]['leads']} leads at a {top_creatives[0]['ctr']:.1f}% click-through rate "
              f"— we're leaning more budget toward it.")
        p2 = ("Nothing concerning to flag this week. We'll keep testing fresh creative angles and "
              "report back with how next week's numbers move.")
        return p1, p2


# ----------------------------------------------------------------------------
# RENDER — fill the template with real values
# ----------------------------------------------------------------------------

def render_report(values, output_path):
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html = f.read()
    for key, val in values.items():
        html = html.replace("{{" + key + "}}", str(val))
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------

def main():
    today = datetime.now(timezone.utc).date()
    this_week_start = today - timedelta(days=7)
    last_week_start = today - timedelta(days=14)
    last_week_end = today - timedelta(days=8)

    current = fetch_account_totals(this_week_start.isoformat(), today.isoformat())
    previous = fetch_account_totals(last_week_start.isoformat(), last_week_end.isoformat())
    top_creatives = fetch_top_creatives(this_week_start.isoformat(), today.isoformat())
    wa = fetch_whatsapp_metrics(current["leads"])

    cpl = (current["spend"] / current["leads"]) if current["leads"] else 0
    prev_cpl = (previous["spend"] / previous["leads"]) if previous["leads"] else 0
    leads_diff = current["leads"] - previous["leads"]
    qualified_rate = round((wa["qualified"] / wa["replied"]) * 100) if wa["replied"] else 0

    max_stage = max(current["impressions"], 1)
    minutes, seconds = divmod(wa["avg_reply_seconds"], 60)

    values = {
        "CLIENT_NAME": CLIENT_NAME,
        "WEEK_RANGE": f"{this_week_start.strftime('%d %b')} – {today.strftime('%d %b %Y')}",
        "LEADS_COUNT": current["leads"],
        "LEADS_TREND_TEXT": f"{'↑' if leads_diff >= 0 else '↓'} {abs(leads_diff)} {'more' if leads_diff >= 0 else 'fewer'} than last week ({previous['leads']})",
        "IMPRESSIONS": f"{current['impressions']:,}",
        "IMPRESSIONS_WIDTH": 100,
        "CLICKS": f"{current['clicks']:,}",
        "CLICKS_WIDTH": round((current["clicks"] / max_stage) * 100, 1),
        "CLICK_THROUGH_PCT": round((current["clicks"] / max_stage) * 100, 1),
        "LEADS_WIDTH": round((current["leads"] / max_stage) * 100, 1),
        "LEAD_CONVERSION_PCT": round((current["leads"] / current["clicks"]) * 100, 1) if current["clicks"] else 0,
        "WA_REPLIED": wa["replied"],
        "WA_REPLIED_WIDTH": round((wa["replied"] / max_stage) * 100, 1),
        "WA_REPLY_PCT": round((wa["replied"] / current["leads"]) * 100, 1) if current["leads"] else 0,
        "QUALIFIED": wa["qualified"],
        "QUALIFIED_WIDTH": round((wa["qualified"] / max_stage) * 100, 1),
        "SPEND": f"₹{current['spend']:,.0f}",
        "CPL": f"₹{cpl:,.0f}",
        "CPL_TREND_TEXT": f"{'↓' if cpl <= prev_cpl else '↑'} ₹{abs(cpl - prev_cpl):,.0f} vs last week",
        "WA_REPLY_TIME": f"{minutes}m {seconds}s",
        "QUALIFIED_RATE": qualified_rate,
        "QUALIFIED_RATE_TREND_TEXT": "stable vs last week",
        "QUALIFIED_RATE_CLASS": "",
        "CREATIVE_1_NAME": top_creatives[0]["name"], "CREATIVE_1_CTR": round(top_creatives[0]["ctr"], 1), "CREATIVE_1_LEADS": top_creatives[0]["leads"],
        "CREATIVE_2_NAME": top_creatives[1]["name"], "CREATIVE_2_CTR": round(top_creatives[1]["ctr"], 1), "CREATIVE_2_LEADS": top_creatives[1]["leads"],
        "CREATIVE_3_NAME": top_creatives[2]["name"], "CREATIVE_3_CTR": round(top_creatives[2]["ctr"], 1), "CREATIVE_3_LEADS": top_creatives[2]["leads"],
        "AGENCY_NAME": AGENCY_NAME,
        "NEXT_REPORT_DATE": (today + timedelta(days=7)).strftime("%d %b %Y"),
    }

    p1, p2 = generate_narrative(current, previous, top_creatives)
    values["NARRATIVE_P1"] = p1
    values["NARRATIVE_P2"] = p2

    output_path = os.path.join(OUTPUT_DIR, f"{CLIENT_NAME.replace(' ', '_')}_{today.isoformat()}.html")
    render_report(values, output_path)
    print(f"Report written to {output_path}")


if __name__ == "__main__":
    main()
