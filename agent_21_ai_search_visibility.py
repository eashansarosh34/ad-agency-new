"""
AGENT 21 — AI Search Visibility Monitor
============================================

What this does:
  Checks how a client's business actually gets described when someone
  asks an AI assistant a question they'd realistically ask — "best
  dental clinic in Hyderabad", "jewellery brands in Mumbai for gifting" —
  the way people increasingly search now, inside ChatGPT/Gemini/Perplexity/
  Claude instead of typing into Google.

  This is structurally different from anything Meta or Google's own
  automation can sell you, because it isn't about buying placement on
  their platforms — it's about whether independent AI systems mention
  your client's business at all, and how, when asked naturally.

  Since most of these assistants don't expose a public ads/visibility API
  yet, this uses live web search as the proxy signal: what's actually
  being said about the brand right now, in the kind of pages these AI
  systems draw their answers from. It also tracks competitor mentions in
  the same space, so a client sees not just "are we visible" but
  "are we visible relative to who we're actually competing with."

Run:
  python3 agent_21_ai_search_visibility.py --brand "SunCap" --query "stock credit analysis services Hyderabad"
"""

import os
import json
import argparse
import requests
from datetime import datetime, timezone

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
TAVILY_API_URL = os.environ.get("TAVILY_API_URL", "https://api.tavily.com/search")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
LOG_FILE = "ai_visibility_log.json"


def search_for_query(query, max_results=8):
    if not TAVILY_API_KEY:
        print("[agent-21] TAVILY_API_KEY not set — cannot check live visibility.")
        return []
    resp = requests.post(TAVILY_API_URL, json={
        "api_key": TAVILY_API_KEY, "query": query,
        "search_depth": "advanced", "max_results": max_results,
    }, timeout=25)
    resp.raise_for_status()
    return resp.json().get("results", [])


def analyze_visibility(brand_name, query, results):
    """Checks whether the brand actually appears in the kind of content
    AI assistants draw answers from, and who else shows up instead."""
    mentioned_in = [r for r in results if brand_name.lower() in (r.get("content", "") + r.get("title", "")).lower()]
    not_mentioned = [r for r in results if r not in mentioned_in]

    analysis = {
        "brand": brand_name, "query": query,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "total_sources_found": len(results),
        "brand_mentioned_in": len(mentioned_in),
        "visibility_rate": round(len(mentioned_in) / len(results), 2) if results else 0,
        "sources_mentioning_brand": [{"title": r.get("title"), "url": r.get("url")} for r in mentioned_in],
        "top_sources_NOT_mentioning_brand": [{"title": r.get("title"), "url": r.get("url")} for r in not_mentioned[:5]],
    }
    return analysis


def identify_competitors_mentioned(results, brand_name):
    """Uses Claude to spot which OTHER businesses keep showing up for this
    query — i.e. who's actually winning the AI-visibility race right now."""
    if not ANTHROPIC_API_KEY or not results:
        return None

    sources_text = "\n".join(f"- {r.get('title','')}: {r.get('content','')[:200]}" for r in results)
    prompt = f"""These are search results for a query relevant to the brand "{brand_name}":
{sources_text}

List the OTHER specific business/brand names (not "{brand_name}") that appear repeatedly
or prominently in these results — these are who an AI assistant would likely mention
INSTEAD of or ALONGSIDE "{brand_name}" if asked this question.

Respond with ONLY a raw JSON array of strings, no markdown. If none found, return []."""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 300, "messages": [{"role": "user", "content": prompt}]},
            timeout=20,
        )
        resp.raise_for_status()
        raw = "".join(b.get("text", "") for b in resp.json().get("content", []) if b.get("type") == "text")
        return json.loads(raw.replace("```json", "").replace("```", "").strip())
    except Exception as e:
        print(f"[agent-21] Competitor identification unavailable: {e}")
        return None


def recommend_action(analysis, competitors):
    if not ANTHROPIC_API_KEY:
        if analysis["visibility_rate"] < 0.2:
            return ("LOW visibility — your brand barely shows up in the content AI assistants would draw "
                    "from for this question. Worth getting listed/reviewed on the sources that DO show up.")
        return "Visibility looks reasonable for this query. Keep monitoring."

    prompt = f"""A client's AI-search visibility was just checked.
Visibility rate: {analysis['visibility_rate']:.0%} (brand appeared in {analysis['brand_mentioned_in']} of {analysis['total_sources_found']} sources)
Competitors showing up instead: {competitors}
Top sources NOT mentioning the brand: {[s['title'] for s in analysis['top_sources_NOT_mentioning_brand'][:3]]}

Write ONE specific, plain-language recommendation (3 sentences max) for what this client
should do this month to improve how often AI assistants mention them for this kind of query.
Be concrete — name an actual type of action (get listed somewhere specific, get a review on
a specific kind of site, publish specific content), not generic advice."""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 200, "messages": [{"role": "user", "content": prompt}]},
            timeout=20,
        )
        resp.raise_for_status()
        return "".join(b.get("text", "") for b in resp.json().get("content", []) if b.get("type") == "text")
    except Exception as e:
        return f"(recommendation unavailable: {e})"


def run_check(brand_name, query):
    print(f"--- Agent 21 run: {datetime.now(timezone.utc).isoformat()} ---")
    print(f"Checking AI-search visibility for '{brand_name}' on: \"{query}\"")

    results = search_for_query(f"{query} {brand_name}" if brand_name.lower() not in query.lower() else query)
    if not results:
        print("No results to analyze.")
        return None

    analysis = analyze_visibility(brand_name, query, results)
    competitors = identify_competitors_mentioned(results, brand_name)
    recommendation = recommend_action(analysis, competitors)

    print(f"\nVisibility: {analysis['brand_mentioned_in']}/{analysis['total_sources_found']} sources "
          f"({analysis['visibility_rate']:.0%}) mention '{brand_name}'")
    if competitors:
        print(f"Competitors showing up instead: {', '.join(competitors[:5])}")
    print(f"\nRecommendation:\n  {recommendation}")

    result = {**analysis, "competitors_mentioned": competitors, "recommendation": recommendation}
    existing = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []
    existing.append(result)
    with open(LOG_FILE, "w") as f:
        json.dump(existing, f, indent=2)

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--brand", required=True)
    parser.add_argument("--query", required=True, help='The natural question a customer might ask an AI assistant')
    args = parser.parse_args()
    run_check(args.brand, args.query)
