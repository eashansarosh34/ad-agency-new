"""
AGENT 23 — Conversational WhatsApp Qualifier
================================================

The gap this closes: most "WhatsApp agents" (n8n/Make style) just fire a
fixed template and dump the reply into a sheet. This holds an actual
back-and-forth conversation — it reads what the lead says, decides what
to ask next based on THAT, and works toward a real qualification
decision, the way a good salesperson would.

Why it's ahead, not just present:
  - It doesn't follow a fixed script. Claude decides the next message
    based on the whole conversation so far.
  - It tracks a qualification goal (budget? timeline? real intent?) and
    steers toward it naturally instead of interrogating.
  - It knows when to STOP and hand to a human — a hot lead ready to buy,
    or a question it shouldn't answer alone, both trigger handoff.
  - Every conversation state is persisted, so it survives restarts and
    the human can pick up exactly where the AI left off.

This runs as a webhook receiver: WhatsApp sends an incoming message,
this decides the reply, sends it back. Meta's Cloud API delivers the
messages; Claude drives the conversation.

HARD SAFETY RULES (enforced in code, not just prompt):
  - Never sends more than MAX_MESSAGES_PER_LEAD without human review
    (prevents an endless bot loop annoying a real person)
  - Always hands off — never tries to close the sale itself
  - Logs every message for the human to audit
"""

import os
import json
import requests
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_API_URL = os.environ.get("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "my_verify_token")
GRAPH_URL = os.environ.get("META_API_URL", "https://graph.facebook.com/v21.0")
CONVERSATIONS_DB = "conversations_db.json"
CLIENT_NAME = os.environ.get("CLIENT_NAME", "our business")
CLIENT_CONTEXT = os.environ.get("CLIENT_CONTEXT",
    "a local business offering services to customers")

MAX_MESSAGES_PER_LEAD = 6  # hard cap — bot never sends more than this without human
PORT = int(os.environ.get("WHATSAPP_AGENT_PORT", 8010))
DRY_RUN = os.environ.get("WHATSAPP_AGENT_DRY_RUN", "true").lower() != "false"


def load_conversations():
    if not os.path.exists(CONVERSATIONS_DB):
        return {}
    with open(CONVERSATIONS_DB) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_conversations(convos):
    with open(CONVERSATIONS_DB, "w") as f:
        json.dump(convos, f, indent=2)


SYSTEM_PROMPT = f"""You are a warm, human-sounding assistant for {CLIENT_NAME} ({CLIENT_CONTEXT}),
talking to a potential customer on WhatsApp who just enquired via an ad.

Your ONLY job is to have a natural, friendly conversation that gently qualifies whether this
is a real, ready customer — and then hand off to a human teammate to close. You are NOT a
salesperson and you must NEVER try to close a deal, quote final prices, or make promises.

What you're trying to learn, naturally, across the conversation (not all at once, not like a form):
- Are they a real person with genuine interest (vs. a mis-click or spam)?
- Roughly what do they want / what's their situation?
- Any sense of urgency or timeline?

Rules:
- Sound like a friendly human on WhatsApp. Short messages. No corporate tone. No essays.
- Ask ONE thing at a time. React to what they actually said.
- The moment they seem ready to buy, ask a pricing/commercial question, or the conversation
  needs a real decision — you MUST hand off. To hand off, respond with ONLY the exact token
  [HANDOFF] followed by a one-line reason. Do not say anything else.
- If they're clearly not interested or it's spam, respond with ONLY [DISQUALIFY] and a reason.
- Never invent details about the business you don't know. If asked something specific you're
  unsure of, hand off rather than guess.
- Never discuss anything unrelated to their enquiry.

Respond with ONLY the message text to send them, OR [HANDOFF]/[DISQUALIFY] plus reason."""


def decide_reply(conversation_history):
    """Claude reads the whole conversation and decides the next move."""
    if not ANTHROPIC_API_KEY:
        return "[HANDOFF] No AI available — routing to human."

    messages = []
    for turn in conversation_history:
        role = "user" if turn["from"] == "lead" else "assistant"
        messages.append({"role": role, "content": turn["text"]})

    try:
        resp = requests.post(
            ANTHROPIC_API_URL,
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                     "Content-Type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 300,
                  "system": SYSTEM_PROMPT, "messages": messages},
            timeout=30,
        )
        resp.raise_for_status()
        return "".join(b.get("text", "") for b in resp.json().get("content", []) if b.get("type") == "text").strip()
    except Exception as e:
        return f"[HANDOFF] AI error ({e}) — routing to human."


