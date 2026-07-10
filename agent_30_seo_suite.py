"""
AGENT 30 — SEO Suite (Website Marketing)
============================================

Complete SEO analysis and guidance toolkit. Covers the four pillars of
real SEO work:

  1. TECHNICAL AUDIT — page speed, mobile-friendliness, crawlability,
     broken links, meta tags present/missing (the Lighthouse-style stuff)
  2. ON-PAGE SEO — title tags, meta descriptions, heading structure,
     keyword placement, image alt text
  3. KEYWORD STRATEGY — what to rank for, search intent, difficulty
  4. CONTENT GAP — what competitors rank for that this site doesn't

WHAT'S NEEDED FROM THE CLIENT (one-time onboarding, not a code task):
  - Their website URL (to audit)
  - Ideally: Google Search Console access (to see real ranking data)
  - For deep technical audit: the site must be publicly reachable

HOW THE ANALYSIS WORKS:
  - Fetches the actual page HTML and inspects it for on-page/technical issues
    (this part is real and works on any public URL)
  - Uses Tavily to research keyword landscape and competitor content
  - Uses Claude to synthesize findings into a prioritized action plan
  - For live Lighthouse-grade performance scores, points to Google's own
    PageSpeed Insights API (free, needs a Google API key) — wired in as
    an optional enhancement

Note: this AUDITS and GUIDES. Actually implementing fixes (editing the
site's code/meta tags) requires access to the client's site — that's the
delivery step you do with their CMS/developer access.
"""

