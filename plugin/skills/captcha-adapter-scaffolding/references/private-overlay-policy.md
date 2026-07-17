# Private overlay policy

Partner-specific target code, domain bindings, authorization evidence, accounts, raw captures, and business assertions belong in a private repository or an ignored `private/targets/<target-id>/` overlay.

The public core may contain provider-neutral templates and self-owned or official sandbox fixtures. Public artifacts must fail if a private overlay path is included in the package manifest.
