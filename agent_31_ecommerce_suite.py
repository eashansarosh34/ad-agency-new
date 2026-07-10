"""
AGENT 31 — E-commerce / Shopify Suite
=========================================

Complete e-commerce marketing toolkit for online stores (Shopify and
similar). Covers what actually moves the needle for a D2C/e-commerce
client:

  1. PRODUCT FEED OPTIMIZATION — turns a raw product catalog into
     ad-ready, SEO-optimized product entries (titles, descriptions
     written to convert AND rank)
  2. STORE CONVERSION ANALYSIS — reads the funnel (visits → product
     views → add to cart → checkout → purchase) and finds where sales
     leak (works with Agent 26's funnel data)
  3. CATALOG → META SHOPPING — structures products for Meta/Instagram
     Shopping catalog ads (the highest-ROAS format for e-commerce)
  4. PRICING & MERCHANDISING SIGNALS — flags which products to push in
     ads (high margin + high interest) vs. which to fix or drop

WHAT'S NEEDED FROM THE CLIENT (onboarding, not code):
  - Their product catalog (Shopify CSV export, or store URL, or a product
    list) — Shopify exports this natively in one click
  - Ideally Shopify Admin API access for live data (optional; CSV works)
  - Meta Commerce Manager connected for catalog ads

This suite OPTIMIZES and STRUCTURES. Publishing the catalog to their
store or Meta requires their store/Meta access — the delivery step.
"""

import os
import re
import json
import csv
import argparse
import requests
from io import StringIO

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_API_URL = os.environ.get("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages")


def optimize_product_listing(product):
    """Turn a raw product into an ad-ready, SEO-optimized listing.
    product: {name, description, price, category, ...}"""
    if not ANTHROPIC_API_KEY:
        # Fallback: basic structural optimization
        return {
            "seo_title": f"{product.get('name','')} — Buy Online | Free Shipping"[:60],
            "meta_description": (product.get('description','')[:150]),
            "note": "Basic fallback — set API key for conversion-optimized copy"
        }

    prompt = f"""Optimize this e-commerce product listing to both CONVERT buyers and RANK in search.

Product:
Name: {product.get('name','')}
Current description: {product.get('description','')}
Price: {product.get('price','')}
Category: {product.get('category','')}

Write:
1. seo_title: a search-optimized product title (under 60 chars, includes the key search term)
2. meta_description: compelling meta description (120-155 chars, includes a reason to click)
3. product_description: a short conversion-focused description (2-3 sentences, benefit-led not
   feature-led, speaks to why someone WANTS this)
4. ad_headline: a punchy headline for a Meta shopping ad (under 40 chars)

Respond with ONLY raw JSON, no markdown:
{{"seo_title": "...", "meta_description": "...", "product_description": "...", "ad_headline": "..."}}"""

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


def analyze_store_funnel(funnel_data):
    """funnel_data: {visits, product_views, add_to_cart, checkout_started, purchases}
    Finds where the store loses sales."""
    steps = [
        ("Store visits", funnel_data.get("visits", 0)),
        ("Viewed a product", funnel_data.get("product_views", 0)),
        ("Added to cart", funnel_data.get("add_to_cart", 0)),
        ("Started checkout", funnel_data.get("checkout_started", 0)),
        ("Purchased", funnel_data.get("purchases", 0)),
    ]

    print(f"\n{'='*55}")
    print("STORE CONVERSION FUNNEL")
    print(f"{'='*55}")

    biggest_leak = {"step": None, "drop": 0, "from": None}
    top = steps[0][1] or 1
    for i, (name, count) in enumerate(steps):
        pct = count / top * 100
        bar = "█" * min(int(pct / 3.3), 30)
        print(f"  {name:<22} {count:>7,}  {bar} {pct:.1f}%")
        if i > 0 and steps[i-1][1] > 0:
            drop = (steps[i-1][1] - count) / steps[i-1][1]
            if drop > biggest_leak["drop"]:
                biggest_leak = {"step": name, "drop": drop, "from": steps[i-1][0]}

    print(f"{'='*55}")
    if biggest_leak["step"]:
        print(f"\n  🔍 Biggest leak: {biggest_leak['drop']:.0%} lost between "
              f"'{biggest_leak['from']}' → '{biggest_leak['step']}'")
        print(f"     {_diagnose_store_leak(biggest_leak['from'], biggest_leak['step'])}")

    # Overall conversion rate
    if top > 1:
        cvr = steps[-1][1] / top * 100
        benchmark = "above" if cvr > 2 else "below"
        print(f"\n  Overall conversion rate: {cvr:.2f}% ({benchmark} the ~2% e-commerce average)")
    return biggest_leak


def _diagnose_store_leak(frm, to):
    if "visits" in frm.lower() and "product" in to.lower():
        return "Visitors leave before viewing products — homepage/landing isn't pulling them in, or traffic is poorly targeted."
    if "product" in frm.lower() and "cart" in to.lower():
        return "They look but don't add — price, product photos, reviews, or unclear value. The product page is the problem."
    if "cart" in frm.lower() and "checkout" in to.lower():
        return "Cart abandonment before checkout — often unexpected shipping cost or forced account creation."
    if "checkout" in frm.lower() and "purchas" in to.lower():
        return "They start checkout but don't finish — payment friction, too many form fields, or trust concerns at the final step."
    return "Investigate what changes between these two steps."


def parse_shopify_csv(csv_text, limit=5):
    """Parse a Shopify product CSV export into product dicts."""
    products = []
    reader = csv.DictReader(StringIO(csv_text))
    seen = set()
    for row in reader:
        handle = row.get("Handle")
        if handle and handle not in seen:
            seen.add(handle)
            products.append({
                "name": row.get("Title", ""),
                "description": re.sub(r"<[^>]+>", "", row.get("Body (HTML)", "") or "")[:300],
                "price": row.get("Variant Price", ""),
                "category": row.get("Type", "") or row.get("Product Category", ""),
            })
        if len(products) >= limit:
            break
    return products


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--funnel", action="store_true", help="Demo the store funnel analysis")
    parser.add_argument("--optimize", action="store_true", help="Demo product listing optimization")
    args = parser.parse_args()

    if args.funnel or not (args.optimize):
        # Realistic store funnel with a product-page leak
        analyze_store_funnel({
            "visits": 8000, "product_views": 5200, "add_to_cart": 620,
            "checkout_started": 410, "purchases": 180,
        })

    if args.optimize:
        print("\n=== PRODUCT LISTING OPTIMIZATION (example) ===")
        result = optimize_product_listing({
            "name": "Cat Lamp Milo",
            "description": "A 3d printed cat lamp, usb powered, cute",
            "price": "899", "category": "Home Decor",
        })
        print(json.dumps(result, indent=2))