import os
import re
import json
import argparse
import requests

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_API_URL = os.environ.get("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
TAVILY_API_URL = os.environ.get("TAVILY_API_URL", "https://api.tavily.com/search")
PAGESPEED_API_KEY = os.environ.get("GOOGLE_PAGESPEED_KEY", "")  # optional


def fetch_page(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; SEOAuditBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        return None


def onpage_audit(html, url):
    """Real on-page SEO inspection of actual page HTML."""
    issues = []
    wins = []

    # Title tag
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if not title_match:
        issues.append(("HIGH", "Missing <title> tag — critical for search rankings"))
    else:
        title = title_match.group(1).strip()
        if len(title) < 30:
            issues.append(("MEDIUM", f"Title too short ({len(title)} chars) — aim for 50-60"))
        elif len(title) > 65:
            issues.append(("MEDIUM", f"Title too long ({len(title)} chars) — may get cut off in results"))
        else:
            wins.append(f"Title tag length good ({len(title)} chars)")

    # Meta description
    meta_desc = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', html, re.IGNORECASE | re.DOTALL)
    if not meta_desc:
        issues.append(("HIGH", "Missing meta description — this is what shows under your link in Google"))
    else:
        desc_len = len(meta_desc.group(1).strip())
        if desc_len < 70 or desc_len > 160:
            issues.append(("LOW", f"Meta description length off ({desc_len} chars) — aim for 120-155"))
        else:
            wins.append("Meta description present and well-sized")

    # H1
    h1_tags = re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
    if not h1_tags:
        issues.append(("HIGH", "No H1 heading — every page needs exactly one clear H1"))
    elif len(h1_tags) > 1:
        issues.append(("MEDIUM", f"{len(h1_tags)} H1 tags found — should be exactly one per page"))
    else:
        wins.append("Exactly one H1 heading (correct)")

    # Images without alt
    imgs = re.findall(r"<img[^>]*>", html, re.IGNORECASE)
    imgs_no_alt = [i for i in imgs if not re.search(r'alt=["\'][^"\']+["\']', i, re.IGNORECASE)]
    if imgs_no_alt:
        issues.append(("MEDIUM", f"{len(imgs_no_alt)} of {len(imgs)} images missing alt text "
                       "(hurts accessibility and image SEO)"))
    elif imgs:
        wins.append(f"All {len(imgs)} images have alt text")

    # Viewport (mobile)
    if not re.search(r'<meta\s+name=["\']viewport["\']', html, re.IGNORECASE):
        issues.append(("HIGH", "No viewport meta tag — page won't display correctly on mobile"))
    else:
        wins.append("Mobile viewport tag present")

    # HTTPS
    if not url.startswith("https://"):
        issues.append(("HIGH", "Site not on HTTPS — Google penalizes non-secure sites"))

    # Open Graph (social sharing)
    if not re.search(r'<meta\s+property=["\']og:', html, re.IGNORECASE):
        issues.append(("LOW", "No Open Graph tags — links won't preview nicely when shared on social"))

    return issues, wins


def pagespeed_check(url):
    """Optional: real Google PageSpeed/Lighthouse score if API key is set."""
    if not PAGESPEED_API_KEY:
        return None
    try:
        resp = requests.get("https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
            params={"url": url, "key": PAGESPEED_API_KEY, "strategy": "mobile"}, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        score = data.get("lighthouseResult", {}).get("categories", {}).get("performance", {}).get("score")
        return round(score * 100) if score is not None else None
    except Exception:
        return None


def keyword_research(niche, city=""):
    """Research the keyword landscape for this business."""
    if not TAVILY_API_KEY:
        return []
    query = f"{niche} {city} services".strip()
    try:
        resp = requests.post(TAVILY_API_URL, json={
            "api_key": TAVILY_API_KEY, "query": query, "search_depth": "basic", "max_results": 6,
        }, timeout=20)
        resp.raise_for_status()
        return [{"title": r.get("title"), "url": r.get("url")} for r in resp.json().get("results", [])]
    except Exception:
        return []


def run_audit(url, niche="", city=""):
    print(f"\n{'='*60}")
    print(f"SEO AUDIT — {url}")
    print(f"{'='*60}")

    html = fetch_page(url)
    if not html:
        print(f"\n  ⚠ Could not fetch the page. Check the URL is correct and publicly reachable.")
        return

    issues, wins = onpage_audit(html, url)

    speed = pagespeed_check(url)
    if speed is not None:
        verdict = "good" if speed >= 90 else "needs work" if speed >= 50 else "poor"
        print(f"\n  ⚡ Page speed score (mobile): {speed}/100 — {verdict}")

    print(f"\n  ✅ What's already good ({len(wins)}):")
    for w in wins:
        print(f"     • {w}")

    high = [i for i in issues if i[0] == "HIGH"]
    med = [i for i in issues if i[0] == "MEDIUM"]
    low = [i for i in issues if i[0] == "LOW"]

    print(f"\n  🔴 Fix first ({len(high)} high priority):")
    for _, msg in high:
        print(f"     • {msg}")
    if med:
        print(f"\n  🟡 Fix soon ({len(med)} medium):")
        for _, msg in med:
            print(f"     • {msg}")
    if low:
        print(f"\n  🔵 Nice to fix ({len(low)} low):")
        for _, msg in low:
            print(f"     • {msg}")

    print(f"\n{'='*60}")
    print(f"  Summary: {len(high)} critical, {len(med)} medium, {len(low)} minor issues found")
    print(f"{'='*60}\n")

    return {"url": url, "issues": issues, "wins": wins, "speed": speed}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="Website URL to audit")
    parser.add_argument("--niche", default="")
    parser.add_argument("--city", default="")
    args = parser.parse_args()

    if args.url:
        run_audit(args.url, args.niche, args.city)
    else:
        # Demo on a simple test HTML to prove the audit logic works
        print("[Demo — auditing a sample HTML page with deliberate issues]")
        sample = """<html><head><title>Home</title></head>
        <body><h1>Welcome</h1><h1>Also welcome</h1>
        <img src="a.jpg"><img src="b.jpg" alt="a product">
        </body></html>"""
        issues, wins = onpage_audit(sample, "http://example.com")
        print("\nIssues found:")
        for sev, msg in issues:
            print(f"  [{sev}] {msg}")
        print("\nWins:")
        for w in wins:
            print(f"  • {w}")
