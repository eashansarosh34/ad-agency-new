"""
AGENT 09 — Email Nurture Sequence
====================================

What this does:
  Generates a 3-part nurture email sequence personalized to a qualified
  lead's interest (using Claude, same pattern as Agent 01), then sends
  each email on schedule (day 0, day 3, day 7) — a slower-burn channel
  than WhatsApp, aimed at leads who gave an email address and haven't
  converted yet.

Before this can run for real, you need:
  1. A Brevo account (generous free tier, simple API — other ESPs like
     SendGrid/Mailchimp work too, just change the send function below)
  2. A Brevo API key from Settings -> SMTP & API
  3. A verified sending domain with SPF/DKIM set up in Brevo, or emails
     land in spam regardless of how good the copy is
  4. An Anthropic API key for live generation (falls back to a template
     if missing, same pattern as every other agent here)
  5. `pip install requests --break-system-packages`

SAFETY DEFAULT: DRY_RUN = True. Sequences generate and schedule normally,
but no real email sends until you disable this.
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta, timezone

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "PASTE_YOUR_BREVO_KEY")
BREVO_API_URL = os.environ.get("BREVO_API_URL", "https://api.brevo.com/v3/smtp/email")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "hello@yourclinic.example")
SENDER_NAME = os.environ.get("SENDER_NAME", "Aura Dental Clinic")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
LEADS_DB_PATH = os.environ.get("LEADS_DB_PATH", "leads_db.json")

SEQUENCE_SCHEDULE_DAYS = [0, 3, 7]  # send timing for email 1, 2, 3

DRY_RUN = True  # <-- flip to False only once domain auth + Brevo are both confirmed


# ----------------------------------------------------------------------------
# LEAD STORE
# ----------------------------------------------------------------------------

def load_leads():
    if not os.path.exists(LEADS_DB_PATH):
        return {}
    with open(LEADS_DB_PATH, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_leads(leads):
    with open(LEADS_DB_PATH, "w") as f:
        json.dump(leads, f, indent=2)

def upsert_lead(lead_id, **fields):
    leads = load_leads()
    record = leads.get(lead_id, {"lead_id": lead_id})
    record.update(fields)
    leads[lead_id] = record
    save_leads(leads)
    return record


# ----------------------------------------------------------------------------
# GENERATION — same Claude-with-fallback pattern as Agents 01/03/05/06
# ----------------------------------------------------------------------------

def generate_sequence(name, interest_service):
    prompt = f"""Write a 3-email nurture sequence for a dental clinic lead named {name}
who showed interest in: {interest_service or "general dental care"}.
They haven't booked an appointment yet. Tone: warm, helpful, not pushy.

Email 1 (sent immediately): build trust, answer a common concern about this service.
Email 2 (sent 3 days later): social proof / what to expect, gentle nudge to book.
Email 3 (sent 7 days later): a clear, low-pressure offer to book, with urgency that
feels genuine, not fake.

Respond with ONLY a raw JSON array, no markdown. Each item exactly:
{{"subject": "...", "body": "..."}}"""

    try:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError("no API key set")
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                     "Content-Type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 1200,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        response.raise_for_status()
        text = "".join(b.get("text", "") for b in response.json().get("content", []) if b.get("type") == "text")
        cleaned = text.replace("```json", "").replace("```", "").strip()
        emails = json.loads(cleaned)
    except Exception as e:
        print(f"[agent-09] Live generation unavailable ({e}); using template fallback.")
        service = interest_service or "an appointment"
        booking_phrase = f"book your {service} appointment" if interest_service else "book an appointment"
        emails = [
            {"subject": f"Quick answer about {service}", "body": f"Hi {name}, just following up on your interest in {service} — happy to answer any questions before you decide anything."},
            {"subject": "What other patients say", "body": f"Hi {name}, lots of patients felt nervous before their first visit too — most say it was easier than expected. Happy to walk you through what to expect."},
            {"subject": "Ready when you are", "body": f"Hi {name}, no pressure at all — just wanted to leave the door open if you'd like to {booking_phrase} this week."},
        ]

    for i, email in enumerate(emails):
        email["day_offset"] = SEQUENCE_SCHEDULE_DAYS[i] if i < len(SEQUENCE_SCHEDULE_DAYS) else SEQUENCE_SCHEDULE_DAYS[-1]
        email["sent"] = False
        email["sent_at"] = None
    return emails


def generate_for_lead(lead_id, email_address):
    leads = load_leads()
    lead = leads.get(lead_id)
    if not lead:
        print(f"[agent-09] No lead found with ID {lead_id}.")
        return
    sequence = generate_sequence(lead.get("name", "there"), lead.get("interest_service"))
    upsert_lead(lead_id, email=email_address, nurture_emails=sequence,
                nurture_generated_at=datetime.now(timezone.utc).isoformat())
    print(f"[agent-09] Generated a {len(sequence)}-email sequence for {lead_id} ({lead.get('name')}).")
    for i, e in enumerate(sequence):
        print(f"  Email {i+1} (day {e['day_offset']}): {e['subject']}")


# ----------------------------------------------------------------------------
# RECURRING NEWSLETTER — different audience and purpose from the nurture
# sequence above: this goes to existing/past customers on a regular cadence,
# not to new leads who haven't converted yet.
# ----------------------------------------------------------------------------

def generate_newsletter(business_name, topic, audience):
    prompt = f"""Write a monthly newsletter email for "{business_name}".
