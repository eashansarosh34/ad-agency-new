from http.server import BaseHTTPRequestHandler, HTTPServer
import json

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("[mock-tavily]", fmt % args)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode())
        print(f"[mock-tavily] Received query: {body.get('query')}")
        if "query" not in body or "api_key" not in body:
            self.send_response(400); self.end_headers(); return

        results = {"results": [
            {"title": "Short-form video now dominates local service ads",
             "content": "Vertical video ads are outperforming static images by 30-50% lower cost-per-lead in 2026, especially for local clinics and gyms in India.",
             "url": "https://example.com/trend1"},
            {"title": "Click-to-WhatsApp ads overtaking landing pages",
             "content": "Meta confirms WhatsApp-first lead capture is now the dominant pattern for Indian local lead generation.",
             "url": "https://example.com/trend2"},
        ]}
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(results).encode())

if __name__ == "__main__":
    server = HTTPServer(("localhost", 8006), Handler)
    print("Mock Tavily running on http://localhost:8006")
    server.serve_forever()
