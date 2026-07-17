# Authorization and scope

An `AuthorizationRecord` records what is known about permission. A separate scope record controls what an executor may do.

Required authorization fields include the subject/controller, target environment, authorization basis and evidence references, allowed environments, validity window, revocation contact, production permission, data handling, and fact level.

An oral or user-claimed basis is recorded as `unverified` and must not enable production execution. Successful technical interaction cannot upgrade authorization.

Every executable scope must bind:

- target ID and environment;
- allowed hosts, routes, methods, and actions;
- start and expiry times;
- request and concurrency limits;
- retention and redaction rules;
- operator acknowledgement when required.

A target adapter cannot broaden its own scope.
