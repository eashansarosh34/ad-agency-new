"""
Mock Meta Graph API server — for local testing of Agent 02 and Agent 03
without touching a real ad account.

Run: python3 mock_meta_server.py
Serves on http://localhost:8001
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta, timezone
import json
import re

# Fake ad-level data: 4 ads with varied performance so Agent 02 has
# real decisions to make (one bad CPL to pause, one great CPL to boost).
MOCK_ADS = [
    {"ad_id": "1001", "ad_name": "Free Consultation — This Weekend", "adset_id": "2001",
     "spend": "4200", "actions": [{"action_type": "lead", "value": "21"}], "ctr": "4.8"},
    {"ad_id": "1002", "ad_name": "Before / After — Smile Makeover", "adset_id": "2002",
     "spend": "3100", "actions": [{"action_type": "lead", "value": "14"}], "ctr": "3.1"},
    {"ad_id": "1003", "ad_name": "Painless Root Canal — Myth Busting", "adset_id": "2003",
     "spend": "2900", "actions": [{"action_type": "lead", "value": "9"}], "ctr": "2.4"},
    {"ad_id": "1004", "ad_name": "Generic Dental Checkup Ad", "adset_id": "2004",
     "spend": "3800", "actions": [{"action_type": "lead", "value": "3"}], "ctr": "1.1"},
]

MOCK_ACCOUNT_TOTALS = {
    "impressions": "38420", "clicks": "5390", "spend": "18400",
    "actions": [{"action_type": "lead", "value": "47"}],
}
MOCK_ACCOUNT_TOTALS_PREVIOUS = {
    "impressions": "35100", "clicks": "4700", "spend": "19800",
    "actions": [{"action_type": "lead", "value": "31"}],
}

ADSET_BUDGETS = {"2001": 5000, "2002": 4000, "2003": 3500, "2004": 4500}


class MockHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload, code=200):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("[mock-meta]", fmt % args)

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        # /v21.0/{act_id}/insights
        if parsed.path.endswith("/insights"):
            level = params.get("level", [None])[0]
            if level == "ad":
                self._send_json({"data": MOCK_ADS})
                return

            time_range_raw = params.get("time_range", ["{}"])[0]
            try:
                since_str = json.loads(time_range_raw).get("since")
                since_date = datetime.strptime(since_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except Exception:
                since_date = datetime.now(timezone.utc)

            is_recent_window = since_date >= (datetime.now(timezone.utc) - timedelta(days=8))
            totals = MOCK_ACCOUNT_TOTALS if is_recent_window else MOCK_ACCOUNT_TOTALS_PREVIOUS
            self._send_json({"data": [totals]})
            return

        # /v21.0/{adset_id}  (fetch current budget)
        m = re.search(r"/(\d{4})$", parsed.path)
        if m and m.group(1) in ADSET_BUDGETS:
            self._send_json({"daily_budget": str(ADSET_BUDGETS[m.group(1)])})
            return

        self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        # Ad status update (pause) or ad set budget update — both just acknowledged.
        length = int(self.headers.get("Content-Length", 0))
        _ = self.rfile.read(length)
        self._send_json({"success": True})


if __name__ == "__main__":
    server = HTTPServer(("localhost", 8001), MockHandler)
    print("Mock Meta API running on http://localhost:8001")
    server.serve_forever()
