# Outcome and evidence gate

Keep stage results orthogonal:

- prediction is a solver result;
- action execution is a driver result;
- provider verification is a provider result;
- business acceptance is a first-party backend result;
- promotion is a policy decision over all required receipts.

Only a `BusinessAcceptanceReceipt` created from the final first-party protected business API and ledger assertions can set business acceptance to `accepted`.

Promotion additionally requires:

1. a verified, valid authorization record;
2. all actions within the approved scope;
3. accepted response assertions;
4. matching owner, session, worker, object, and version assertions;
5. a fresh repeat round when required;
6. zero business-ledger delta for every negative control.

When evidence is missing, return `ineligible` or `negative_only` and list the exact missing evidence. Do not infer success from transport status.
