"""
AGENT 04b — Lead Poller (webhook alternative)
=================================================

What this does:
  Instead of waiting for Meta to push new leads to a webhook (which needs
  a tunnel + the subscribed_apps linking step), this asks Meta directly:
  "any new leads on this Page?" — on a schedule, e.g. every few minutes.
  Same data, far less fragile setup. Once a lead is found, it runs the
  exact same intake (save + send WhatsApp template) as the webhook would.

Before this can run for real, you need:
  1. A Page Access Token with the `leads_retrieval` permission — the one
     you already generated in Graph API Explorer for SunCap.
  2. Your Page ID (we already have this: 1260680110451105).
  3. `pip install requests --break-system-packages`

This deliberately reuses the same leads_db.json and send_whatsapp_template
logic as agent_04_whatsapp.py, so reports/Agent 03 work identically either
way — only how leads arrive is different.

SAFETY DEFAULT: DRY_RUN = True, same pattern as everything else.
"""

import os
import json
import requests
from datetime import datetime, timezone

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "PASTE_YOUR_PAGE_TOKEN")
PAGE_ID = os.environ.get("META_PAGE_ID", "1260680110451105")
GRAPH_URL = os.environ.get("META_API_URL", "https://graph.facebook.com/v21.0")
LEADS_DB_PATH = os.environ.get("LEADS_DB_PATH", "leads_db.json")

DRY_RUN = True  # <-- flip to False only once you trust this on a real account


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


def get_lead_forms():
    url = f"{GRAPH_URL}/{PAGE_ID}/leadgen_forms"
    resp = requests.get(url, params={"access_token": PAGE_ACCESS_TOKEN}, timeout=20)
    if not resp.ok:
        print(f"[agent-04b] Meta's actual error response: {resp.text}")
    resp.raise_for_status()
    return resp.json().get("data", [])


def get_leads_for_form(form_id):
    url = f"{GRAPH_URL}/{form_id}/leads"
    resp = requests.get(url, params={"access_token": PAGE_ACCESS_TOKEN}, timeout=20)
    if not resp.ok:
        print(f"[agent-04b] Meta's actual error response: {resp.text}")
    resp.raise_for_status()
    return resp.json().get("data", [])


def parse_lead_fields(field_data):
    """Meta returns answers as a list of {name, values} — flatten to a dict."""
    parsed = {}
    for field in field_data:
        name = field.get("name", "").lower()
        values = field.get("values", [])
        parsed[name] = values[0] if values else ""
    return parsed


def send_whatsapp_template(phone, name):
    if DRY_RUN:
        print(f"[DRY RUN] Would send WhatsApp template to {phone} ({name}).")
        return
    # Real send would go here — same as agent_04_whatsapp.py's version.
    print(f"[agent-04b] (Real send not wired here — copy send logic from agent_04_whatsapp.py once ready.)")


def poll_for_new_leads():
    leads_db = load_leads()
    forms = get_lead_forms()
    print(f"[agent-04b] Found {len(forms)} lead form(s) on this Page.")

    new_count = 0
    for form in forms:
        form_id = form["id"]
        raw_leads = get_leads_for_form(form_id)
        print(f"[agent-04b] Form {form_id} ('{form.get('name','')}') has {len(raw_leads)} total lead(s).")

        for raw in raw_leads:
            lead_id = raw["id"]
            if lead_id in leads_db:
                continue  # already processed

            fields = parse_lead_fields(raw.get("field_data", []))
            name = fields.get("full_name") or fields.get("name") or "there"
            phone = fields.get("phone_number") or fields.get("phone") or ""

            leads_db[lead_id] = {
                "lead_id": lead_id, "name": name, "phone": phone,
                "status": "contacted", "interest_service": None, "last_reply": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            send_whatsapp_template(phone, name)
            new_count += 1
            print(f"[agent-04b] NEW lead: {name} ({phone})")

    save_leads(leads_db)
    if new_count == 0:
        print("[agent-04b] No new leads this run.")
    return new_count


if __name__ == "__main__":
    print(f"--- Agent 04b poll: {datetime.now(timezone.utc).isoformat()} (DRY_RUN={DRY_RUN}) ---")
    try:
        poll_for_new_leads()
    except Exception as _e:
        print(f"[agent_04b_lead_poller] Poll could not run - likely missing/invalid Page token or permissions. Details: {_e}")
        import sys; sys.exit(0)
