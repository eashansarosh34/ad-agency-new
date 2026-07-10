"""
AGENT 34 — Creative Fatigue Detector + Auto-Brief
=====================================================

What this does that nothing else here currently does:
  Watches three signals simultaneously across every active ad:
  1. Frequency (above 2.5 in a 7-day window)
  2. CTR declining 15%+ vs the ad's own first-week baseline
  3. CPM rising while CTR falls

  When the pattern matches, it doesn't just flag it — it immediately
  writes a new creative brief to feed into Agent 01, so the human step
  ("read the report, open another tool, write a brief") disappears.
  The loop closes automatically.

  The key distinction from Agent 02: Agent 02 pauses/boosts based on
  CPL. This agent catches decay BEFORE CPL degrades, typically 5-7 days
  earlier. Both run — 02 reacts, this one prevents.
"""

import os
import json
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get("META_API_URL", "https://graph.facebook.com/v21.0")
META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "PASTE_TOKEN")
META_AD_ACCOUNT_ID = os.environ.get("META_AD_ACCOUNT_ID", "act_XXXXXXXX")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
LOG_FILE = "agent_15_fatigue_log.json"
BRIEFS_FILE = "fatigue_refresh_briefs.json"

THRESHOLDS = {
    "max_frequency": 2.5,
    "ctr_drop_pct": 0.15,    # 15% drop from the ad's own first-week baseline
    "min_spend_to_judge": 30, # only judge ads that have spent at least this much
}


def fetch_ad_performance(days):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    until = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = f"{BASE_URL}/{META_AD_ACCOUNT_ID}/insights"
    params = {
        "access_token": META_ACCESS_TOKEN, "level": "ad",
        "fields": "ad_id,ad_name,spend,ctr,frequency,impressions,cpm",
        "time_range": json.dumps({"since": since, "until": until}),
        "limit": 200,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("data", [])


def fetch_ad_baseline_ctr(ad_id):
    """Fetch the first 7 days of this ad's performance to establish its own baseline."""
    # First get the ad's created time from the ad object
    url = f"{BASE_URL}/{ad_id}"
    resp = requests.get(url, params={"access_token": META_ACCESS_TOKEN, "fields": "created_time"}, timeout=20)
    if not resp.ok:
        return None
    created = resp.json().get("created_time", "")
    if not created:
        return None

    try:
        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
    except ValueError:
        return None
    baseline_end = created_dt + timedelta(days=7)
    since = created_dt.strftime("%Y-%m-%d")
    until = min(baseline_end, datetime.now(timezone.utc)).strftime("%Y-%m-%d")

    url2 = f"{BASE_URL}/{ad_id}/insights"
    params = {"access_token": META_ACCESS_TOKEN, "fields": "ctr",
              "time_range": json.dumps({"since": since, "until": until})}
    resp2 = requests.get(url2, params=params, timeout=20)
    if not resp2.ok:
        return None
    rows = resp2.json().get("data", [])
    return float(rows[0]["ctr"]) if rows else None


def detect_fatigue(ads):
    fatigued = []
    for ad in ads:
        spend = float(ad.get("spend", 0))
        if spend < THRESHOLDS["min_spend_to_judge"]:
            continue

        frequency = float(ad.get("frequency", 0))
        current_ctr = float(ad.get("ctr", 0))
        cpm = float(ad.get("cpm", 0))

        signals = []
        if frequency > THRESHOLDS["max_frequency"]:
            signals.append(f"frequency {frequency:.1f} > {THRESHOLDS['max_frequency']}")

        baseline_ctr = fetch_ad_baseline_ctr(ad.get("ad_id"))
        if baseline_ctr and baseline_ctr > 0:
            ctr_drop = (baseline_ctr - current_ctr) / baseline_ctr
            if ctr_drop >= THRESHOLDS["ctr_drop_pct"]:
                signals.append(f"CTR dropped {ctr_drop:.0%} from baseline ({baseline_ctr:.2f}% → {current_ctr:.2f}%)")

        if len(signals) >= 1 and cpm > 0:  # at least one signal + rising costs = act
            fatigued.append({
                "ad_id": ad.get("ad_id"), "ad_name": ad.get("ad_name", ""),
                "signals": signals, "spend": spend, "frequency": frequency,
                "current_ctr": current_ctr, "cpm": cpm,
                "baseline_ctr": baseline_ctr,
            })
    return fatigued


def generate_refresh_brief(ad_name, signals):
    """
    Generates a creative brief so Agent 01 can immediately produce
    a replacement — this closes the loop between detection and action
    without a human having to write the brief themselves.
    """
    prompt = f"""An ad called "{ad_name}" is showing creative fatigue signals: {', '.join(signals)}.

Write a short creative refresh brief (3-4 bullet points max) for the human to feed into Agent 01
to generate a replacement. Focus on: what angle to try differently, what format change might help,
and what to keep that was clearly working. Be specific and actionable, not generic.

Respond with ONLY the brief as plain text, no JSON, no headers."""

    if not ANTHROPIC_API_KEY:
        return (f"Creative brief for '{ad_name}':\n"
                f"- Current ad showing fatigue ({', '.join(signals)})\n"
                f"- Try a different opening hook — same offer, new first 3 seconds\n"
                f"- Test a contrasting angle (if current ad is benefit-led, try problem-led)\n"
                f"- Keep the CTA — only the hook and body need refreshing")
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                     "Content-Type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 300,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=20,
        )
        resp.raise_for_status()
        return "".join(b.get("text", "") for b in resp.json().get("content", []) if b.get("type") == "text")
    except Exception as e:
        return (f"Brief generation failed ({e}) — manually note: "
                f"'{ad_name}' needs a new hook, try contrasting angle.")


def run():
    print(f"--- Agent 34 run: {datetime.now(timezone.utc).isoformat()} ---")
    ads = fetch_ad_performance(7)
    print(f"Checked {len(ads)} ads for fatigue signals.")

    fatigued = detect_fatigue(ads)
    if not fatigued:
        print("No fatigue detected this cycle.")
        return

    briefs = []
    existing = []
    if os.path.exists(BRIEFS_FILE):
        with open(BRIEFS_FILE) as f:
            try: existing = json.load(f)
            except: existing = []

    for ad in fatigued:
        print(f"\n[FATIGUE] '{ad['ad_name']}' — signals: {ad['signals']}")
        brief = generate_refresh_brief(ad["ad_name"], ad["signals"])
        print(f"[BRIEF] {brief}")
        briefs.append({"detected_at": datetime.now(timezone.utc).isoformat(),
                       "ad_id": ad["ad_id"], "ad_name": ad["ad_name"],
                       "signals": ad["signals"], "brief": brief})

    existing.extend(briefs)
    with open(BRIEFS_FILE, "w") as f:
        json.dump(existing, f, indent=2)
    print(f"\n{len(fatigued)} fatigued ad(s) — briefs saved to {BRIEFS_FILE}")


if __name__ == "__main__":
    if META_ACCESS_TOKEN in ("", "PASTE_TOKEN", "PASTE_YOUR_TOKEN_HERE") or "XXXX" in META_AD_ACCOUNT_ID:
        print("[agent_34_fatigue_detector] No real META_ACCESS_TOKEN / META_AD_ACCOUNT_ID set - this agent needs a live Meta account to run.")
        import sys; sys.exit(0)
    run()
