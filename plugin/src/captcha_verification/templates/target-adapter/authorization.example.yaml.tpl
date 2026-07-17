schema_version: captcha-authorization/v1
authorization_id: "replace-with-auditable-id"
subject: "replace-with-authorized-party"
controller: "replace-with-controller"
target_environment_id: "{{ target_id }}-integration"
allowed_hosts: []
allowed_routes: []
allowed_methods: []
allowed_actions: []
prohibited_actions:
  - stealth
  - webdriver_hiding
  - fingerprint_spoofing
  - clearance_cookie_reuse
  - token_fabrication
basis: oral_claim
status: claimed_unverified
fact_level: unverified
evidence: []
issued_at: "2000-01-01T00:00:00Z"
expires_at: "2099-01-01T00:00:00Z"
revocation_contact: "replace-before-use"
data_handling_scope: "replace-before-use"
production_allowed: false
operator_acknowledged: false
