"""
AGENT 05 — Trend Scout
=========================

What this does:
  Searches for what's currently trending in ad creative/lead-gen for a
  given niche, then hands back a short list of concrete, named angles —
  with a one-line "why it works" and a "next step" for each.

This agent deliberately does NOT decide anything or build anything. It
surfaces options. You (the strategist) pick which ones are worth building,
then hand the chosen angle to Agent 01 to actually write the creative.
That split is intentional — trend-spotting can be automated, taste and
brand fit can't.

Setup:
  1. Tavily Search API key — free tier, ~1000 searches/month.
     Sign up at tavily.com -> Dashboard -> API Keys.
  2. Anthropic API key — to turn raw search results into a clean,
     usable shortlist instead of a wall of article snippets.
  3. pip install requests --break-system-packages

Run:
  python3 agent_05_trend_scout.py --niche "dental clinic ads India"
  python3 agent_05_trend_scout.py --niche "gym membership ads India"

Without any keys set, this still runs — it just tells you plainly that
it's not grounded in live search, rather than silently guessing.
"""

import os
import json
import argparse
import requests

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
TAVILY_API_URL = os.environ.get("TAVILY_API_URL", "https://api.tavily.com/search")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


def search_trends(niche, max_results=8):
    if not TAVILY_API_KEY:
        print("[warn] TAVILY_API_KEY not set — skipping live search.")
        return []
    try:
        resp = requests.post(
            TAVILY_API_URL,
            json={
                "api_key": TAVILY_API_KEY,
                "query": f"{niche} trending ad creative angles 2026",
                "search_depth": "basic",
                "max_results": max_results,
                "days": 60,  # keep results recent, not stale evergreen articles
            },
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception as e:
        print(f"[warn] Live search failed ({e}); continuing without it.")
        return []


def synthesize(niche, raw_results):
    if raw_results:
        sources_text = "\n\n".join(
            f"- {r.get('title','')}: {r.get('content','')[:400]}" for r in raw_results
        )
        grounding_note = ""
    else:
        sources_text = "(no live search results available)"
        grounding_note = (" IMPORTANT: no live search data was available, so base this on general "
                           "knowledge only and say so plainly — do not present this as current data.")

    prompt = f"""You are a trend scout for a one-person ad agency running local lead-generation
campaigns in India. Niche: {niche}.

Sources found:
{sources_text}

Produce exactly 5 concrete, actionable trending ad angles or formats relevant to this niche
right now. For each, give: a short name, one sentence on what it is, one sentence on why it's
working, and one concrete next step a strategist could hand to a creative agent to build it.
{grounding_note}

Respond with ONLY a raw JSON array, no markdown fences, no preamble. Each item exactly:
{{"name": "...", "what_it_is": "...", "why_it_works": "...", "next_step": "..."}}"""

    if not ANTHROPIC_API_KEY:
        print("[warn] ANTHROPIC_API_KEY not set — returning raw sources instead of a synthesized shortlist.")
        return [{"name": r.get("title", "untitled"), "what_it_is": r.get("content", "")[:200],
                 "why_it_works": "(not synthesized — no API key set)", "next_step": r.get("url", "")}
                for r in raw_results] or [{"name": "No data available", "what_it_is": "",
                                            "why_it_works": "Set both TAVILY_API_KEY and ANTHROPIC_API_KEY to get real suggestions.",
                                            "next_step": ""}]

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                     "Content-Type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 1000,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        resp.raise_for_status()
        text = "".join(b.get("text", "") for b in resp.json().get("content", []) if b.get("type") == "text")
        cleaned = text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except Exception as e:
        print(f"[warn] Synthesis failed ({e}); returning raw sources instead.")
        return [{"name": r.get("title", "untitled"), "what_it_is": r.get("content", "")[:200],
                 "why_it_works": "(synthesis failed)", "next_step": r.get("url", "")} for r in raw_results]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--niche", required=True, help='e.g. "dental clinic ads India"')
    args = parser.parse_args()

    print(f"Scouting trends for: {args.niche}\n")
    raw = search_trends(args.niche)
    suggestions = synthesize(args.niche, raw)

    print(json.dumps(suggestions, indent=2))
    print("\n--- These are suggestions only. Nothing gets built automatically. "
          "Pick what fits the brand, then hand it to Agent 01. ---")


if __name__ == "__main__":
    main()
