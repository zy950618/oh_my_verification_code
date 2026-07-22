#!/usr/bin/env python3
"""Build and optionally execute a fresh localhost action manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ACTION_VALIDATOR = ROOT / "tools" / "validate_captcha_action_schema.py"


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_manifest(offset: float, *, challenge_instance_id: str = "localhost-slider-1", expected: float = 172) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "schema_version": "1.0.0",
        "manifest_type": "captcha_action_schema",
        "manifest_id": f"action-{_hash([challenge_instance_id, offset])[:16]}",
        "challenge_instance_id": challenge_instance_id,
        "challenge_type": "slider",
        "provider": "first_party_local_reference",
        "target_id": "captcha-vision-lab",
        "target_host": "127.0.0.1",
        "execution_allowed": True,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=2)).isoformat(),
        "coordinate_space": {"origin": "viewport_css_px", "units": "css_px", "rounding": "nearest_int"},
        "viewport": {"width": 320, "height": 160, "device_pixel_ratio": 1.0},
        "target_element": {"selector_hint": "#slider", "bbox_css_px": {"x": 0, "y": 0, "width": 320, "height": 160}},
        "mobile_h5_transform": {"input_space": "image_px", "output_space": "viewport_css_px", "device_pixel_ratio": 1.0, "image_size_px": {"width": 320, "height": 160}, "element_bbox_css_px": {"x": 0, "y": 0, "width": 320, "height": 160}, "scroll_offset_css_px": {"x": 0, "y": 0}, "safe_area_css_px": {"top": 0, "right": 0, "bottom": 0, "left": 0}},
        "provider_detection_signals": [{"kind": "dom", "value": "#slider"}, {"kind": "network_path", "value": "/index.html"}],
        "solver_input_sources": ["challenge_image"],
        "forbidden_runtime_inputs": ["label", "dom_answer", "query_expected", "cookie", "token"],
        "actions": [{"kind": "pointer_down", "x": 0, "y": 130, "time_ms": 0}, {"kind": "pointer_move", "x": offset, "y": 130, "time_ms": 100}, {"kind": "pointer_up", "x": offset, "y": 130, "time_ms": 120}],
        "challenge_state_machine": {"initial_state": "loaded", "terminal_states": ["accepted", "rejected", "blocked"], "states": ["loaded", "predicted", "action_ready", "submitted", "accepted", "rejected", "blocked"], "transitions": [{"from": "loaded", "event": "model_prediction", "to": "predicted"}, {"from": "predicted", "event": "geometry_validated", "to": "action_ready"}, {"from": "action_ready", "event": "action_replay", "to": "submitted"}, {"from": "submitted", "event": "local_lab_accept", "to": "accepted"}]},
        "capability_boundary": {"evidence_scope": "local_lab", "third_party_positive_claim": False, "business_data_status": "NOT_RUN"},
        "expected_server_offset": expected,
    }


def run_browser(manifest: dict[str, Any], output: Path, *, expected: float) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"status": "blocked", "missing_evidence": ["playwright_dependency"]}
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *_: object) -> None:
            return
    server = ThreadingHTTPServer(("127.0.0.1", 0), lambda *args, **kwargs: Handler(*args, directory=str(ROOT / "labs/public-range-labs/captcha-vision-lab"), **kwargs))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 320, "height": 160})
            page.goto(f"http://127.0.0.1:{server.server_address[1]}/index.html?expected={expected}")
            page.fill("#offset", str(manifest["actions"][-1]["x"]))
            page.click("#apply")
            state = page.locator("#state").inner_text()
            screenshot = output.with_suffix(".png")
            page.screenshot(path=str(screenshot))
            browser.close()
        return {"status": "completed" if state == "state=backend_accepted" else "failed", "state": state, "screenshot": str(screenshot), "url_host": "127.0.0.1"}
    finally:
        server.shutdown()
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--offset", type=float, default=172)
    parser.add_argument("--expected", type=float, default=172)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(args.offset, expected=args.expected)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validation = subprocess.run([sys.executable, str(ACTION_VALIDATOR), str(args.output)], cwd=ROOT, capture_output=True, text=True, check=False)
    result: dict[str, Any] = {"manifest": str(args.output), "manifest_hash": _hash(manifest), "validation_exit_code": validation.returncode, "validation": validation.stdout.strip() or validation.stderr.strip(), "execution": {"status": "not_run"}}
    if validation.returncode == 0 and args.execute:
        result["execution"] = run_browser(manifest, args.output, expected=args.expected)
    receipt = {"manifest_type": "captcha_localhost_action_receipt", "run_id": manifest["manifest_id"], "manifest_hash": result["manifest_hash"], "fact_level": "observed" if result["execution"]["status"] == "completed" else "unverified", "evidence_stage": "E2_local_executed" if result["execution"]["status"] == "completed" else "E1_static_validated", "business_data_status": "NOT_RUN", "business_success": "not_attempted", "target_host": "127.0.0.1", "negative_controls": {"wrong_offset": "required_but_not_run", "stale_instance": "required_but_not_run"}, "execution": result["execution"]}
    receipt_path = args.output.with_name(args.output.stem + "-receipt.json")
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["receipt"] = str(receipt_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if validation.returncode == 0 and result["execution"]["status"] in {"not_run", "completed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
