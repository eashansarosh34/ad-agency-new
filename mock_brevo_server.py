from http.server import BaseHTTPRequestHandler, HTTPServer
import json

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("[mock-brevo]", fmt % args)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode())
        print(f"[mock-brevo] Received payload: {json.dumps(body)}")
        required = ["sender", "to", "subject", "htmlContent"]
        missing = [k for k in required if k not in body]
        if missing:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"message": f"missing {missing}"}).encode())
            return
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"messageId": "mock-brevo-id-456"}).encode())

if __name__ == "__main__":
    server = HTTPServer(("localhost", 8005), Handler)
    print("Mock Brevo running on http://localhost:8005")
    server.serve_forever()
