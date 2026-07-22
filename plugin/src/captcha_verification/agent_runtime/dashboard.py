from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path
from typing import Iterable


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"manifest root must be object: {path}")
    return value


def summarize(root: Path) -> dict[str, object]:
    manifests = sorted(path for path in root.rglob("*.json") if path.is_file())
    statuses: Counter[str] = Counter()
    verdicts: Counter[str] = Counter()
    stages: Counter[str] = Counter()
    runs: list[dict[str, object]] = []
    for path in manifests:
        try:
            item = _load(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        status = item.get("status")
        verdict = item.get("verdict") or item.get("review_status")
        stage = item.get("evidence_stage")
        if isinstance(status, str):
            statuses[status] += 1
        if isinstance(verdict, str):
            verdicts[verdict] += 1
        if isinstance(stage, str):
            stages[stage] += 1
        if item.get("manifest_type") in {"agent_result", "agent_eval_run", "review_verdict"}:
            runs.append({"path": str(path), "id": item.get("job_id") or item.get("run_id"), "status": status, "verdict": verdict, "evidence_stage": stage})
    return {"manifest_type": "agent_dashboard_summary", "root": str(root), "manifest_count": len(manifests), "status_counts": dict(statuses), "verdict_counts": dict(verdicts), "evidence_stage_counts": dict(stages), "runs": runs}


def render_html(summary: dict[str, object]) -> str:
    payload = html.escape(json.dumps(summary, ensure_ascii=False, indent=2))
    return "<!doctype html><meta charset='utf-8'><title>CAPTCHA runtime dashboard</title><h1>CAPTCHA runtime dashboard</h1><p>Read-only local manifests. Unverified results are not capability passes.</p><pre>" + payload + "</pre>"


def serve(root: Path, *, host: str = "127.0.0.1", port: int = 8765) -> None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("dashboard server must bind to loopback")
    summary = summarize(root)
    rendered = render_html(summary).encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(rendered)))
            self.end_headers()
            self.wfile.write(rendered)

        def log_message(self, *_args: object) -> None:
            return

    ThreadingHTTPServer((host, port), Handler).serve_forever()
