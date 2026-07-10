"""
AGENT 04 — WhatsApp Lead Qualifier
====================================

What this does:
  Receives a webhook the instant Meta generates a new lead, sends that lead
  a WhatsApp template message asking which service they want, then receives
  their reply, classifies them as qualified/unqualified, extracts what
  service they're interested in, and saves it — completing the funnel that
  Agent 03 reports on.

Before this can run for real, you need:
  1. A WhatsApp Business Platform number connected via Meta (Cloud API
     directly, or a wrapper like AiSensy/Wati — this code targets the
     Cloud API directly since AiSensy/Wati sit on top of it anyway).
  2. A permanent access token with `whatsapp_business_messaging` permission,
     and your Phone Number ID (from Meta's WhatsApp Manager).
  3. At least one APPROVED message template (Meta requires this for the
     first business-initiated message — you cannot free-text a stranger).
  4. A webhook subscription pointed at this server's /webhook path, with a
     VERIFY_TOKEN you choose and your app's secret for signature checks.
  5. `pip install requests --break-system-packages` (stdlib handles the
     server itself — no Flask needed).

SAFETY DEFAULT: DRY_RUN = True. Incoming webhooks are still processed and
leads still get saved/classified, but no real WhatsApp message is sent
until you set this to False.
"""

import os
import json
import hmac
import hashlib
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import requests

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "PASTE_YOUR_TOKEN_HERE")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "PASTE_PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("WEBHOOK_VERIFY_TOKEN", "choose-your-own-verify-token")
META_APP_SECRET = os.environ.get("META_APP_SECRET", "")  # required for real signature checks
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

GRAPH_URL = os.environ.get("META_API_URL", "https://graph.facebook.com/v21.0")
LEADS_DB_PATH = os.environ.get("LEADS_DB_PATH", "leads_db.json")
PORT = int(os.environ.get("AGENT_04_PORT", 8002))

# For the review-request feature — get this from the client's Google Business
# Profile: search the business on Google Maps, click Share, copy the link, or
# build it as https://search.google.com/local/writereview?placeid=THEIR_PLACE_ID
GOOGLE_REVIEW_LINK = os.environ.get("GOOGLE_REVIEW_LINK", "PASTE_CLIENT_GOOGLE_REVIEW_LINK")

DRY_RUN = True  # <-- flip to False only once a real template + token are wired up

SERVICE_KEYWORDS = ["implant", "root canal", "cleaning", "braces", "whitening",
                    "consultation", "checkup", "extraction"]
NEGATIVE_KEYWORDS = ["not interested", "stop", "no thanks", "unsubscribe", "remove me"]


# ----------------------------------------------------------------------------
# LEAD STORE — shared with Agent 03, which reads this for real WhatsApp metrics
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
# SECURITY — verifies the request really came from Meta
# ----------------------------------------------------------------------------

def verify_signature(body_bytes, signature_header):
    if not META_APP_SECRET:
        print("[WARN] META_APP_SECRET not set — rejecting, cannot verify request authenticity.")
        return False
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(META_APP_SECRET.encode(), body_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


# ----------------------------------------------------------------------------
# OUTBOUND — sending WhatsApp messages
# ----------------------------------------------------------------------------

def send_whatsapp_template(to_phone, lead_name):
    """First message to a new lead must use a pre-approved template."""
    if DRY_RUN:
        print(f"[DRY RUN] Would send WhatsApp template to {to_phone} ({lead_name}) "
              f"asking which service they're interested in.")
        return {"dry_run": True}

    url = f"{GRAPH_URL}/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "template",
        "template": {
            "name": "lead_qualifier_intro",  # must match a template approved in WhatsApp Manager
            "language": {"code": "en"},
            "components": [{"type": "body", "parameters": [{"type": "text", "text": lead_name}]}],
        },
    }
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json=payload, timeout=15)
    response.raise_for_status()
    return response.json()


def send_whatsapp_text(to_phone, text):
    """Free-text replies are allowed within 24h of the lead replying to us."""
    if DRY_RUN:
        print(f"[DRY RUN] Would reply to {to_phone}: \"{text}\"")
        return {"dry_run": True}

    url = f"{GRAPH_URL}/{PHONE_NUMBER_ID}/messages"
    payload = {"messaging_product": "whatsapp", "to": to_phone, "type": "text", "text": {"body": text}}
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json=payload, timeout=15)
    response.raise_for_status()
    return response.json()


# ----------------------------------------------------------------------------
# CLASSIFICATION — qualify the lead from their reply text
# ----------------------------------------------------------------------------