def send_whatsapp_message(phone, text):
    if DRY_RUN:
        print(f"[DRY RUN] Would send to {phone}: {text}")
        return True
    try:
        resp = requests.post(
            f"{GRAPH_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"},
            json={"messaging_product": "whatsapp", "to": phone,
                  "type": "text", "text": {"body": text}},
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[agent-23] Send failed: {e}")
        return False


def handle_incoming(phone, message_text):
    """Core logic: an incoming lead message comes in, decide + send a reply."""
    convos = load_conversations()
    convo = convos.get(phone, {"phone": phone, "status": "active", "history": [],
                                "bot_messages_sent": 0,
                                "started_at": datetime.now(timezone.utc).isoformat()})

    if convo["status"] in ("handoff", "disqualified"):
        print(f"[agent-23] {phone} already {convo['status']} — bot stays silent, human owns this now.")
        return

    convo["history"].append({"from": "lead", "text": message_text,
                             "at": datetime.now(timezone.utc).isoformat()})

    # HARD GUARDRAIL: bot never exceeds message cap without human
    if convo["bot_messages_sent"] >= MAX_MESSAGES_PER_LEAD:
        convo["status"] = "handoff"
        convo["handoff_reason"] = f"Hit {MAX_MESSAGES_PER_LEAD}-message limit — handing to human to continue."
        convos[phone] = convo
        save_conversations(convos)
        print(f"[agent-23] {phone} hit message cap → HANDOFF to human.")
        _notify_owner_handoff(phone, convo)
        return

    decision = decide_reply(convo["history"])

    if decision.startswith("[HANDOFF]"):
        convo["status"] = "handoff"
        convo["handoff_reason"] = decision.replace("[HANDOFF]", "").strip()
        print(f"[agent-23] {phone} → HANDOFF: {convo['handoff_reason']}")
        _notify_owner_handoff(phone, convo)
    elif decision.startswith("[DISQUALIFY]"):
        convo["status"] = "disqualified"
        convo["disqualify_reason"] = decision.replace("[DISQUALIFY]", "").strip()
        print(f"[agent-23] {phone} → DISQUALIFIED: {convo['disqualify_reason']}")
    else:
        # Normal conversational reply
        sent = send_whatsapp_message(phone, decision)
        if sent:
            convo["history"].append({"from": "bot", "text": decision,
                                     "at": datetime.now(timezone.utc).isoformat()})
            convo["bot_messages_sent"] += 1

    convos[phone] = convo
    save_conversations(convos)


def _notify_owner_handoff(phone, convo):
    """Tell the human a lead is ready for them, with full context."""
    owner = os.environ.get("AGENCY_OWNER_WHATSAPP", "")
    transcript = "\n".join(f"{'Them' if t['from']=='lead' else 'Bot'}: {t['text']}"
                           for t in convo["history"])
    msg = (f"🔔 Lead ready for you: {phone}\n"
           f"Reason: {convo.get('handoff_reason','ready to talk')}\n\n"
           f"Conversation so far:\n{transcript}")
    if owner and not DRY_RUN:
        try:
            requests.post(f"{GRAPH_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages",
                headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"},
                json={"messaging_product": "whatsapp", "to": owner, "type": "text",
                      "text": {"body": msg[:4000]}}, timeout=15)
        except Exception as e:
            print(f"[agent-23] Owner notify failed: {e}")
    else:
        print(f"[agent-23] (owner handoff notice)\n{msg}\n")


class WebhookHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Meta webhook verification handshake
        from urllib.parse import urlparse, parse_qs
        params = parse_qs(urlparse(self.path).query)
        if params.get("hub.verify_token", [""])[0] == VERIFY_TOKEN:
            challenge = params.get("hub.challenge", [""])[0].encode()
            self.send_response(200); self.end_headers(); self.wfile.write(challenge)
        else:
            self.send_response(403); self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length))
            for entry in payload.get("entry", []):
                for change in entry.get("changes", []):
                    for msg in change.get("value", {}).get("messages", []):
                        if msg.get("type") == "text":
                            handle_incoming(msg["from"], msg["text"]["body"])
        except Exception as e:
            print(f"[agent-23] Webhook error: {e}")
        self.send_response(200); self.end_headers()

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    import sys
    if "--simulate" in sys.argv:
        # Offline test: simulate a full conversation without WhatsApp/webhook
        print("=== SIMULATED CONVERSATION ===")
        test_phone = "919999999999"
        for lead_msg in ["hi saw your ad", "yeah i need help with my taxes this month",
                          "ok whats the price", "sounds good when can we start"]:
            print(f"\nThem: {lead_msg}")
            handle_incoming(test_phone, lead_msg)
    else:
        print(f"Agent 23 (Conversational WhatsApp) on http://localhost:{PORT} (DRY_RUN={DRY_RUN})")
        HTTPServer(("localhost", PORT), WebhookHandler).serve_forever()
