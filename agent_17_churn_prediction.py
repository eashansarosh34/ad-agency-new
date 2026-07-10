"""
AGENT 17 — Churn Prediction
==============================

Watches for the signals that a client is about to leave — before they
say anything. Reads three things no agency currently watches
systematically: whether the client is opening reports, whether replies
are getting shorter, and whether campaign performance has been trending
down long enough without a creative refresh.

When signals cluster, it generates a specific recommended action to take
this week — not "check in more often," but exactly what to do.

Reads from: leads_db.json (lead/performance context), report_open_log.json
(needs to be written when you send reports — see below), client_notes.json
(optional short log of client reply content length/sentiment).

Usage:
  python3 agent_17_churn_prediction.py
"""

import os
import json
import requests
from datetime import datetime, timezone, timedelta

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CHURN_LOG = "churn_signals.json"

# These files track signals over time — you write to them when relevant
# events happen (report sent, reply received, CPL checked).
REPORT_OPEN_LOG = os.environ.get("REPORT_OPEN_LOG", "report_open_log.json")
CLIENT_NOTES_LOG = os.environ.get("CLIENT_NOTES_LOG", "client_notes.json")
PERFORMANCE_LOG = os.environ.get("PERFORMANCE_LOG", "performance_log.json")


def load_json_file(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def log_report_open(client_id, opened=True):
    """Call this when you send a report and when you confirm it was opened."""
    log = load_json_file(REPORT_OPEN_LOG)
    log.append({"client_id": client_id, "timestamp": datetime.now(timezone.utc).isoformat(), "opened": opened})
    with open(REPORT_OPEN_LOG, "w") as f:
        json.dump(log, f, indent=2)


def log_client_reply(client_id, reply_word_count, sentiment="neutral"):
    """Call this after each client communication — just the word count and rough sentiment."""
    log = load_json_file(CLIENT_NOTES_LOG)
    log.append({"client_id": client_id, "timestamp": datetime.now(timezone.utc).isoformat(),
                "word_count": reply_word_count, "sentiment": sentiment})
    with open(CLIENT_NOTES_LOG, "w") as f:
        json.dump(log, f, indent=2)


def log_performance(client_id, cpl, leads):
    """Call this after each optimizer run or report generation."""
    log = load_json_file(PERFORMANCE_LOG)
    log.append({"client_id": client_id, "timestamp": datetime.now(timezone.utc).isoformat(),
                "cpl": cpl, "leads": leads})
    with open(PERFORMANCE_LOG, "w") as f:
        json.dump(log, f, indent=2)


def compute_churn_signals(client_id, lookback_weeks=4):
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=lookback_weeks)
    signals = []
    score = 0  # 0-100 risk score

    # Signal 1: Report open rate
    report_log = [r for r in load_json_file(REPORT_OPEN_LOG)
                  if r["client_id"] == client_id and
                  datetime.fromisoformat(r["timestamp"]) > cutoff]
    if report_log:
        open_rate = sum(1 for r in report_log if r["opened"]) / len(report_log)
        if open_rate < 0.4:
            signals.append(f"Report open rate only {open_rate:.0%} in the last {lookback_weeks} weeks — client may be disengaging")
            score += 30
        elif open_rate < 0.7:
            signals.append(f"Report open rate {open_rate:.0%} — below healthy threshold")
            score += 15

    # Signal 2: Reply length trend
    reply_log = [r for r in load_json_file(CLIENT_NOTES_LOG)
                 if r["client_id"] == client_id and
                 datetime.fromisoformat(r["timestamp"]) > cutoff]
    if len(reply_log) >= 3:
        recent_avg = sum(r["word_count"] for r in reply_log[-2:]) / 2
        earlier_avg = sum(r["word_count"] for r in reply_log[:2]) / 2
        if recent_avg < earlier_avg * 0.5:
            signals.append(f"Reply length dropped sharply: {earlier_avg:.0f} words → {recent_avg:.0f} words recently")
            score += 25
        negative_replies = [r for r in reply_log if r.get("sentiment") == "negative"]
        if negative_replies:
            signals.append(f"{len(negative_replies)} negative-sentiment reply/replies in recent communications")
            score += 20 * len(negative_replies)

    # Signal 3: CPL trend
    perf_log = [p for p in load_json_file(PERFORMANCE_LOG)
                if p["client_id"] == client_id and
                datetime.fromisoformat(p["timestamp"]) > cutoff]
    if len(perf_log) >= 3:
        recent_cpls = [p["cpl"] for p in perf_log[-3:] if p["cpl"]]
        if len(recent_cpls) >= 2:
            trend = (recent_cpls[-1] - recent_cpls[0]) / recent_cpls[0]
            if trend > 0.3:
                signals.append(f"CPL has risen {trend:.0%} over the last {len(perf_log)} checks without a creative refresh")
                score += 25
            elif trend > 0.15:
                signals.append(f"CPL trending up {trend:.0%} — worth flagging proactively")
                score += 10

    score = min(score, 100)
    risk_level = "HIGH" if score >= 60 else "MEDIUM" if score >= 30 else "LOW"

    return {
        "client_id": client_id,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "risk_score": score,
        "risk_level": risk_level,
        "signals": signals,
    }