def classify_reply(text):
    """Returns (status, interest_service). Tries Claude first, falls back to
    keyword matching if there's no live API access — never crashes either way."""
    try:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError("no API key set")
        prompt = (f'A lead replied to a dental clinic WhatsApp message with: "{text}"\n'
                   'Respond with ONLY raw JSON, no markdown: '
                   '{"qualified": true or false, "interest_service": "short string or null"}')
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                     "Content-Type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 100,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=10,
        )
        response.raise_for_status()
        raw = "".join(b.get("text", "") for b in response.json().get("content", []) if b.get("type") == "text")
        parsed = json.loads(raw.replace("```json", "").replace("```", "").strip())
        return ("qualified" if parsed.get("qualified") else "unqualified"), parsed.get("interest_service")

    except Exception as e:
        print(f"[classify] Live Claude call unavailable ({e}); using keyword fallback.")
        lowered = text.lower()
        if any(neg in lowered for neg in NEGATIVE_KEYWORDS):
            return "unqualified", None
        found_service = next((kw for kw in SERVICE_KEYWORDS if kw in lowered), None)
        return "qualified", found_service


# ----------------------------------------------------------------------------
# WEBHOOK HANDLERS
# ----------------------------------------------------------------------------

class WebhookHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print("[agent-04]", fmt % args)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length)

    def _respond(self, code, body_dict=None, plain_text=None):
        self.send_response(code)
        if plain_text is not None:
            body = plain_text.encode()
            self.send_header("Content-Type", "text/plain")
        else:
            body = json.dumps(body_dict or {}).encode()
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # Meta's webhook verification handshake, run once when you register the webhook URL.
        parsed = urlparse(self.path)
        if parsed.path == "/webhook":
            params = parse_qs(parsed.query)
            mode = params.get("hub.mode", [None])[0]
            token = params.get("hub.verify_token", [None])[0]
            challenge = params.get("hub.challenge", [""])[0]
            if mode == "subscribe" and token == VERIFY_TOKEN:
                self._respond(200, plain_text=challenge)
            else:
                self._respond(403, plain_text="Verification failed")
            return
        self._respond(404, {"error": "not found"})

    def do_POST(self):
        body_bytes = self._read_body()
        signature = self.headers.get("X-Hub-Signature-256", "")

        if not verify_signature(body_bytes, signature):
            print("[SECURITY] Rejected request with invalid/missing signature.")
            self._respond(401, {"error": "invalid signature"})
            return

        try:
            payload = json.loads(body_bytes.decode("utf-8"))
        except json.JSONDecodeError:
            self._respond(400, {"error": "invalid json"})
            return

        parsed = urlparse(self.path)

        if parsed.path == "/webhook/meta-lead":
            self._handle_new_lead(payload)
        elif parsed.path == "/webhook/whatsapp-reply":
            self._handle_reply(payload)
        else:
            self._respond(404, {"error": "not found"})
            return

        self._respond(200, {"success": True})

    # -- lead creation -----------------------------------------------------
    def _handle_new_lead(self, payload):
        lead_id = str(payload.get("lead_id", ""))
        name = payload.get("name", "there")
        phone = payload.get("phone", "")
        if not lead_id or not phone:
            print("[agent-04] Lead payload missing lead_id or phone — skipping.")
            return

        upsert_lead(lead_id, name=name, phone=phone, status="contacted",
                    interest_service=payload.get("interest_service"), last_reply=None)
        send_whatsapp_template(phone, name)
        print(f"[agent-04] New lead {lead_id} ({name}) contacted.")

    # -- reply handling ------------------------------------------------------
    def _handle_reply(self, payload):
        # Real Meta WhatsApp webhook shape: entry[0].changes[0].value.messages[0]
        try:
            message = payload["entry"][0]["changes"][0]["value"]["messages"][0]
            from_phone = message["from"]
            text = message["text"]["body"]
        except (KeyError, IndexError):
            print("[agent-04] Reply payload didn't match expected shape — skipping.")
            return

        leads = load_leads()
        lead_id = next((lid for lid, rec in leads.items() if rec.get("phone") == from_phone), None)
        if not lead_id:
            print(f"[agent-04] No matching lead for phone {from_phone} — skipping.")
            return

        status, interest_service = classify_reply(text)
        upsert_lead(lead_id, status=status, last_reply=text,
                    interest_service=interest_service or leads[lead_id].get("interest_service"))

        if status == "qualified":
            send_whatsapp_text(from_phone, "Thanks! The clinic will reach out shortly to confirm your appointment.")
            print(f"[agent-04] Lead {lead_id} QUALIFIED — interested in: {interest_service}")
        else:
            send_whatsapp_text(from_phone, "No problem — feel free to reach out anytime if that changes.")
            print(f"[agent-04] Lead {lead_id} marked unqualified.")


