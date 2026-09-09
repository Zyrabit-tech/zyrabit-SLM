#!/usr/bin/env python3
"""Minimal local ticket inbox — stands in for Jira/Linear/n8n webhook."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)
TICKETS = OUT / "tickets.jsonl"
PORT = 8765


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:  # quieter
        print(f"[ticket-inbox] {self.address_string()} - {fmt % args}")

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/health", "/"):
            self._json(200, {"status": "ok", "service": "mock-ticket-inbox", "port": PORT})
            return
        if self.path == "/tickets":
            rows = []
            if TICKETS.exists():
                for line in TICKETS.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        rows.append(json.loads(line))
            self._json(200, {"count": len(rows), "tickets": rows})
            return
        self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/tickets":
            self._json(404, {"error": "not_found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid_json"})
            return
        ticket = {
            "id": f"TCK-{uuid.uuid4().hex[:8].upper()}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "title": data.get("title") or "untitled",
            "priority": data.get("priority") or "medium",
            "body": data.get("body") or "",
            "source": data.get("source") or "zyrabit-case3-demo",
            "requester": data.get("requester") or "unknown",
        }
        with TICKETS.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ticket, ensure_ascii=False) + "\n")
        self._json(201, {"ok": True, "ticket": ticket})


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"mock ticket inbox on http://127.0.0.1:{PORT}  (POST /tickets)")
    print(f"persisting to {TICKETS}")
    server.serve_forever()


if __name__ == "__main__":
    main()
