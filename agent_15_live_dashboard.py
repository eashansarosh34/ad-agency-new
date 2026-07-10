"""
AGENT 15 — Live Client Dashboard Server
==========================================

What this does:
  Serves a live, auto-refreshing dashboard at http://localhost:8080 (or
  wherever you host it) that a client can bookmark. Every time they open
  it, they see real numbers pulled fresh from Meta's API — not a
  screenshot, not a PDF, not a monthly report. Real spend, real leads,
  real cost-per-result, updated on page load.

  This is the trust layer. A client who can see everything, any time,
  on their own, without asking you first, is a client you keep.

What to host this on:
  Locally for demos: just run this script.
  For a real permanent URL: deploy to any free tier (Railway, Render,
  Fly.io) — all have free Python hosting. One deploy, stays live.

Setup: same Meta credentials as Agent 02.
Run: python3 agent_15_live_dashboard.py
Then open http://localhost:8080 in your browser.
"""

import os
import json
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timedelta, timezone

META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")
META_AD_ACCOUNT_ID = os.environ.get("META_AD_ACCOUNT_ID", "act_XXXXXXXXXXXX")
CLIENT_NAME = os.environ.get("CLIENT_NAME", "Your Brand")
GRAPH_URL = os.environ.get("META_API_URL", "https://graph.facebook.com/v21.0")
PORT = int(os.environ.get("DASHBOARD_PORT", 8080))


def fetch_summary():
    if not META_ACCESS_TOKEN:
        return None, "META_ACCESS_TOKEN not set — run this with a real token to see live data."
    since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    until = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = f"{GRAPH_URL}/{META_AD_ACCOUNT_ID}/insights"
    try:
        resp = requests.get(url, params={
            "access_token": META_ACCESS_TOKEN, "fields": "spend,impressions,clicks,actions",
            "time_range": json.dumps({"since": since, "until": until}),
        }, timeout=15)
        resp.raise_for_status()
        rows = resp.json().get("data", [])
        if not rows:
            return {"spend": 0, "impressions": 0, "clicks": 0, "leads": 0, "cpl": 0}, None
        row = rows[0]
        spend = float(row.get("spend", 0))
        impressions = int(row.get("impressions", 0))
        clicks = int(row.get("clicks", 0))
        leads = sum(int(a.get("value", 0)) for a in row.get("actions", [])
                    if a.get("action_type") in ("lead", "onsite_conversion.lead_grouped"))
        cpl = round(spend / leads, 2) if leads else 0
        return {"spend": spend, "impressions": impressions, "clicks": clicks,
                "leads": leads, "cpl": cpl}, None
    except Exception as e:
        return None, str(e)


def render_dashboard(data, error):
    updated = datetime.now(timezone.utc).strftime("%d %b %Y, %I:%M %p UTC")
    if error:
        status_section = f'<div class="error">⚠ Could not load live data: {error}</div>'
        cards = ""
    else:
        def card(label, value, sub=""):
            return f'''<div class="card">
              <div class="label">{label}</div>
              <div class="value">{value}</div>
              {"<div class='sub'>" + sub + "</div>" if sub else ""}
            </div>'''
        cards = f'''<div class="grid">
          {card("Total Spend", f"₹{data['spend']:,.0f}", "last 30 days")}
          {card("Leads Generated", f"{data['leads']:,}", "real people who showed interest")}
          {card("Cost Per Lead", f"₹{data['cpl']:,.0f}", "what each lead cost us")}
          {card("Impressions", f"{data['impressions']:,}", "times your ad was seen")}
          {card("Link Clicks", f"{data['clicks']:,}", "people who clicked through")}
          {card("Click Rate", f"{round(data['clicks']/max(data['impressions'],1)*100,2)}%", "of people who saw it, clicked")}
        </div>'''
        status_section = ""

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="300">
<title>{CLIENT_NAME} — Live Performance</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{font-family:'Inter',sans-serif;background:#0f1117;color:#e8e8e8;min-height:100vh;padding:40px 20px;}}
  .wrap{{max-width:840px;margin:0 auto;}}
  .top{{display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:12px;border-bottom:1px solid rgba(255,255,255,0.08);padding-bottom:20px;margin-bottom:32px;}}
  .brand{{font-size:22px;font-weight:700;}}
  .live{{display:flex;align-items:center;gap:8px;font-size:13px;color:#888;}}
  .dot{{width:8px;height:8px;background:#4ade80;border-radius:50%;animation:pulse 2s infinite;}}
  @keyframes pulse{{0%,100%{{opacity:1;}}50%{{opacity:.4;}}}}
  .tagline{{font-size:13px;color:#4ade80;margin-bottom:28px;}}
  .grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;}}
  .card{{background:#1a1d27;border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:22px 18px;}}
  .label{{font-size:12px;color:#888;margin-bottom:10px;letter-spacing:.04em;text-transform:uppercase;}}
  .value{{font-size:28px;font-weight:700;}}
  .sub{{font-size:12px;color:#666;margin-top:6px;}}
  .error{{background:#2d1515;border:1px solid #c53030;color:#fc8181;padding:16px;border-radius:10px;}}
  .footer{{margin-top:40px;font-size:12px;color:#555;text-align:center;}}
  @media(max-width:600px){{.grid{{grid-template-columns:1fr 1fr;}}}}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div class="brand">{CLIENT_NAME}</div>
    <div class="live"><div class="dot"></div>Live data — updates every 5 min</div>
  </div>
  <div class="tagline">Your campaign numbers, always real, always visible.</div>
  {status_section}
  {cards}
  <div class="footer">Last loaded: {updated} · Powered by your campaign's real Meta data · Refreshes automatically</div>
</div>
</body>
</html>'''


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data, error = fetch_summary()
        html = render_dashboard(data, error).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def log_message(self, fmt, *args):
        print("[dashboard]", fmt % args)


if __name__ == "__main__":
    print(f"Dashboard running at http://localhost:{PORT}")
    print("Share this URL with your client once hosted publicly.")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
