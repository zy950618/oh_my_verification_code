# test.cap.guru captcha memory

```yaml
domain: test.cap.guru
provider: hcaptcha
captcha_type: hcaptcha_checkbox_with_drag_drop_challenge
version: first_observed_2026-06-15
completion_status: blocked
blocked_stage: verified
blocked_reason: manual_challenge_required
scope:
  market: unverified
  locale: zh observed in provider assets
  auth_state: anonymous
  business_stage: demo/hcap#hcap1
site_binding:
  sitekey: 471c62d2-22ce-4903-9ce0-0132d0018b03
  action: unverified
  mode: checkbox
  widget_script: https://hcaptcha.com/1/api.js?hl=zh
  widget_script_hash: 150c59452c88cd19e7c25a300d2b1bff149bf0ea9fe574a0c2f8e14ce0455327
challenge:
  config_endpoint: https://api.hcaptcha.com/checksiteconfig
  challenge_endpoint: https://api.hcaptcha.com/getcaptcha/<sitekey>
  challenge_type_observed: image_drag_drop
  request_fields: redacted in stored artifacts
token:
  token_field: body.tok sent to /proverka.php; DOM source f_textarea_<sitekey>
  ttl_observed: unverified
  bound_to:
    - domain
    - sitekey
    - browser_session
verify:
  verify_endpoint: POST https://test.cap.guru/proverka.php
  request_fields:
    - key
    - tok
  success_pointer: unverified
  failure_pointer: /status == fail
state_write:
  cookies: no site state write confirmed
  local_storage: no site state write confirmed
  session_storage: no site state write confirmed
effects:
  unlocks_endpoint: unverified
  changes_response: empty token returns /status fail
  blocks_replay: unverified
  breaks_concurrency: unverified
captures:
  clean_unverified: cap_clean_unverified_001
  unverified_submit: cap_unverified_submit_001
  verified: blocked_by_manual_drag_drop_challenge
  repeat_verified: blocked_until_verified_capture_exists
freshness:
  old_evidence_invalidated: no prior domain evidence existed
  revalidated_by: run_20260615T112359_test_cap_guru_hcap1
```

## Human Review Protocol

```yaml
visible_browser:
  required: true
  launch_command_or_tool: use a visible Chrome/DevTools session or equivalent HAR-capable browser
  browser_profile_id: new profile dedicated to run_20260615T112359_test_cap_guru_hcap1_verified
  state_reset: clear test.cap.guru and hcaptcha cookies/storage/cache or record any retained state
target:
  url: https://test.cap.guru/demo/hcap?utm_source=chatgpt.com#hcap1
  variant: hcap1
  sitekey: 471c62d2-22ce-4903-9ce0-0132d0018b03
  auth_state: anonymous
user_action:
  instruction: complete only the visible hCaptcha drag/drop challenge
  stop_after: the hCaptcha token field is non-empty or the site result area updates after pressing Verif
live_capture:
  listener: browser DevTools HAR or equivalent network capture
  must_capture:
    - api.hcaptcha.com checksiteconfig/getcaptcha requests with payloads redacted
    - POST https://test.cap.guru/proverka.php request/response
    - cookie/localStorage/sessionStorage diffs
    - screenshot after completion
completion_criteria:
  token_state: f_textarea_<sitekey> or h-captcha-response becomes non-empty; record length only
  backend_acceptance: /proverka.php response JSON Pointer /status == success
  evidence_required:
    - request URL/method/status
    - redacted request fields key/tok
    - response JSON Pointer /status
    - capture_id and captured_at
repeat_flow:
  action: reopen or create a fresh browser context and repeat the same visible-browser flow
  expected: repeat capture produces the same backend acceptance without reusing old token values
  failure_handling: write repeat failure to known-failures.md and keep completion_status blocked
artifact_paths:
  har: metrics/captures/test.cap.guru/hcap1/<run_id>/human_verified.har
  summary: metrics/captures/test.cap.guru/hcap1/<run_id>/human_verified.summary.json
  screenshot: metrics/captures/test.cap.guru/hcap1/<run_id>/human_verified.png
  memory_update: 验证码经验库/domains/test.cap.guru/captcha-memory.md
```

## Fact labels

- observed: hCaptcha script loads, hcap1 sitekey exists, site script renders hCaptcha and posts `{key, tok}`, empty token returns `/status == fail`, checkbox interaction opens drag/drop challenge.
- derived: `/proverka.php` is the site backend verify endpoint because `web/js/1.js` line 270 posts `{key, tok}` and the unverified submit response is captured from that endpoint.
- unverified: solved hCaptcha token, success pointer, token TTL, cookie/storage binding, repeat verified state, concurrency, other hCaptcha variants.

## run_20260615T115700_test_cap_guru_cloud1

