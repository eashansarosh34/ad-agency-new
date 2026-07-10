"""
AGENT 14 — Live Competitive-Shift Monitor
=============================================

What this does:
  Agent 05 (Trend Scout) answers "what's trending" when you ask. This
  agent runs on a schedule and only speaks up when something actually
  CHANGED since last time — a genuinely new source/angle appeared that
  wasn't there last run — and when it does, it immediately drafts ready
  creative concepts reacting to that shift, with zero manual step between
  "market moved" and "new copy ready to review." Nothing else at small-
  business tooling tier does this; AdCreative.ai-tier tools generate on
  request, they don't watch the market on their own.

Setup: same as Agent 05 — TAVILY_API_KEY + ANTHROPIC_API_KEY. Run this on
a schedule (e.g. daily) via the scheduler.

Run:
  python3 agent_14_competitive_monitor.py --niche "dental clinic ads India"
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime, timezone

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
TAVILY_API_URL = os.environ.get("TAVILY_API_URL", "https://api.tavily.com/search")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
STATE_FILE = os.environ.get("TREND_STATE_PATH", "trend_state.json")
OUTPUT_FILE = "new_concepts_from_trend_shift.json"


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def search_trends(niche, max_results=8):
    if not TAVILY_API_KEY:
        print("[agent-14] TAVILY_API_KEY not set — skipping live search.")
        return []
    resp = requests.post(TAVILY_API_URL, json={
        "api_key": TAVILY_API_KEY, "query": f"{niche} trending ad creative angles 2026",
        "search_depth": "basic", "max_results": max_results, "days": 14,  # short window — only recent
    }, timeout=20)
    resp.raise_for_status()
    return resp.json().get("results", [])


def detect_new_items(niche, current_results, state):
    seen_urls = set(state.get(niche, {}).get("seen_urls", []))
    new_items = [r for r in current_results if r.get("url") not in seen_urls]

    all_urls = seen_urls | {r.get("url") for r in current_results if r.get("url")}
    state[niche] = {"seen_urls": list(all_urls), "last_checked": datetime.now(timezone.utc).isoformat()}
    save_state(state)
    return new_items


def draft_concepts_for_shift(niche, new_items):
    if not ANTHROPIC_API_KEY:
        print("[agent-14] ANTHROPIC_API_KEY not set — can't draft concepts, but here's what's new:")
        for item in new_items:
            print(f"  - {item.get('title')}: {item.get('url')}")
        return None

    sources_text = "\n".join(f"- {r.get('title')}: {r.get('content','')[:300]}" for r in new_items)
    prompt = f"""A new development just appeared in the competitive/trend landscape for: {niche}

What's new:
{sources_text}

Write exactly 2 ad creative concepts reacting specifically to this shift — not generic ideas,
ones that directly respond to what's new above. For each: headline, primary_text, cta.

Respond with ONLY a raw JSON array, no markdown. Each item:
{{"headline": "...", "primary_text": "...", "cta": "...", "based_on": "which new item this reacts to"}}"""

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
        json={"model": "claude-sonnet-4-6", "max_tokens": 800, "messages": [{"role": "user", "content": prompt}]},
        timeout=30,
    )
    resp.raise_for_status()
    raw = "".join(b.get("text", "") for b in resp.json().get("content", []) if b.get("type") == "text")
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)


def run_monitor(niche):
    print(f"--- Agent 14 run: {datetime.now(timezone.utc).isoformat()} — niche: {niche} ---")
    state = load_state()
    current_results = search_trends(niche)

    if not current_results:
        print("[agent-14] No search results available this run.")
        return

    new_items = detect_new_items(niche, current_results, state)

    if not new_items:
        print(f"[agent-14] Checked {len(current_results)} sources — nothing new since last run. No action.")
        return

    print(f"[agent-14] SHIFT DETECTED — {len(new_items)} new source(s) since last check:")
    for item in new_items:
        print(f"  - {item.get('title')}")

    concepts = draft_concepts_for_shift(niche, new_items)
    if concepts:
        with open(OUTPUT_FILE, "w") as f:
            json.dump(concepts, f, indent=2)
        print(f"\n[agent-14] Drafted {len(concepts)} concept(s) reacting to this shift — saved to {OUTPUT_FILE}")
        for c in concepts:
            print(f"  - {c['headline']} (reacting to: {c.get('based_on')})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--niche", required=True)
    args = parser.parse_args()
    run_monitor(args.niche)
