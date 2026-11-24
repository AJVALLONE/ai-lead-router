"""Minimal webhook server (standard library only).

POST /webhook/lead with a JSON lead and an X-Signature header (HMAC-SHA256 of the raw body
using WEBHOOK_SECRET). Duplicate deliveries (same lead id) are acknowledged but not re-routed.
In production the returned tags/actions are written back to the CRM; here DRY_RUN prints them.
"""
import hashlib
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from .routing import route

SECRET = os.environ.get("WEBHOOK_SECRET", "dev-secret").encode()
_seen = set()


def verify(body, signature):
    expected = hmac.new(SECRET, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def handle(body, signature):
    if not verify(body, signature):
        return 401, {"error": "bad signature"}
    try:
        lead = json.loads(body)
    except json.JSONDecodeError:
        return 400, {"error": "invalid JSON"}
    lead_id = lead.get("id")
    if lead_id in _seen:
        return 200, {"status": "duplicate", "id": lead_id}
    _seen.add(lead_id)
    result = route(lead)
    return 200, {"status": "routed", "id": lead_id, **result}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/webhook/lead":
            self.send_error(404)
            return
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        status, payload = handle(body, self.headers.get("X-Signature"))
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)
        print(json.dumps(payload))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Listening on :{port}/webhook/lead")
    HTTPServer(("", port), Handler).serve_forever()