Topic/theme this month: {topic}
Audience: {audience} (existing/past customers, not new leads)
Tone: warm, useful, not salesy — should feel worth opening next month too.
Keep it genuinely short — one useful tip or update, not a sales pitch.

Respond with ONLY raw JSON, no markdown: {{"subject": "...", "body": "..."}}"""

    try:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError("no API key set")
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 600,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        response.raise_for_status()
        text = "".join(b.get("text", "") for b in response.json().get("content", []) if b.get("type") == "text")
        cleaned = text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except Exception as e:
        print(f"[agent-09] Live generation unavailable ({e}); using template fallback.")
        return {"subject": f"This month at {business_name}",
                "body": f"Hi there — quick update from {business_name} on {topic}. "
                        f"Thanks for being a valued customer, see you again soon."}


def send_newsletter_to_list(recipient_emails, business_name, topic, audience):
    """recipient_emails: list of {"email": ..., "name": ...} dicts — pull this
    from wherever you maintain a customer list (a CRM export, or extend this
    to read from leads_db.json filtered to a 'customer' status if you add one)."""
    newsletter = generate_newsletter(business_name, topic, audience)
    print(f"[agent-09] Newsletter: \"{newsletter['subject']}\"")
    sent = 0
    for r in recipient_emails:
        send_email(r["email"], r.get("name", "there"), newsletter["subject"], newsletter["body"])
        sent += 1
    print(f"[agent-09] Newsletter {'would be ' if DRY_RUN else ''}sent to {sent} recipient(s).")


# ----------------------------------------------------------------------------
# SENDING
# ----------------------------------------------------------------------------

def send_email(to_email, to_name, subject, body):
    if DRY_RUN:
        print(f"[DRY RUN] Would email {to_name} <{to_email}>: \"{subject}\"")
        return {"dry_run": True}

    payload = {
        "sender": {"email": SENDER_EMAIL, "name": SENDER_NAME},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": f"<p>{body}</p>",
    }
    headers = {"api-key": BREVO_API_KEY, "Content-Type": "application/json"}
    response = requests.post(BREVO_API_URL, headers=headers, json=payload, timeout=20)
    response.raise_for_status()
    return response.json()


def send_due_nurture_emails():
    leads = load_leads()
    now = datetime.now(timezone.utc)
    sent_count = 0

    for lead_id, record in leads.items():
        sequence = record.get("nurture_emails")
        generated_at_str = record.get("nurture_generated_at")
        email_address = record.get("email")
        if not sequence or not generated_at_str or not email_address:
            continue

        generated_at = datetime.fromisoformat(generated_at_str)
        changed = False
        for email in sequence:
            if email["sent"]:
                continue
            due_at = generated_at + timedelta(days=email["day_offset"])
            if now >= due_at:
                send_email(email_address, record.get("name", "there"), email["subject"], email["body"])
                email["sent"] = True
                email["sent_at"] = now.isoformat()
                changed = True
                sent_count += 1
                break  # one email per lead per run, keeps sequence order honest

        if changed:
            upsert_lead(lead_id, nurture_emails=sequence)

    if sent_count == 0:
        print("[agent-09] No nurture emails due in this run.")
    return sent_count


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "--generate":
        generate_for_lead(sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 2 and sys.argv[1] == "--send-due":
        print(f"--- Agent 09 run: {datetime.now(timezone.utc).isoformat()} (DRY_RUN={DRY_RUN}) ---")
        send_due_nurture_emails()
    elif len(sys.argv) >= 4 and sys.argv[1] == "--newsletter":
        # Quick test path: comma-separated emails, e.g. "a@x.com:Name,b@y.com:Name2"
        business, topic, audience = sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "customers"
        recipients_raw = sys.argv[5] if len(sys.argv) > 5 else ""
        recipients = []
        for entry in recipients_raw.split(","):
            if ":" in entry:
                email, name = entry.split(":", 1)
                recipients.append({"email": email, "name": name})
        send_newsletter_to_list(recipients, business, topic, audience)
    else:
        print("Usage:\n"
              "  python3 agent_09_email_nurture.py --generate <lead_id> <email_address>\n"
              "  python3 agent_09_email_nurture.py --send-due   (put this on a cron, e.g. daily)\n"
              "  python3 agent_09_email_nurture.py --newsletter \"<business>\" \"<topic>\" \"<audience>\" \"a@x.com:Name,b@y.com:Name2\"")
