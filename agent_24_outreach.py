"""
AGENT 24 — Outbound Outreach System
=======================================

The gap this closes: you currently do outbound BY HAND — finding brands
on Reddit, reading their post, writing a custom reply. That works but
doesn't scale past your own hours. This systematizes exactly that motion:
find prospects, understand each one, draft a genuinely personalized first
message that proves you read their specific situation.

Why it's ahead, not spam: the n8n-style "outreach system" blasts the same
templated DM to 500 people. This does the opposite — it reads each
prospect's actual content and writes a message that could ONLY have been
written for them. Personalization at the quality of hand-writing, at the
speed of automation. That's the whole difference between outreach that
works and outreach that gets you banned.

IMPORTANT — this drafts, it does NOT auto-send. Every message is queued
for your review and you send it yourself. This is deliberate:
  1. Cold-DM automation violates most platforms' terms and gets accounts
     banned. Human-sent messages don't.
  2. A person should always eyeball a cold message before it goes out.
So this is a force-multiplier for your judgment, not a replacement for it.

Workflow:
  1. You give it a source of prospects (a list of brand descriptions,
     or it can use Tavily to find businesses in a niche/city)
  2. It researches/reads each one
  3. It drafts a personalized opener + notes WHY that angle
  4. You review the queue and send the good ones yourself
"""

import os
import json
import requests
from datetime import datetime, timezone

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_API_URL = os.environ.get("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
TAVILY_API_URL = os.environ.get("TAVILY_API_URL", "https://api.tavily.com/search")
OUTREACH_QUEUE = "outreach_queue.json"


def find_prospects(niche, city, max_results=5):
    """Use Tavily to find real businesses in a niche/city that might need marketing help."""
    if not TAVILY_API_KEY:
        print("[agent-24] No Tavily key — skipping auto-discovery. Feed prospects manually instead.")
        return []
    query = f"small {niche} businesses in {city} instagram"
    resp = requests.post(TAVILY_API_URL, json={
        "api_key": TAVILY_API_KEY, "query": query,
        "search_depth": "basic", "max_results": max_results,
    }, timeout=20)
    resp.raise_for_status()
    return [{"source": "tavily", "title": r.get("title"), "url": r.get("url"),
             "description": r.get("content", "")[:400]} for r in resp.json().get("results", [])]


def draft_outreach(prospect):
    """Read one prospect's actual situation, draft a message only they could receive."""
    if not ANTHROPIC_API_KEY:
        return {"draft": "(no AI available)", "angle": "n/a", "quality_flag": "skipped"}

    prompt = f"""You run a performance marketing agency for Indian small businesses. You're writing
a FIRST cold outreach message to this specific prospect. Here's what you know about them:

Business: {prospect.get('title', 'unknown')}
What they do / their situation: {prospect.get('description', '')}
{f"Their own words: {prospect['their_words']}" if prospect.get('their_words') else ""}

Write a short, warm, genuinely personalized first message (WhatsApp/DM length, 3-4 sentences
max) that:
- Proves you actually looked at THEIR specific business (reference something real about them)
- Names one specific, plausible way you could help them — not generic "grow your business"
- Is humble and curious, not salesy. You're starting a conversation, not pitching a package.
- Sounds like a real person, not a marketing bot. No buzzwords.
- Does NOT mention price, does NOT oversell, does NOT make guarantees

Also decide: is this actually a good-fit prospect worth reaching out to, or a poor fit
(wrong business type, too big, location mismatch, unclear they need ads)?

Respond with ONLY raw JSON, no markdown:
{{"draft": "the message", "angle": "one line: the specific hook you used and why",
  "fit": "good" or "poor", "fit_reason": "why"}}"""

    try:
        resp = requests.post(
            ANTHROPIC_API_URL,
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                     "Content-Type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 400,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        resp.raise_for_status()
        raw = "".join(b.get("text", "") for b in resp.json().get("content", []) if b.get("type") == "text")
        return json.loads(raw.replace("```json", "").replace("```", "").strip())
    except Exception as e:
        return {"draft": f"(error: {e})", "angle": "n/a", "fit": "unknown", "fit_reason": str(e)}


def build_outreach_queue(prospects):
    """Draft messages for a batch of prospects, queue good-fits for human review."""
    queue = []
    if os.path.exists(OUTREACH_QUEUE):
        with open(OUTREACH_QUEUE) as f:
            try:
                queue = json.load(f)
            except json.JSONDecodeError:
                queue = []

    new_count = 0
    for prospect in prospects:
        result = draft_outreach(prospect)
        entry = {
            "queued_at": datetime.now(timezone.utc).isoformat(),
            "prospect": prospect.get("title", "unknown"),
            "url": prospect.get("url", ""),
            "draft_message": result.get("draft"),
            "angle": result.get("angle"),
            "fit": result.get("fit", "unknown"),
            "fit_reason": result.get("fit_reason", ""),
            "status": "awaiting_your_review",  # you send it, not the bot
        }
        queue.append(entry)
        new_count += 1
        fit_icon = "✅" if result.get("fit") == "good" else "⏭️" if result.get("fit") == "poor" else "❓"
        print(f"\n{fit_icon} {entry['prospect']} [{result.get('fit','?')} fit]")
        print(f"   Angle: {entry['angle']}")
        print(f"   Draft: {entry['draft_message']}")
        if result.get("fit") == "poor":
            print(f"   (Poor fit: {result.get('fit_reason')} — review before sending)")

    with open(OUTREACH_QUEUE, "w") as f:
        json.dump(queue, f, indent=2)
    print(f"\n[agent-24] {new_count} drafts added to {OUTREACH_QUEUE}. "
          f"Review them and send the good ones YOURSELF — nothing auto-sends.")
    return queue


if __name__ == "__main__":
    # Test with realistic manually-fed prospects (like the Reddit ones you handle now)
    test_prospects = [
        {"title": "epixsave — 3D printed animal lamps",
         "description": "Small D2C brand making cute 3D-printed animal lamps (cats, ducks). "
                        "USB-C powered, ₹799-899. Founder-run, just launched first 6 designs. "
                        "Selling via Instagram DMs, wants more reach.",
         "their_words": "I am launching my first set of 6 designs, would love feedback and reach"},
        {"title": "Generic SEO Agency Ltd",
         "description": "A large established 200-person SEO agency with offices in three cities "
                        "and their own marketing team.",
         "their_words": ""},
    ]
    build_outreach_queue(test_prospects)
