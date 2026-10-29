"""
Lightweight Webhook Auto-Deployment Daemon for Dota 2 Coaching Platform
Receives GitHub / GitLab Webhook events on code push and triggers automated
hot-update / container restart without any manual intervention.

Run with:
    python scripts/webhook_deployer.py
"""

import os
import hmac
import hashlib
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

PORT = int(os.environ.get("WEBHOOK_PORT", 9000))
SECRET_TOKEN = os.environ.get("WEBHOOK_SECRET", "change-me-secret-key").encode()
DEPLOY_SCRIPT = Path(__file__).resolve().parent / "deploy.sh"

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        # Check signature if provided (GitHub HMAC SHA256)
        sig_header = self.headers.get("X-Hub-Signature-256")
        gitlab_token = self.headers.get("X-Gitlab-Token")

        authenticated = False
        if gitlab_token and gitlab_token.encode() == SECRET_TOKEN:
            authenticated = True
        elif sig_header:
            expected_sig = "sha256=" + hmac.new(SECRET_TOKEN, body, hashlib.sha256).hexdigest()
            if hmac.compare_digest(sig_header, expected_sig):
                authenticated = True
        elif not os.environ.get("WEBHOOK_SECRET"):
            # No secret configured, allow trigger
            authenticated = True

        if not authenticated:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'{"status": "forbidden", "reason": "invalid signature"}')
            return

        print("[Webhook] Valid push event received! Triggering deployment script...")
        try:
            # Trigger deployment asynchronously in background
            if os.name == "nt":
                subprocess.Popen(["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(Path(__file__).resolve().parent / "deploy.ps1")])
            else:
                subprocess.Popen(["bash", str(DEPLOY_SCRIPT)])
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "deploy_triggered", "message": "Automated update in progress"}).encode())
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "ready", "service": "Dota 2 Webhook Deployer"}')

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    print(f"[*] Dota 2 Webhook Deployer listening on port {PORT}...")
    print(f"[*] Configured to trigger: {DEPLOY_SCRIPT}")
    server.serve_forever()

