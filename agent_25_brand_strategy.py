"""
AGENT 25 — Brand Strategy Classifier
========================================

The question this answers: "How do I know what approach fits THIS brand?"
Instead of running the same playbook on every client, this reads a brand's
situation and classifies it into a strategy archetype — then recommends
the channel mix, content approach, and primary metric that actually fits
that type. This is the "which approach for which brand" decision,
systematized.

Brand archetypes it distinguishes (each needs a genuinely different playbook):
  - impulse_dtc:      cheap, visual, emotional buy (lamps, tees, snacks)
                      -> Meta/IG heavy, Reels, retargeting, ROAS focus
  - considered_purchase: expensive/researched (jewellery, real estate, B2B)
                      -> Google intent + Meta trust-building, longer funnel
  - local_service:    clinics, gyms, salons, restaurants
                      -> Local targeting, WhatsApp leads, Google Maps, CPL focus
  - personal_brand:   influencer, creator, public figure, actor
                      -> Organic-led, profile-visit optimization, collabs
  - app_marketplace:  two-sided apps, platforms
                      -> Split campaigns per side, install+activation focus

For each, it returns: recommended channels, primary metric to optimize,
content angle, and the single biggest mistake to avoid for that type.
"""

import os
import json
import argparse
import requests

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_API_URL = os.environ.get("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages")

# The playbooks — hard-coded expert knowledge, so this works even without
# the API (the API just handles the classification + nuance).
PLAYBOOKS = {
    "impulse_dtc": {
        "channels": "Meta/Instagram primary (Reels + Feed), retargeting essential",
        "primary_metric": "ROAS (return on ad spend) — track actual sales, not leads",
        "content_angle": "Visual, emotional, fast hook. The product in action IS the ad. UGC and unboxing win.",
        "biggest_mistake": "Sending traffic to a slow/confusing checkout. Impulse dies in 3 seconds of friction.",
        "funnel_length": "Short — see, want, buy in one session. Retarget the ones who didn't.",
    },
    "considered_purchase": {
        "channels": "Google Search (capture intent) + Meta (build trust/desire over time)",
        "primary_metric": "Cost per qualified lead, then close rate — not immediate sales",
        "content_angle": "Trust and proof. Reviews, before/after, craftsmanship, guarantees. Educate before selling.",
        "biggest_mistake": "Expecting a same-day sale. These buyers research for days/weeks. Nurture, don't rush.",
        "funnel_length": "Long — multiple touchpoints. Retargeting and email/WhatsApp nurture matter most.",
    },
    "local_service": {
        "channels": "Meta lead ads (WhatsApp form) + Google Maps/Local SEO + Google Search",
        "primary_metric": "Cost per lead, then show-up rate",
        "content_angle": "Trust + convenience + locality. Team, process, real patients/customers, proximity.",
        "biggest_mistake": "Targeting too wide. A clinic 40km away is useless. Tight radius, local trust signals.",
        "funnel_length": "Medium — enquiry to booking. Speed of response is everything (reply in minutes).",
    },
    "personal_brand": {
        "channels": "Organic-led (real content) + paid profile-visit amplification + real creator collabs",
        "primary_metric": "Cost per profile visit + genuine follower growth + engagement rate",
        "content_angle": "Authenticity and personality. Behind-the-scenes, POV, real voice. Never corporate.",
        "biggest_mistake": "Buying fake followers/engagement — kills real reach and destroys trust. Grow real or don't.",
        "funnel_length": "Ongoing — this is relationship-building, not a campaign with an end date.",
    },
    "app_marketplace": {
        "channels": "Meta App Promotion (split by user type) + Google UAC, geo-concentrated",
        "primary_metric": "Cost per install THEN cost per activation — an install that never acts is worthless",
        "content_angle": "Different message per side of the marketplace. Solve each side's specific pain separately.",
        "biggest_mistake": "One generic 'download our app' campaign for a two-sided marketplace. Split it always.",
        "funnel_length": "Install -> activation -> retention. Optimize toward the action, not the download.",
    },
}


def classify_brand(brand_description, extra_context=""):
    if not ANTHROPIC_API_KEY:
        return {"archetype": "unknown", "reasoning": "No API key — cannot classify. "
                "Review the 5 archetypes in PLAYBOOKS manually.", "confidence": "none"}

    archetypes_list = "\n".join(f"- {k}: {v['content_angle'][:80]}" for k, v in PLAYBOOKS.items())
    prompt = f"""Classify this brand into exactly ONE strategy archetype.

Brand: {brand_description}
{f"Extra context: {extra_context}" if extra_context else ""}

The 5 archetypes:
- impulse_dtc: cheap, visual, emotional-buy D2C products (lamps, tees, snacks, accessories)
- considered_purchase: expensive or researched purchases (jewellery, real estate, B2B services, high-value)
- local_service: local businesses serving a geographic area (clinics, gyms, salons, restaurants)
- personal_brand: an individual — influencer, creator, public figure, actor, coach
- app_marketplace: apps and platforms, especially two-sided marketplaces

Respond with ONLY raw JSON, no markdown:
{{"archetype": "one of the 5 exact keys above", "confidence": "high/medium/low",
  "reasoning": "one sentence why", "watch_out": "any nuance that makes this brand slightly unusual for its type"}}"""

    try:
        resp = requests.post(
            ANTHROPIC_API_URL,
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                     "Content-Type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 300,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        resp.raise_for_status()
        raw = "".join(b.get("text", "") for b in resp.json().get("content", []) if b.get("type") == "text")
        return json.loads(raw.replace("```json", "").replace("```", "").strip())
    except Exception as e:
        return {"archetype": "unknown", "reasoning": f"Classification failed: {e}", "confidence": "none"}


def build_strategy(brand_description, extra_context=""):
    classification = classify_brand(brand_description, extra_context)
    archetype = classification.get("archetype", "unknown")
    playbook = PLAYBOOKS.get(archetype)

    print(f"\n{'='*60}")
    print(f"BRAND STRATEGY — {brand_description[:50]}")
    print(f"{'='*60}")
    print(f"Type: {archetype}  (confidence: {classification.get('confidence','?')})")
    print(f"Why: {classification.get('reasoning','')}")
    if classification.get("watch_out"):
        print(f"Watch out: {classification['watch_out']}")

    if playbook:
        print(f"\n  Channels:        {playbook['channels']}")
        print(f"  Primary metric:  {playbook['primary_metric']}")
        print(f"  Content angle:   {playbook['content_angle']}")
        print(f"  Funnel length:   {playbook['funnel_length']}")
        print(f"  ⚠ Avoid:         {playbook['biggest_mistake']}")
    print(f"{'='*60}\n")

    return {"classification": classification, "playbook": playbook}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--brand", help="Description of the brand/business")
    parser.add_argument("--context", default="")
    args = parser.parse_args()

    if args.brand:
        build_strategy(args.brand, args.context)
    else:
        # Demo across brand types
        for desc in [
            "3D printed cute animal lamps, ₹799-899, sold via Instagram DMs",
            "Designer jewellery brand, pieces ₹15,000-80,000, gifting focus",
            "Dental clinic in Hyderabad wanting more patient appointments",
            "Actor with 10K Instagram followers wanting to grow their following",
            "Hyperlocal task-matching app connecting people who need help with earners",
        ]:
            build_strategy(desc)