```yaml
domain: test.cap.guru
provider: cloudflare_turnstile
captcha_type: turnstile_managed_checkbox
version: observed_2026-06-15
completion_status: blocked
blocked_stage: verified
blocked_reason: manual_challenge_required
scope:
  market: unverified
  locale: zh text observed in widget
  auth_state: anonymous
  business_stage: demo/cloud#cloud1
site_binding:
  sitekey: 0x4AAAAAAAFgtad7pcAaTILY
  action: unverified
  mode: managed
  widget_script: https://challenges.cloudflare.com/turnstile/v0/api.js
  widget_script_hash: 550ee5324f2c405d2e21206bd7099b9dcca18a052483b70695f2c7c971322d4e
  site_script: https://test.cap.guru/web/js/1.js?1781495882
  site_script_hash: bb90452020dfe6f8bcfd1a95f81711dc204ed5f045f533ce8df423dae004ec2c
challenge:
  iframe_endpoint: https://challenges.cloudflare.com/cdn-cgi/challenge-platform/h/g/turnstile/f/ov2/av0/rch/<widget_id>/<sitekey>/auto/<opaque>/new/normal?lang=auto
  flow_endpoint: https://challenges.cloudflare.com/cdn-cgi/challenge-platform/h/g/flow/ov1/<opaque>
  challenge_type_observed: managed_checkbox_prompt
  request_fields: redacted in stored artifacts
token:
  token_field: body.tok sent to /proverka.php; DOM source f_textarea_0x4AAAAAAAFgtad7pcAaTILY
  provider_field: cf-turnstile-response hidden input
  token_value_observed: false
  ttl_observed: unverified
  bound_to:
    - domain
    - sitekey
    - browser_session
verify:
  verify_endpoint: POST https://test.cap.guru/proverka.php
  request_fields:
    - key
    - tok
  success_pointer: unverified
  failure_pointer: /status == fail
state_write:
  cookies: no site cookie write confirmed in clean capture
  local_storage: no site localStorage write confirmed
  session_storage: no site sessionStorage write confirmed
effects:
  unlocks_endpoint: unverified
  changes_response: empty token returns /status fail
  blocks_replay: unverified
  breaks_concurrency: unverified
captures:
  clean_unverified: metrics/captures/test.cap.guru/cloud1/run_20260615T115700_test_cap_guru_cloud1/clean_unverified.summary.json
  unverified_submit: metrics/captures/test.cap.guru/cloud1/run_20260615T115700_test_cap_guru_cloud1/unverified_submit.summary.json
  verified: blocked_by_turnstile_checkbox_challenge
  repeat_verified: blocked_until_verified_capture_exists
freshness:
  old_evidence_invalidated: prior hcap1 evidence is different provider/stage and not reused for cloud1 facts
  revalidated_by: run_20260615T115700_test_cap_guru_cloud1
```

### Human Review Protocol - cloud1

```yaml
visible_browser:
  required: true
  launch_command_or_tool: visible Chrome with DevTools Network recording or equivalent HAR-capable browser
  browser_profile_id: new isolated profile, e.g. test_cap_guru_cloud1_human_verified
  state_reset: clear cookies, localStorage, sessionStorage, cache storage, and service workers for test.cap.guru and challenges.cloudflare.com when possible
target:
  url: https://test.cap.guru/demo/cloud#cloud1
  variant: cloud1
  sitekey: 0x4AAAAAAAFgtad7pcAaTILY
  mode: managed
  auth_state: anonymous
user_action:
  instruction: complete only the visible Turnstile challenge shown by the page, then press the page Verif button if it is not pressed automatically
  stop_after: the page result area shows a backend response or f_textarea_0x4AAAAAAAFgtad7pcAaTILY is non-empty
live_capture:
  listener: DevTools Network HAR with cache disabled
  must_capture:
    - Cloudflare Turnstile iframe/flow requests with payload redaction
    - POST https://test.cap.guru/proverka.php request and response
    - cookie/localStorage/sessionStorage diffs
    - screenshot after completion
completion_criteria:
  token_state: f_textarea_0x4AAAAAAAFgtad7pcAaTILY or cf-turnstile-response becomes non-empty; store length only
  backend_acceptance: /proverka.php response JSON Pointer /status == success
repeat_flow:
  action: use a new context or documented refresh after the first verified capture
  expected: repeat_verified captures a fresh accepted backend response
failure_path:
  known_failure: 站点经验库/test.cap.guru/known-failures.md
  captcha_memory: 验证码经验库/domains/test.cap.guru/captcha-memory.md
```

### Fact labels - cloud1

- observed: Turnstile API script loads, cloud1 sitekey exists, the widget renders in managed checkbox mode, token fields are empty in clean capture, empty-token submit returns `/status == fail`.
- derived: `/proverka.php` is the site backend verify endpoint because `web/js/1.js?1781495882` line 270 posts `{key, tok}` and the unverified submit response is captured from that endpoint.
- unverified: solved Turnstile token, success pointer, token TTL, cookie/storage binding, repeat verified state, concurrency, other Cloudflare variants.
