#!/usr/bin/env python3
import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"
MARKET_DIR = BASE_DIR / "data" / "pb_wave_market"
TRADER_DIR = BASE_DIR / "data" / "pb_wave_trader"

HOST = os.environ.get("PB_WAVE_BACKEND_HOST", "0.0.0.0")
PORT = int(os.environ.get("PB_WAVE_BACKEND_PORT", "8080"))


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


class Handler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            return self.serve_file(APP_DIR / "index.html", "text/html; charset=utf-8", head_only=True)
        if parsed.path == "/app.js":
            return self.serve_file(APP_DIR / "app.js", "application/javascript; charset=utf-8", head_only=True)
        if parsed.path == "/styles.css":
            return self.serve_file(APP_DIR / "styles.css", "text/css; charset=utf-8", head_only=True)
        if parsed.path == "/healthz":
            return self.send_json({"ok": True}, head_only=True)
        return self.send_json({"error": "Not found"}, 404, head_only=True)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            return self.serve_file(APP_DIR / "index.html", "text/html; charset=utf-8")
        if parsed.path == "/app.js":
            return self.serve_file(APP_DIR / "app.js", "application/javascript; charset=utf-8")
        if parsed.path == "/styles.css":
            return self.serve_file(APP_DIR / "styles.css", "text/css; charset=utf-8")
        if parsed.path == "/healthz":
            return self.send_json({"ok": True})
        if parsed.path == "/api/market":
            return self.send_json(
                {
                    "rows": read_json(MARKET_DIR / "latest.json", default=[]) or [],
                    "manifest": read_json(MARKET_DIR / "meta" / "manifest.json", default={}) or {},
                }
            )
        if parsed.path == "/api/trader":
            return self.send_json(read_json(TRADER_DIR / "latest.json", default={}) or {})
        return self.send_json({"error": "Not found"}, 404)

    def serve_file(self, path: Path, content_type: Optional[str] = None, head_only: bool = False):
        if not path.exists():
            return self.send_json({"error": "Not found"}, 404, head_only=head_only)
        data = path.read_bytes()
        ctype = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if not head_only:
            self.wfile.write(data)

    def send_json(self, payload, status=200, head_only: bool = False):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if not head_only:
            self.wfile.write(data)

    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"pb-wave-clean readonly server on http://{HOST}:{PORT}")
    server.serve_forever()
