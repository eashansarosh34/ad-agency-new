"""
AGENT 22 — Human Escalation Layer
=====================================

What this is: the explicit, visible answer to "what do you do that AI
can't?" As Meta and Google automate more execution natively, the real
differentiator isn't running campaigns — it's knowing exactly when a
decision needs a human, and making that handoff visible and reliable
instead of hidden.

This agent doesn't run campaigns. It watches what OTHER agents detect
and decides: is this safe to let the automation handle, or does this
need a real person, right now? When it escalates, it sends YOU a
WhatsApp alert with full context — and optionally tells the CLIENT
"we caught this and a real person is on it" — which is the actual
trust-building feature in 2027's market, not another optimization.

Escalation triggers (each one maps to a real, specific risk category):
  - Compliance: Agent 12 flags a FLAGGED verdict — never auto-fix, always human review
  - Budget: Agent 02's Budget Guardian fires — ceiling hit, real money event
  - Churn: Agent 17 detects HIGH risk — relationship needs a human touch, not a bot
  - Competitive: Agent 14 detects a significant market shift — judgment call on response
  - Anomaly: performance moves more than expected in either direction — could be good
    news worth understanding or bad news worth catching early; either way, a human
    should look before assuming the automation has it handled

Usage: call escalate() from within other agents when their own trigger
conditions fire, OR run check_all_signals() on a schedule to scan recent
logs from every other agent for anything that should have escalated but
didn't get caught at the source.
"""

import os
import json
import requests
from datetime import datetime, timezone, timedelta

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
AGENCY_OWNER_WHATSAPP = os.environ.get("AGENCY_OWNER_WHATSAPP", "")  # YOUR number, not the client's
CLIENT_WHATSAPP = os.environ.get("BUDGET_CEILING_WHATSAPP", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
DRY_RUN = True

ESCALATION_LOG = "human_escalations.json"

SEVERITY_LEVELS = {
    "compliance": "HIGH",     # never auto-resolve — legal/regulatory risk
    "budget": "HIGH",         # real money already spent or about to be
    "churn": "MEDIUM",        # relationship risk, time-sensitive but not urgent-urgent
    "competitive": "LOW",     # informational, worth knowing, rarely time-critical
    "anomaly": "MEDIUM",      # could be good or bad — needs a human read either way
}


def escalate(category, client_name, summary, details=None, notify_client=False):
    """
    Call this from any other agent the moment it detects something that
    shouldn't be auto-resolved. This is the actual product feature —
    every escalation is logged, timestamped, and (when not in DRY_RUN)
    sent straight to the agency owner's own WhatsApp, with full context.
    """
    severity = SEVERITY_LEVELS.get(category, "MEDIUM")
    entry = {
        "escalated_at": datetime.now(timezone.utc).isoformat(),
        "category": category, "severity": severity,
        "client": client_name, "summary": summary, "details": details or {},
        "owner_notified": False, "client_notified": False,
    }

    print(f"\n{'🔴' if severity == 'HIGH' else '🟡' if severity == 'MEDIUM' else '🔵'} "
          f"HUMAN ESCALATION [{severity}] — {category.upper()} — {client_name}")
    print(f"   {summary}")

    owner_message = (f"⚠ {severity} priority — {client_name}\n"
                     f"Category: {category}\n"
                     f"{summary}\n\n"
                     f"This needs your judgment, not automation. Check it when you can.")

    if AGENCY_OWNER_WHATSAPP:
        if DRY_RUN:
            print(f"[DRY RUN] Would WhatsApp YOU ({AGENCY_OWNER_WHATSAPP}): {owner_message}")
        else:
            _send_whatsapp(AGENCY_OWNER_WHATSAPP, owner_message)
            entry["owner_notified"] = True
    else:
        print("[agent-22] AGENCY_OWNER_WHATSAPP not set — escalation logged but not sent. Set this to actually receive alerts.")

    # The trust-building client-facing message — optional, used sparingly,
    # only for things genuinely worth telling a client you caught.
    if notify_client and CLIENT_WHATSAPP:
        client_message = _generate_client_facing_message(category, summary)
        if DRY_RUN:
            print(f"[DRY RUN] Would WhatsApp CLIENT ({CLIENT_WHATSAPP}): {client_message}")
        else:
            _send_whatsapp(CLIENT_WHATSAPP, client_message)
            entry["client_notified"] = True

    _log_escalation(entry)
    return entry


def _generate_client_facing_message(category, summary):
    """The actual differentiator message — reassuring, not alarming, proves
    a real human is in the loop without exposing internal detail."""
    if not ANTHROPIC_API_KEY:
        return ("Quick note — our system flagged something on your account that needs a human look "
                "rather than letting automation handle it alone. We're on it, nothing for you to do.")

    prompt = f"""Write a SHORT WhatsApp message (2-3 sentences) to a marketing client, telling them
that something was flagged on their account and a real person (not just AI) is handling it.

Category: {category}
What was flagged (internal note, don't repeat technical details to client): {summary}

Tone: reassuring, confident, builds trust that humans are watching, not alarming.
Do NOT reveal specific numbers or technical details — just that it's being handled by a person.
Plain text, no jargon, no emojis."""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 120, "messages": [{"role": "user", "content": prompt}]},
            timeout=15,
        )
        resp.raise_for_status()
        return "".join(b.get("text", "") for b in resp.json().get("content", []) if b.get("type") == "text")
    except Exception:
        return "Quick note — something on your account needed a real person's judgment call. We caught it and are on it."


