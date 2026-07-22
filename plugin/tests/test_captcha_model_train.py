from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from captcha_model_train import (  # noqa: E402
    TrainingDependencyError,
    make_trained_predictions,
    split_samples,
    text_accuracy,
    train_centroids,
)


def _sample(tmp_path: Path, sample_id: str, split: str, answer: str = "ABCDE") -> dict[str, object]:
    from PIL import Image, ImageDraw

    image_path = tmp_path / f"{sample_id}.png"
    label_path = tmp_path / f"{sample_id}.json"
    image = Image.new("RGB", (210, 78), "white")
    draw = ImageDraw.Draw(image)
    draw.text((12, 18), answer, fill="black")
    image.save(image_path)
    label_path.write_text(json.dumps({"answer": answer}), encoding="utf-8")
    return {
        "sample_id": sample_id,
        "challenge_type": "text-captcha",
        "difficulty": "easy",
        "image_path": str(image_path),
        "label_path": str(label_path),
        "split": split,
        "answer": answer,
    }


def test_training_helpers_keep_explicit_splits_and_metrics(tmp_path: Path) -> None:
    samples = [
        _sample(tmp_path, "train-1", "train"),
        _sample(tmp_path, "val-1", "val"),
        _sample(tmp_path, "test-1", "test"),
        {**_sample(tmp_path, "slider-1", "train"), "challenge_type": "slider-captcha"},
    ]
    manifest = {"samples": samples}
    splits = split_samples(manifest)
    assert {item["sample_id"] for item in splits["train"]} == {"train-1"}
    assert {item["sample_id"] for item in splits["val"]} == {"val-1"}
    assert {item["sample_id"] for item in splits["test"]} == {"test-1"}

    model = train_centroids(splits["train"])
    metrics = text_accuracy(splits["train"], model)
    assert metrics["sample_count"] == 1
    assert 0 <= metrics["char_accuracy"] <= 1
    assert 0 <= metrics["sequence_accuracy"] <= 1


def test_generated_predictions_preserve_no_leakage_claim(tmp_path: Path) -> None:
    sample = _sample(tmp_path, "train-1", "train")
    manifest = {"run_id": "test-run", "samples": [sample]}
    baseline = {
        "predictions": [{
            "sample_id": sample["sample_id"],
            "challenge_type": "text-captcha",
            "prediction": "AAAAA",
        }]
    }
    model = train_centroids([sample])
    output = tmp_path / "predictions.json"
    payload = make_trained_predictions(manifest, baseline, model, output)
    assert payload["leakage_claim"]["label_read_for_prediction"] is False
    assert payload["leakage_claim"]["dom_read_for_prediction"] is False
    assert payload["leakage_claim"]["query_param_read_for_prediction"] is False
    assert payload["leakage_claim"]["metadata_answer_read_for_prediction"] is False
    assert output.is_file()


def test_torch_backend_has_explicit_optional_dependency_boundary() -> None:
    try:
        import torch  # noqa: F401
    except ImportError:
        from captcha_model_train import train_torch_cnn

        with pytest.raises(TrainingDependencyError, match="optional deep-learning dependency"):
            train_torch_cnn([])
