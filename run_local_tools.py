"""
Local Proxy Server — fixes the "Failed to fetch" error in the browser tools
==============================================================================

WHY THIS EXISTS:
  agent_01 (creative_copy_agent.html), agent_06 (agent_06_local_visibility.html),
  and agent_10 (agent_10_content_social_studio.html) all call Claude directly
  from your browser. That only works inside Claude's own chat interface — not
  when you open the file yourself, because your browser correctly refuses to
  send your request straight to Anthropic's API with no authentication and no
  permission from that domain (this is CORS, a standard browser security
  rule, not a bug in your setup).

  This script fixes it by sitting in between: your browser talks to this
  script (running on your own machine), which holds your real API key and
  forwards the request to Anthropic on your behalf.

SETUP:
  1. Get an API key from console.anthropic.com -> API Keys (different from
     a claude.ai login — this is the developer API, has its own billing)
  2. export ANTHROPIC_API_KEY="your_key_here"
  3. Put this script in the SAME folder as the three HTML files
  4. python3 run_local_tools.py
  5. Open http://localhost:8000/creative_copy_agent.html in your browser
     (NOT by double-clicking the file — it must be opened through this
     server's URL, or the same CORS problem comes right back)
"""

import os
import json
import http.server
import urllib.request
import urllib.error
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from agent_12_compliance_gate import check_compliance
    COMPLIANCE_AVAILABLE = True
except ImportError:
    COMPLIANCE_AVAILABLE = False

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
PORT = int(os.environ.get("LOCAL_TOOLS_PORT", 8000))


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/api/compliance-check":
            self._handle_compliance_check()
            return
        if self.path != "/api/generate":
            self.send_response(404)
            self.end_headers()
            return

        if not ANTHROPIC_API_KEY:
            self._send_json(500, {"error": "ANTHROPIC_API_KEY is not set on this machine. "
                                            "Run: export ANTHROPIC_API_KEY=\"your_key\" then restart this script."})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                self._send_raw(resp.status, resp.read())
        except urllib.error.HTTPError as e:
            self._send_raw(e.code, e.read())
        except Exception as e:
            self._send_json(502, {"error": f"Could not reach Anthropic's API: {e}"})

    def _handle_compliance_check(self):
        if not COMPLIANCE_AVAILABLE:
            self._send_json(500, {"error": "agent_12_compliance_gate.py not found in this folder."})
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length))
            result = check_compliance(body.get("text", ""), body.get("category", "general"))
            self._send_json(200, result)
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _send_json(self, code, payload):
        self._send_raw(code, json.dumps(payload).encode())

    def _send_raw(self, code, body_bytes):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body_bytes)

    def log_message(self, fmt, *args):
        print("[local-proxy]", fmt % args)


if __name__ == "__main__":
    if not ANTHROPIC_API_KEY:
        print("WARNING: ANTHROPIC_API_KEY is not set. The server will start, but every")
        print("generate request will fail until you set it and restart.\n")
    print(f"Serving on http://localhost:{PORT}")
    print(f"Open e.g. http://localhost:{PORT}/creative_copy_agent.html in your browser.")
    server = http.server.HTTPServer(("localhost", PORT), Handler)
    server.serve_forever()
