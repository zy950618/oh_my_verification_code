# CAPTCHA Model Lab Inference API

## Command

Run from the repository root:

```bash
python evidence/public-range/captcha-model-lab/inference/sample_infer.py
```

## Input

The sample inference script reads the canonical dataset manifest and local synthetic images under `samples/images/`.

## Output

The script writes `inference/sample_predictions.json` and each prediction contains `sample_id`, `predicted_offset_css_px`, `confidence`, `prediction_status`, and an action sequence compatible with `captcha_action_schema@0.1.0`.

## Boundary

This API is local-lab only. It does not contact CAPTCHA providers, remote solver APIs, live targets, or user sessions.
