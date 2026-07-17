#!/usr/bin/env python3
"""List geometry-based CAPTCHA solver support."""
from __future__ import annotations
import json
if __name__ == "__main__":
    print(json.dumps({"operation_status": "succeeded", "registry_status": "legacy_inventory_only", "solvers": ["slider gap x/y", "rotate angle", "click point centroid"], "leakage": "challenge_image_only"}, indent=2))

