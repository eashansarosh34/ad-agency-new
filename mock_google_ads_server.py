"""
Mock Google Ads API + OAuth server — for local testing of Agent 07
without real Google Ads credentials.

Run: python3 mock_google_ads_server.py
Serves on http://localhost:8003
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json

# 4 campaigns with varied performance — one bad CPA to pause, ones good
# enough to boost, mirroring the same test shape used for Agent 02.
MOCK_RESULTS = [
    {"campaign": {"id": "1", "name": "Search - Implants Near Me", "resourceName": "customers/123/campaigns/1"},
     "campaignBudget": {"resourceName": "customers/123/campaignBudgets/1", "amountMicros": "500000000"},
     "metrics": {"costMicros": "320000000", "clicks": "210", "impressions": "4200", "conversions": "18"}},
    {"campaign": {"id": "2", "name": "Search - Root Canal Treatment", "resourceName": "customers/123/campaigns/2"},
     "campaignBudget": {"resourceName": "customers/123/campaignBudgets/2", "amountMicros": "400000000"},
     "metrics": {"costMicros": "280000000", "clicks": "150", "impressions": "3100", "conversions": "11"}},
    {"campaign": {"id": "3", "name": "Search - Dental Checkup", "resourceName": "customers/123/campaigns/3"},
     "campaignBudget": {"resourceName": "customers/123/campaignBudgets/3", "amountMicros": "350000000"},
     "metrics": {"costMicros": "260000000", "clicks": "95", "impressions": "2800", "conversions": "2"}},
    {"campaign": {"id": "4", "name": "Search - Generic Dentist", "resourceName": "customers/123/campaigns/4"},
     "campaignBudget": {"resourceName": "customers/123/campaignBudgets/4", "amountMicros": "300000000"},
     "metrics": {"costMicros": "200000000", "clicks": "60", "impressions": "1900", "conversions": "1"}},
]


class MockHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload, code=200):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("[mock-google-ads]", fmt % args)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(length)

        if self.path.endswith("/oauth2_token") or "oauth2.googleapis.com" in self.path:
            self._send_json({"access_token": "mock_access_token_xyz", "expires_in": 3600})
            return

        if self.path.endswith(":search"):
            self._send_json({"results": MOCK_RESULTS})
            return

        if self.path.endswith(":mutate"):
            self._send_json({"results": [{"resourceName": "mock/mutated/resource"}]})
            return

        self._send_json({"error": "not found"}, 404)


if __name__ == "__main__":
    server = HTTPServer(("localhost", 8003), MockHandler)
    print("Mock Google Ads API running on http://localhost:8003")
    server.serve_forever()
