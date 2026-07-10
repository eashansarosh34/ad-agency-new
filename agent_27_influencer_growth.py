"""
AGENT 27 — Influencer / PR Organic Growth Engine
====================================================

The legitimate, real version of "grow a page's reach" — inspired by how
I-PAC actually worked: not fake numbers, but identifying REAL people who
genuinely move a specific audience, and building authentic content that
resonates. This is for personal brands, creators, public figures, actors.

What it does (all real, all organic-first):
  1. CONTENT RESONANCE — analyzes what content genuinely performs for
     this person's specific audience and niche, recommends what to make
     more of (based on real engagement data, not guesses)
  2. REAL COLLABORATOR DISCOVERY — finds genuine micro-influencers /
     accounts in the same niche who share an audience, for real collabs
     (the I-PAC "15,000 real local influencers" model, applied to a brand)
  3. POSTING OPTIMIZATION — best times/formats for THIS audience
  4. GROWTH DIAGNOSIS — is growth stalling because of content, consistency,
     or reach? Names the actual cause.

Explicitly NOT: buying followers, fake engagement, bots. Those destroy
real reach (the algorithm punishes high-followers/low-engagement) and
destroy trust. This grows the real thing or it doesn't pretend to.

Setup: TAVILY_API_KEY (collaborator discovery) + ANTHROPIC_API_KEY.
For engagement data, feed it real post-performance numbers.
"""

import os
import json
import argparse
import requests

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
TAVILY_API_URL = os.environ.get("TAVILY_API_URL", "https://api.tavily.com/search")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_API_URL = os.environ.get("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages")


def analyze_content_resonance(niche, recent_posts):
    """recent_posts: list of {caption/description, likes, comments, saves, reach}
    Finds the pattern in what actually works for this audience."""
    if not ANTHROPIC_API_KEY:
        # Simple fallback: rank by engagement rate
        ranked = sorted(recent_posts, key=lambda p: (p.get("likes",0)+p.get("comments",0)*3+p.get("saves",0)*5)
                        / max(p.get("reach",1),1), reverse=True)
        return {"top_performer": ranked[0] if ranked else None,
                "insight": "Ranked by weighted engagement (saves and comments count most). "
                           "Make more like the top performer.", "method": "fallback"}

    posts_text = "\n".join(
        f"- \"{p.get('description','')[:80]}\" | likes:{p.get('likes',0)} comments:{p.get('comments',0)} "
        f"saves:{p.get('saves',0)} reach:{p.get('reach',0)}" for p in recent_posts)
    prompt = f"""You are analyzing content performance for a personal brand / creator in the "{niche}" space.

Recent posts and their real engagement:
{posts_text}

Note: saves and comments signal much deeper resonance than likes. Reach shows distribution.

Identify:
1. What TYPE of content is genuinely resonating (the pattern, not just the single best post)
2. What's underperforming and why
3. One specific, concrete content idea to make next that builds on what's working

Respond with ONLY raw JSON, no markdown:
{{"whats_working": "...", "whats_not": "...", "make_next": "...", "why": "..."}}"""

    try:
        resp = requests.post(ANTHROPIC_API_URL,
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 400, "messages": [{"role": "user", "content": prompt}]},
            timeout=30)
        resp.raise_for_status()
        raw = "".join(b.get("text","") for b in resp.json().get("content",[]) if b.get("type")=="text")
        return json.loads(raw.replace("```json","").replace("```","").strip())
    except Exception as e:
        return {"error": str(e)}


def discover_real_collaborators(niche, city=""):
    """Find genuine accounts/creators in the same niche who share an audience —
    for REAL collaborations, not fake anything."""
    if not TAVILY_API_KEY:
        print("[agent-27] No Tavily key — skipping collaborator discovery.")
        return []
    query = f"micro influencers creators {niche} {city} instagram collaboration".strip()
    resp = requests.post(TAVILY_API_URL, json={
        "api_key": TAVILY_API_KEY, "query": query, "search_depth": "basic", "max_results": 6,
    }, timeout=20)
    resp.raise_for_status()
    return [{"title": r.get("title"), "url": r.get("url"), "snippet": r.get("content","")[:150]}
            for r in resp.json().get("results", [])]


def diagnose_growth(followers, avg_reach, avg_engagement_rate, posting_frequency_per_week):
    """Name the actual reason growth is or isn't happening."""
    signals = []
    # Reach relative to followers tells you if the algorithm is distributing
    reach_ratio = avg_reach / max(followers, 1)
    if reach_ratio < 0.15:
        signals.append(("REACH PROBLEM", "Your posts reach under 15% of your own followers — the algorithm "
                        "isn't distributing your content. Usually means low early engagement or inconsistent posting."))
    elif reach_ratio > 0.5:
        signals.append(("REACH HEALTHY", "Posts reach over half your followers — the algorithm likes your content. "
                        "Growth lever here is more collabs/shares to reach NEW audiences."))
    if avg_engagement_rate < 0.02:
        signals.append(("ENGAGEMENT PROBLEM", "Under 2% engagement — content isn't compelling enough to react to. "
                        "This is a content quality/relevance issue, not a reach issue."))
    if posting_frequency_per_week < 3:
        signals.append(("CONSISTENCY PROBLEM", f"Only {posting_frequency_per_week} posts/week — the algorithm rewards "
                        "consistency. Inconsistent posting caps reach regardless of quality."))
    if not signals:
        signals.append(("HEALTHY", "Metrics look healthy. To grow faster: more collaborations with real accounts "
                        "in your niche to tap new audiences, and double down on your best-performing format."))
    return signals


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--niche", default="fashion creator")
    parser.add_argument("--city", default="")
    parser.add_argument("--diagnose", action="store_true")
    args = parser.parse_args()

    if args.diagnose:
        print("=== GROWTH DIAGNOSIS (example: 10K follower creator) ===")
        for label, detail in diagnose_growth(followers=10000, avg_reach=1200,
                                              avg_engagement_rate=0.018, posting_frequency_per_week=2):
            print(f"\n  [{label}]\n  {detail}")

    print("\n=== CONTENT RESONANCE (example data) ===")
    example_posts = [
        {"description": "behind the scenes of my morning routine", "likes": 800, "comments": 120, "saves": 340, "reach": 4200},
        {"description": "product photo with price", "likes": 210, "comments": 8, "saves": 12, "reach": 3800},
        {"description": "honest story about a hard week", "likes": 1500, "comments": 280, "saves": 190, "reach": 6100},
    ]
    result = analyze_content_resonance(args.niche, example_posts)
    print(json.dumps(result, indent=2))
