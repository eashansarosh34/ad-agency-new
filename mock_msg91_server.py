from http.server import BaseHTTPRequestHandler, HTTPServer
import json

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("[mock-msg91]", fmt % args)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode())
        print(f"[mock-msg91] Received payload: {json.dumps(body)}")
        # Validate it looks like a real MSG91 Flow API request
        required = ["template_id", "recipients"]
        missing = [k for k in required if k not in body]
        if missing:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"type": "error", "message": f"missing {missing}"}).encode())
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"type": "success", "message": "mock-message-id-123"}).encode())

if __name__ == "__main__":
    server = HTTPServer(("localhost", 8004), Handler)
    print("Mock MSG91 running on http://localhost:8004")
    server.serve_forever()