def _send_whatsapp(phone, message):
    try:
        requests.post(
            f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"},
            json={"messaging_product": "whatsapp", "to": phone, "type": "text", "text": {"body": message}},
            timeout=15,
        ).raise_for_status()
    except Exception as e:
        print(f"[agent-22] WhatsApp send failed: {e}")


def _log_escalation(entry):
    existing = []
    if os.path.exists(ESCALATION_LOG):
        with open(ESCALATION_LOG, "r") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []
    existing.append(entry)
    with open(ESCALATION_LOG, "w") as f:
        json.dump(existing, f, indent=2)


def weekly_escalation_summary():
    """Run weekly — shows the agency owner exactly what was caught and
    handled, building their own confidence in the system over time."""
    if not os.path.exists(ESCALATION_LOG):
        print("[agent-22] No escalations logged yet.")
        return
    with open(ESCALATION_LOG, "r") as f:
        all_escalations = json.load(f)

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    recent = [e for e in all_escalations if datetime.fromisoformat(e["escalated_at"]) > cutoff]

    print(f"\n--- Weekly Escalation Summary ({len(recent)} this week) ---")
    by_severity = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for e in recent:
        by_severity[e["severity"]] += 1
        print(f"  [{e['severity']}] {e['client']} — {e['category']}: {e['summary'][:80]}")
    print(f"\nBreakdown: {by_severity['HIGH']} high, {by_severity['MEDIUM']} medium, {by_severity['LOW']} low priority")


if __name__ == "__main__":
    # Demonstrate realistic escalations across each category
    escalate("compliance", "SunCap",
              "Agent 12 flagged ad copy: 'guaranteed returns' keyword match in financial_services category",
              details={"verdict": "FLAGGED"}, notify_client=True)

    escalate("budget", "SunCap",
              "Agent 02 Budget Guardian: spend hit ₹20,000 ceiling, all ads auto-paused",
              details={"ceiling": 20000}, notify_client=True)

    escalate("churn", "SunCap",
              "Agent 17 churn check: HIGH risk score 75/100 — report opens down, CPL rising, one negative reply",
              notify_client=False)

    escalate("competitive", "Aura Dental Clinic",
              "Agent 14 detected a new trend: competitor launched WhatsApp-first booking flow",
              notify_client=False)

    weekly_escalation_summary()
