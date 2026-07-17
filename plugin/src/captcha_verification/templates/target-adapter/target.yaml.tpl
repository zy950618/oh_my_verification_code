schema_version: captcha-target-adapter/v1
adapter_id: "{{ adapter_id }}"
adapter_version: 0.1.0
target_id: "{{ target_id }}"
challenge_family: "{{ challenge_family }}"
visibility: private
execution_policy: generate_only
transports: {{ transports_json }}
provider:
  name: unknown
  fact_level: unverified
capabilities:
  classify: false
  solve: false
  plan_action: false
  execute_action: false
  verify_business_acceptance: false
missing_evidence:
  - verified authorization record
  - observed provider binding
  - first-party business acceptance assertions
