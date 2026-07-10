"""
AGENT 20 — A/B Creative Intelligence
========================================

What this does:
  Every week, reads real ad performance data, identifies which creative
  angle is winning and why, and sends the client one plain-language
  WhatsApp message telling them exactly what happened and what we're
  doing about it — without them having to ask, open a dashboard, or
  understand a single marketing term.

  "Your before/after style ad got 3x more enquiries than the product
  photo this week. We're putting more budget toward it. Nothing you
  need to do."

  That sentence builds more trust than any report. Most agencies don't
  do this because it takes someone's time. This does it automatically,
  every Monday morning, while you're still asleep.

Run as part of the scheduler (weekly), or manually:
  python3 agent_20_creative_intelligence.py
"""

import os
import json
import requests
from datetime import datetime, timedelta, timezone

META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")
META_AD_ACCOUNT_ID = os.environ.get("META_AD_ACCOUNT_ID", "act_XXXXXXXXXXXX")
META_API_URL = os.environ.get("META_API_URL", "https://graph.facebook.com/v21.0")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLIENT_NAME = os.environ.get("CLIENT_NAME", "your brand")
CLIENT_WHATSAPP = os.environ.get("CLIENT_WHATSAPP", "") or os.environ.get("BUDGET_CEILING_WHATSAPP", "")  # prefer CLIENT_WHATSAPP; fall back to old name
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
DRY_RUN = True


def fetch_ad_performance(days=7):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    until = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = f"{META_API_URL}/{META_AD_ACCOUNT_ID}/insights"
    params = {
        "access_token": META_ACCESS_TOKEN,
        "level": "ad",
        "fields": "ad_id,ad_name,spend,actions,ctr,impressions",
        "time_range": json.dumps({"since": since, "until": until}),
        "limit": 50,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json().get("data", [])

    ads = []
    for row in data:
        spend = float(row.get("spend", 0))
        leads = sum(int(a.get("value", 0)) for a in row.get("actions", [])
                    if a.get("action_type") in ("lead", "onsite_conversion.lead_grouped"))
        cpl = round(spend / leads, 0) if leads else None
        ads.append({
            "name": row.get("ad_name", "Unnamed ad"),
            "spend": spend,
            "leads": leads,
            "cpl": cpl,
            "ctr": float(row.get("ctr", 0)),
            "impressions": int(row.get("impressions", 0)),
        })
    return sorted(ads, key=lambda x: x["leads"], reverse=True)


def generate_brief(ads, client_name):
    if not ads:
        return f"Hey! Quick update on {client_name}'s campaign this week — ads are running but still collecting early data. We'll have a clearer picture next week."

    top = ads[0]
    worst = ads[-1] if len(ads) > 1 else None

    if ANTHROPIC_API_KEY:
        ads_summary = "\n".join(
            f"- '{a['name']}': {a['leads']} leads, CPL ₹{a['cpl'] or 'N/A'}, CTR {a['ctr']:.1f}%"
            for a in ads[:5]
        )
        prompt = f"""Write a short WhatsApp message (4-5 sentences MAX) from a marketing agency
to a small business client named {client_name}. The message explains what happened
with their ads this week, in completely plain language — no jargon, no acronyms,
no marketing terms.

Ad performance this week:
{ads_summary}

Rules:
- Start with what's WORKING (the winner)
- Say what we're DOING about it (more budget to winner, less to loser)
- If there's a losing ad, explain briefly what probably caused it
- End with "Nothing you need to do" or "Let us know if you have questions"
- Tone: friendly, confident, like a trusted friend who handles this for you
- NO emojis, NO bullet points, PLAIN TEXT only
- Must fit in a WhatsApp message — SHORT"""

        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                         "Content-Type": "application/json"},
                json={"model": "claude-sonnet-4-6", "max_tokens": 200,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=20,
            )
            resp.raise_for_status()
            return "".join(b.get("text", "") for b in resp.json().get("content", []) if b.get("type") == "text")
        except Exception as e:
            print(f"[agent-20] Live generation failed ({e}), using template.")

    # Fallback template — always works even without API key
    msg = f"Quick update on {client_name}'s campaign this week. "
    if top["leads"] > 0:
        msg += f"Your '{top['name']}' ad got the most enquiries ({top['leads']} leads"
        if top["cpl"]:
            msg += f", ₹{top['cpl']:.0f} each"
        msg += "), so we've shifted more budget toward it. "
    if worst and worst["leads"] == 0 and worst["name"] != top["name"]:
        msg += f"The '{worst['name']}' ad didn't generate enquiries this week, so we've paused it to focus budget where it's working. "
    msg += "Nothing you need to do — we're on it."
    return msg


def send_whatsapp(phone, message):
    if DRY_RUN:
        print(f"[DRY RUN] Would send WhatsApp to {phone}:")
        print(f"  {message}")
        return
    try:
        requests.post(
            f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"},
            json={"messaging_product": "whatsapp", "to": phone,
                  "type": "text", "text": {"body": message}},
            timeout=15,
        ).raise_for_status()
        print(f"[agent-20] WhatsApp brief sent to {phone}")
    except Exception as e:
        print(f"[agent-20] WhatsApp send failed: {e}")


def run(mock_ads=None):
    print(f"--- Agent 20 run: {datetime.now(timezone.utc).isoformat()} (DRY_RUN={DRY_RUN}) ---")

    if mock_ads:
        ads = mock_ads
        print(f"[agent-20] Using mock data ({len(ads)} ads)")
    elif not META_ACCESS_TOKEN:
        print("[agent-20] META_ACCESS_TOKEN not set — cannot fetch real data.")
        return
    else:
        ads = fetch_ad_performance()
        print(f"[agent-20] Fetched {len(ads)} ads")

    brief = generate_brief(ads, CLIENT_NAME)
    print(f"\n[agent-20] Weekly brief:\n{brief}\n")

    if CLIENT_WHATSAPP:
        send_whatsapp(CLIENT_WHATSAPP, brief)
    else:
        print("[agent-20] CLIENT_WHATSAPP not set — brief generated but not sent.")


if __name__ == "__main__":
    # Test with realistic mock data to confirm output quality
    mock_ads = [
        {"name": "Before/After Smile Makeover", "spend": 4200, "leads": 21, "cpl": 200, "ctr": 4.8, "impressions": 12000},
        {"name": "Free Consultation Weekend", "spend": 3100, "leads": 14, "cpl": 221, "ctr": 3.1, "impressions": 8500},
        {"name": "Generic Clinic Photo", "spend": 2900, "leads": 0, "cpl": None, "ctr": 0.8, "impressions": 7200},
    ]
    run(mock_ads=mock_ads)
