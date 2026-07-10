"""
AGENT 11 — Lead Intelligence & Voice-of-Customer
====================================================

What this does, and why it's structurally different from a report:

  1. PRIORITIZATION — reads every lead's actual WhatsApp reply text and
     scores real buying intent, then ranks who you should personally call
     first. Not "oldest first" — "most likely to convert first." A human
     account manager could do this for 5 leads. At 50+, nobody does.

  2. VOICE-OF-CUSTOMER MINING — aggregates the real language your leads
     use (their objections, their exact phrasing) into a short brief you
     feed back into Agent 01, so new ad copy is written in your actual
     customers' words, not guesses about them. This is the loop most
     agencies never close, because reading every transcript by hand isn't
     worth a human's time — it's exactly worth an agent's time, since the
     marginal cost of reading one more conversation is zero.

Both pull from the same leads_db.json every other agent already writes to
— no new data collection, just synthesis nobody was doing before.

Setup: ANTHROPIC_API_KEY (falls back to a clearly-labeled simple heuristic
if missing, same pattern as every other agent here — never crashes silently).
"""

import os
import json
import requests

LEADS_DB_PATH = os.environ.get("LEADS_DB_PATH", "leads_db.json")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


def load_leads():
    if not os.path.exists(LEADS_DB_PATH):
        return {}
    with open(LEADS_DB_PATH, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def call_claude(prompt, max_tokens):
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("no API key set")
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                 "Content-Type": "application/json"},
        json={"model": "claude-sonnet-4-6", "max_tokens": max_tokens,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=30,
    )
    resp.raise_for_status()
    return "".join(b.get("text", "") for b in resp.json().get("content", []) if b.get("type") == "text")


# ----------------------------------------------------------------------------
# 1. PRIORITIZATION — who to call first, based on what they actually said
# ----------------------------------------------------------------------------

def score_and_rank_leads():
    leads = load_leads()
    repliers = {lid: rec for lid, rec in leads.items() if rec.get("last_reply")}

    if not repliers:
        print("[agent-11] No leads with replies yet — nothing to prioritize.")
        return []

    leads_text = "\n".join(
        f"- ID {lid}: name={rec.get('name')}, said: \"{rec.get('last_reply')}\""
        for lid, rec in repliers.items()
    )
    prompt = f"""These are real leads who replied on WhatsApp to a business's qualifying message:
{leads_text}

For each, score buying intent 1-10 based ONLY on what they actually said (urgency, specificity,
readiness language vs. vague/hesitant language), and give a one-sentence reason.

Respond with ONLY a raw JSON array, no markdown, sorted highest intent first. Each item:
{{"lead_id": "...", "name": "...", "intent_score": 0, "reason": "..."}}"""

    try:
        raw = call_claude(prompt, 800)
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        ranked = json.loads(cleaned)
    except Exception as e:
        print(f"[agent-11] Live scoring unavailable ({e}); using a simple keyword fallback.")
        urgent_words = ["asap", "today", "now", "urgent", "interested", "yes", "price", "cost", "when"]
        scored = []
        for lid, rec in repliers.items():
            text = rec.get("last_reply", "").lower()
            score = sum(2 for w in urgent_words if w in text) or 3
            scored.append({"lead_id": lid, "name": rec.get("name"), "intent_score": min(score, 10),
                            "reason": "Keyword fallback — no live scoring available."})
        ranked = sorted(scored, key=lambda x: x["intent_score"], reverse=True)

    print("\n[agent-11] CALL THESE FIRST, in this order:")
    for i, item in enumerate(ranked, 1):
        print(f"  {i}. {item['name']} (intent {item['intent_score']}/10) — {item['reason']}")
    return ranked


# ----------------------------------------------------------------------------
# 2. VOICE-OF-CUSTOMER — real language, fed back into the creative engine
# ----------------------------------------------------------------------------

def mine_voice_of_customer():
    leads = load_leads()
    replies = [rec["last_reply"] for rec in leads.values() if rec.get("last_reply")]

    if not replies:
        print("[agent-11] No reply text yet to mine.")
        return None

    replies_text = "\n".join(f"- \"{r}\"" for r in replies)
    prompt = f"""Here are real WhatsApp replies from leads to a business:
{replies_text}

Extract: (1) the most common objection or hesitation, in the customers' own words where possible,
(2) the most common phrase or way they describe what they want, (3) one specific suggestion for
how future ad copy could speak more directly to what these real people actually said.

Respond with ONLY raw JSON, no markdown:
{{"common_objection": "...", "common_phrasing": "...", "creative_suggestion": "..."}}"""

    try:
        raw = call_claude(prompt, 400)
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        brief = json.loads(cleaned)
    except Exception as e:
        print(f"[agent-11] Live mining unavailable ({e}); showing raw replies instead.")
        brief = {"common_objection": "(not analyzed — no live API access)",
                 "common_phrasing": "(not analyzed)",
                 "creative_suggestion": f"Raw replies for manual review: {replies}"}

    print("\n[agent-11] VOICE-OF-CUSTOMER BRIEF (feed this into Agent 01's next brief):")
    print(f"  Common objection: {brief['common_objection']}")
    print(f"  Common phrasing: {brief['common_phrasing']}")
    print(f"  Creative suggestion: {brief['creative_suggestion']}")
    return brief


if __name__ == "__main__":
    import sys
    if "--prioritize" in sys.argv:
        score_and_rank_leads()
    elif "--voice-brief" in sys.argv:
        mine_voice_of_customer()
    else:
        print("Usage:\n"
              "  python3 agent_11_lead_intelligence.py --prioritize\n"
              "  python3 agent_11_lead_intelligence.py --voice-brief")
