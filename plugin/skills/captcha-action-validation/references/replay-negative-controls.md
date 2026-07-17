# Replay negative controls

Authorized replay must test applicable negative states:

- stale or expired challenge and plan;
- duplicate token or action;
- wrong session, action, owner, worker, or coordinate frame;
- cross-worker pollution;
- cancellation and timeout;
- provider rejection despite transport success;
- final business assertion mismatch;
- non-zero ledger delta from a negative request.

A negative-control pass means the incorrect request was rejected without unintended business state. It is not a positive CAPTCHA capability.
