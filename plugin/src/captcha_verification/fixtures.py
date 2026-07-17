from __future__ import annotations

import json
import math
import random
from pathlib import Path

from captcha_verification.canonical import file_sha256
from captcha_verification.contracts import AssetRef


FIXTURE_VERSION = "reference-fixtures-v1"


def _pillow():
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise RuntimeError("Install captcha-verification-skills[vision]") from exc
    return Image, ImageDraw


def generate_reference_fixtures(root: Path, *, count_per_family: int = 4) -> dict[str, object]:
    """Generate deterministic self-owned raster fixtures and separated evaluator labels."""
    Image, ImageDraw = _pillow()
    image_root = root / "images"
    label_root = root / "server-labels"
    image_root.mkdir(parents=True, exist_ok=True)
    label_root.mkdir(parents=True, exist_ok=True)
    samples: list[dict[str, object]] = []
    for index in range(count_per_family):
        rng = random.Random(20260717 + index)
        width, height = 330, 170
        image = Image.new("RGB", (width, height), (172, 196, 210))
        draw = ImageDraw.Draw(image)
        for x in range(0, width, 12):
            shade = 135 + (x * 11) % 65
            draw.rectangle((x, 0, x + 7, height), fill=(shade, min(230, shade + 20), min(240, shade + 32)))
        gap_x, gap_y = 90 + index * 35, 42 + index * 13
        gap_w, gap_h = 38, 38
        draw.rectangle((gap_x + 4, gap_y + 5, gap_x + gap_w + 4, gap_y + gap_h + 5), fill=(60, 70, 75))
        draw.rectangle((gap_x, gap_y, gap_x + gap_w, gap_y + gap_h), fill=(248, 250, 251), outline=(35, 55, 65), width=2)
        path = image_root / f"slider-{index:03d}.png"
        image.save(path)
        label = {"family": "slider", "offset": {"x": gap_x + 1, "y": gap_y + 1}}
        label_path = label_root / f"slider-{index:03d}.json"
        label_path.write_text(json.dumps(label, sort_keys=True), encoding="utf-8")
        samples.append(_sample(path, label_path, "slider", index))

        size = 170
        angle = (28 + index * 73) % 360
        image = Image.new("RGB", (size, size), (236, 241, 244))
        draw = ImageDraw.Draw(image)
        cx = cy = size // 2
        radians = math.radians(angle)
        end = (cx + int(math.cos(radians) * 58), cy - int(math.sin(radians) * 58))
        draw.ellipse((20, 20, size - 20, size - 20), outline=(115, 130, 140), width=2)
        draw.line((cx, cy, end[0], end[1]), fill=(220, 42, 42), width=8)
        draw.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), fill=(55, 65, 75))
        draw.ellipse((end[0] - 8, end[1] - 8, end[0] + 8, end[1] + 8), fill=(220, 42, 42))
        path = image_root / f"rotate-{index:03d}.png"
        image.save(path)
        label = {"family": "rotate", "angle_degrees": angle}
        label_path = label_root / f"rotate-{index:03d}.json"
        label_path.write_text(json.dumps(label, sort_keys=True), encoding="utf-8")
        samples.append(_sample(path, label_path, "rotate", index))

        width, height = 260, 180
        image = Image.new("RGB", (width, height), (238, 241, 243))
        draw = ImageDraw.Draw(image)
        points = []
        for target in range(1 + index % 3):
            x = 25 + target * 72 + index * 3
            y = 30 + target * 42 + index * 2
            side = 26
            draw.rectangle((x, y, x + side, y + side), fill=(225, 45, 45), outline=(120, 10, 10), width=2)
            points.append({"x": x + side / 2, "y": y + side / 2})
        for distractor in range(5):
            x, y = rng.randint(5, 225), rng.randint(5, 145)
            draw.ellipse((x, y, x + 18, y + 18), fill=(60, 130, 205))
        path = image_root / f"click-{index:03d}.png"
        image.save(path)
        label = {"family": "click", "points": points}
        label_path = label_root / f"click-{index:03d}.json"
        label_path.write_text(json.dumps(label, sort_keys=True), encoding="utf-8")
        samples.append(_sample(path, label_path, "click", index))
    manifest = {
        "schema_version": "captcha-fixture-manifest/v1",
        "fixture_version": FIXTURE_VERSION,
        "scope": "self_owned_local_synthetic",
        "samples": samples,
    }
    (root / "dataset-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _sample(path: Path, label_path: Path, family: str, index: int) -> dict[str, object]:
    split = ("development", "calibration", "holdout", "negative")[index % 4]
    return {
        "sample_id": f"{family}-{index:03d}",
        "family": family,
        "split": split,
        "asset": {
            "asset_id": f"asset-{family}-{index:03d}",
            "uri": path.resolve().as_uri(),
            "media_type": "image/png",
            "sha256": file_sha256(path),
        },
        "server_label_path": str(label_path.resolve()),
    }


def asset_from_sample(sample: dict[str, object]) -> AssetRef:
    return AssetRef.model_validate(sample["asset"])