def recommend_action(result):
    if not ANTHROPIC_API_KEY:
        # Simple rule-based fallback
        if result["risk_level"] == "HIGH":
            return ("⚠ HIGH RISK — call this client this week, not a message. "
                    "Offer a free creative refresh and ask directly what they're hoping to see more of.")
        elif result["risk_level"] == "MEDIUM":
            return ("Book a check-in this week. Share one specific win from the last report "
                    "before discussing anything that isn't going well.")
        else:
            return "No action needed this week. Keep current cadence."

    prompt = f"""You manage a client relationship for a digital marketing agency.
Here are the churn risk signals detected for this client:

Risk score: {result['risk_score']}/100 ({result['risk_level']} risk)
Signals: {result['signals']}

Write ONE specific, actionable thing to do THIS WEEK to reduce this client's churn risk.
Not general advice — a specific action with a specific message or framing.
3 sentences maximum. Plain language only."""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                     "Content-Type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 150,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=20,
        )
        resp.raise_for_status()
        return "".join(b.get("text", "") for b in resp.json().get("content", []) if b.get("type") == "text")
    except Exception as e:
        return f"Action recommendation unavailable ({e})"


def run_churn_check(client_ids):
    print(f"--- Agent 17 Churn Check: {datetime.now(timezone.utc).isoformat()} ---")
    results = []
    for cid in client_ids:
        result = compute_churn_signals(cid)
        result["recommended_action"] = recommend_action(result)
        results.append(result)
        risk_icon = "🔴" if result["risk_level"] == "HIGH" else "🟡" if result["risk_level"] == "MEDIUM" else "🟢"
        print(f"\n{risk_icon} {cid}: {result['risk_level']} risk (score {result['risk_score']}/100)")
        if result["signals"]:
            for s in result["signals"]:
                print(f"   • {s}")
        print(f"   → {result['recommended_action']}")

    existing = load_json_file(CHURN_LOG)
    existing.extend(results)
    with open(CHURN_LOG, "w") as f:
        json.dump(existing, f, indent=2)
    return results


if __name__ == "__main__":
    # Seed some realistic test data so the agent has something to evaluate
    log_report_open("SunCap", opened=True)
    log_report_open("SunCap", opened=False)
    log_report_open("SunCap", opened=False)
    log_client_reply("SunCap", reply_word_count=120, sentiment="neutral")
    log_client_reply("SunCap", reply_word_count=85, sentiment="neutral")
    log_client_reply("SunCap", reply_word_count=22, sentiment="negative")
    log_performance("SunCap", cpl=280, leads=18)
    log_performance("SunCap", cpl=310, leads=16)
    log_performance("SunCap", cpl=390, leads=11)

    log_report_open("RoldGold", opened=True)
    log_report_open("RoldGold", opened=True)
    log_client_reply("RoldGold", reply_word_count=200, sentiment="positive")
    log_client_reply("RoldGold", reply_word_count=180, sentiment="positive")
    log_performance("RoldGold", cpl=180, leads=42)
    log_performance("RoldGold", cpl=165, leads=48)

    run_churn_check(["SunCap", "RoldGold"])