# ----------------------------------------------------------------------------
# REVIEW REQUEST — deliberately a manual trigger, not a timer
# ----------------------------------------------------------------------------
# Asking for a review only makes sense once you actually know the visit
# happened. There's no real "appointment completed" signal from Meta or
# WhatsApp, so this is a one-off command you run yourself once the clinic
# confirms the patient showed up — never an automatic timer, which risks
# asking someone "how was your visit?" when they never actually came in.

def send_review_request(lead_id):
    leads = load_leads()
    lead = leads.get(lead_id)

    if not lead:
        print(f"[agent-04] No lead found with ID {lead_id}.")
        return
    if lead.get("status") != "qualified":
        print(f"[agent-04] Lead {lead_id} is not marked qualified (status: {lead.get('status')}) — "
              f"refusing to send a review request. Override only if you're sure this is correct.")
        return
    if lead.get("review_requested"):
        print(f"[agent-04] Lead {lead_id} was already sent a review request on "
              f"{lead.get('review_requested_at')} — not sending a second one.")
        return
    if "PASTE_CLIENT" in GOOGLE_REVIEW_LINK:
        print("[agent-04] GOOGLE_REVIEW_LINK isn't set yet — get the real review link from the "
              "client's Google Business Profile before running this.")
        return

    name = lead.get("name", "there")
    message = (f"Hi {name}, thanks for visiting! If you have a minute, a quick Google review "
               f"would really help us — {GOOGLE_REVIEW_LINK}")
    send_whatsapp_text(lead["phone"], message)
    upsert_lead(lead_id, review_requested=True, review_requested_at=datetime.now(timezone.utc).isoformat())
    print(f"[agent-04] Review request sent to {name} ({lead_id}).")


def send_broadcast(status_filter, message):
    """
    Sends one message to every lead matching a status filter (e.g. 'qualified').
    Deliberately requires typed confirmation before sending — a bulk send is
    much harder to undo than a single message, so this should never fire
    without a human explicitly reviewing exactly who it's about to reach.
    """
    leads = load_leads()
    targets = [(lid, rec) for lid, rec in leads.items() if rec.get("status") == status_filter]

    if not targets:
        print(f"[agent-04] No leads found with status '{status_filter}'.")
        return

    print(f"[agent-04] This will send to {len(targets)} lead(s) with status '{status_filter}':")
    for lid, rec in targets:
        print(f"  - {rec.get('name', 'unknown')} ({rec.get('phone', 'no phone')})")
    print(f"\nMessage: \"{message}\"")

    if not DRY_RUN:
        confirm = input(f"\nType the number {len(targets)} to confirm sending to all of them: ")
        if confirm.strip() != str(len(targets)):
            print("[agent-04] Confirmation didn't match — broadcast cancelled, nothing sent.")
            return

    sent = 0
    for lid, rec in targets:
        send_whatsapp_text(rec["phone"], message)
        sent += 1
    print(f"[agent-04] Broadcast complete — {sent} message(s) {'would be ' if DRY_RUN else ''}sent.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--request-review":
        if len(sys.argv) < 3:
            print("Usage: python3 agent_04_whatsapp.py --request-review <lead_id>")
        else:
            send_review_request(sys.argv[2])
    elif len(sys.argv) > 1 and sys.argv[1] == "--broadcast":
        if len(sys.argv) < 4:
            print('Usage: python3 agent_04_whatsapp.py --broadcast <status_filter> "<message>"\n'
                  '  e.g. --broadcast qualified "New offer this month: ..."\n'
                  'NOTE: real broadcast/marketing-category WhatsApp messages need a pre-approved\n'
                  'template, same as the first-contact message, and Meta bills these per-conversation\n'
                  '- this is not free bulk messaging. Also only message leads who replied to you\n'
                  'within the platform\'s messaging window, or who explicitly opted in.')
        else:
            send_broadcast(sys.argv[2], sys.argv[3])
    else:
        server = HTTPServer(("localhost", PORT), WebhookHandler)
        print(f"Agent 04 (WhatsApp Qualifier) running on http://localhost:{PORT} (DRY_RUN={DRY_RUN})")
        server.serve_forever()
