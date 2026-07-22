from __future__ import annotations

import json
import secrets
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


class LocalReferenceServer:
    """Self-owned HTTP business lab; no external target or browser signing."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path.cwd() / ".captcha-local-reference"
        self.root.mkdir(parents=True, exist_ok=True)
        self.database = self.root / "ledger.sqlite3"
        self._lock = threading.Lock()
        with sqlite3.connect(self.database) as db:
            db.execute("create table if not exists challenges (id text primary key, answer text, session_id text, used integer, expires real)")
            db.execute("create table if not exists orders (id text primary key, challenge_id text, session_id text, owner_id text)")

    def issue(self, family: str = "slider", session_id: str = "local-session") -> dict[str, str]:
        challenge_id = f"challenge-{secrets.token_hex(8)}"
        answer = "80" if family == "slider" else "accepted"
        with sqlite3.connect(self.database) as db:
            db.execute("insert into challenges values (?, ?, ?, 0, ?)", (challenge_id, answer, session_id, time.time() + 60))
        return {"challenge_instance_id": challenge_id, "family": family, "session_id": session_id}

    def verify(self, challenge_id: str, answer: str, session_id: str) -> bool:
        with self._lock, sqlite3.connect(self.database) as db:
            row = db.execute("select answer, session_id, used, expires from challenges where id = ?", (challenge_id,)).fetchone()
            if not row or row[2] or row[3] <= time.time() or row[0] != answer or row[1] != session_id:
                return False
            db.execute("update challenges set used = 1 where id = ?", (challenge_id,))
            return True

    def order(self, challenge_id: str, session_id: str, owner_id: str) -> dict[str, Any] | None:
        order_id = f"order-{secrets.token_hex(8)}"
        with self._lock, sqlite3.connect(self.database) as db:
            row = db.execute("select used from challenges where id = ?", (challenge_id,)).fetchone()
            if not row or not row[0]:
                return None
            db.execute("insert into orders values (?, ?, ?, ?)", (order_id, challenge_id, session_id, owner_id))
        return {"object_id": order_id, "challenge_instance_id": challenge_id, "session_id": session_id, "owner_id": owner_id}

    def ledger_count(self) -> int:
        with sqlite3.connect(self.database) as db:
            return int(db.execute("select count(*) from orders").fetchone()[0])


class _Handler(BaseHTTPRequestHandler):
    lab: LocalReferenceServer

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json(200, {"status": "ready", "scope": "first_party_local_reference_only"})
        elif self.path == "/api/ledger":
            self._json(200, {"count": self.lab.ledger_count()})
        else:
            self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/api/challenges":
            self._json(200, self.lab.issue(str(payload.get("family", "slider")), str(payload.get("session_id", "local-session"))))
        elif self.path == "/api/provider/verify":
            accepted = self.lab.verify(str(payload.get("challenge_instance_id", "")), str(payload.get("answer", "")), str(payload.get("session_id", "")))
            self._json(200 if accepted else 403, {"accepted": accepted, "provider": "first_party_local_reference"})
        elif self.path == "/api/business/orders":
            order = self.lab.order(str(payload.get("challenge_instance_id", "")), str(payload.get("session_id", "")), str(payload.get("owner_id", "")))
            self._json(200 if order else 403, order or {"accepted": False})
        else:
            self._json(404, {"error": "not_found"})


def serve(root: Path | None = None) -> ThreadingHTTPServer:
    lab = LocalReferenceServer(root)
    class Handler(_Handler):
        pass
    Handler.lab = lab
    return ThreadingHTTPServer(("127.0.0.1", 0), Handler)
