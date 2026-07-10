"""
AGENT 08 — SMS Appointment Reminder
======================================

What this does:
  Scans leads with a scheduled appointment and sends an SMS reminder in
  the window before it's due — the highest-fit SMS use case for this
  niche (cuts no-shows), and a natural companion to the WhatsApp flow.

Before this can run for real, you need:
  1. DLT registration completed (see the roadmap doc — entity, then a
     header/sender ID, then this specific message template, each
     separately approved). This is the long pole, not the code.
  2. An SMS gateway account — this targets MSG91 (popular India-specific
     provider, handles DLT template linkage cleanly). Get an auth key
     from the MSG91 dashboard once your DLT template is approved there.
  3. The MSG91 Template ID for your approved reminder template — the
     message text sent MUST match the approved template exactly (with
     only the variable slots filled in) or it silently fails delivery.
     This is the #1 real-world failure mode for this channel.
  4. `pip install requests --break-system-packages`

SAFETY DEFAULT: DRY_RUN = True. Reminders are computed and logged, but no
real SMS is sent until you disable this.
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta, timezone

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------

MSG91_AUTH_KEY = os.environ.get("MSG91_AUTH_KEY", "PASTE_YOUR_AUTH_KEY")
MSG91_TEMPLATE_ID = os.environ.get("MSG91_TEMPLATE_ID", "PASTE_DLT_APPROVED_TEMPLATE_ID")
MSG91_API_URL = os.environ.get("MSG91_API_URL", "https://control.msg91.com/api/v5/flow")

LEADS_DB_PATH = os.environ.get("LEADS_DB_PATH", "leads_db.json")
REMINDER_WINDOW_HOURS = 24  # send if appointment is within this many hours and not yet reminded

DRY_RUN = True  # <-- flip to False only once DLT + MSG91 template are both approved and tested


# ----------------------------------------------------------------------------
# LEAD STORE — same file Agent 04 and Agent 03 read from
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
# SCHEDULING — a manual step, since there's no real booking system yet
# ----------------------------------------------------------------------------

def schedule_appointment(lead_id, appointment_time_str):
    leads = load_leads()
    if lead_id not in leads:
        print(f"[agent-08] No lead found with ID {lead_id}.")
        return
    try:
        datetime.fromisoformat(appointment_time_str)
    except ValueError:
        print("[agent-08] Use ISO format, e.g. 2026-06-26T15:30:00")
        return
    upsert_lead(lead_id, appointment_time=appointment_time_str, reminder_sent=False)
    print(f"[agent-08] Appointment for {lead_id} scheduled at {appointment_time_str}.")


# ----------------------------------------------------------------------------
# SENDING — must match the DLT-approved template exactly
# ----------------------------------------------------------------------------

def send_sms_reminder(phone, name, appointment_time_str):
    appointment_dt = datetime.fromisoformat(appointment_time_str)
    display_time = appointment_dt.strftime("%d %b, %I:%M %p")

    if DRY_RUN:
        print(f"[DRY RUN] Would send SMS reminder to {phone} ({name}) for appointment at {display_time}")
        return {"dry_run": True}

    if "PASTE_" in MSG91_TEMPLATE_ID:
        print("[agent-08] MSG91_TEMPLATE_ID not set — get this from MSG91 once your DLT template is approved.")
        return {"error": "no template configured"}

    payload = {
        "template_id": MSG91_TEMPLATE_ID,
        "short_url": "0",
        "realTimeResponse": "1",
        "recipients": [{
            "mobiles": phone,
            # These variable names must match exactly what's defined in your
            # approved DLT template — common pattern is VAR1, VAR2, etc.
            "VAR1": name,
            "VAR2": display_time,
        }],
    }
    headers = {"authkey": MSG91_AUTH_KEY, "Content-Type": "application/json"}
    response = requests.post(MSG91_API_URL, headers=headers, json=payload, timeout=20)
    response.raise_for_status()
    return response.json()


def send_due_reminders():
    leads = load_leads()
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(hours=REMINDER_WINDOW_HOURS)
    sent_count = 0

    for lead_id, record in leads.items():
        appt_str = record.get("appointment_time")
        if not appt_str or record.get("reminder_sent"):
            continue
        try:
            appt_dt = datetime.fromisoformat(appt_str)
        except ValueError:
            continue

        if now <= appt_dt <= window_end:
            send_sms_reminder(record["phone"], record.get("name", "there"), appt_str)
            upsert_lead(lead_id, reminder_sent=True, reminder_sent_at=now.isoformat())
            print(f"[agent-08] Reminder sent for {lead_id} ({record.get('name')}).")
            sent_count += 1

    if sent_count == 0:
        print("[agent-08] No reminders due in this window.")
    return sent_count


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "--schedule":
        schedule_appointment(sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 2 and sys.argv[1] == "--send-reminders":
        print(f"--- Agent 08 run: {datetime.now(timezone.utc).isoformat()} (DRY_RUN={DRY_RUN}) ---")
        send_due_reminders()
    else:
        print("Usage:\n"
              "  python3 agent_08_sms_reminder.py --schedule <lead_id> <ISO_datetime>\n"
              "  python3 agent_08_sms_reminder.py --send-reminders   (put this on a cron, e.g. hourly)")
