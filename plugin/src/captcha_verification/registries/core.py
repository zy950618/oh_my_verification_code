from __future__ import annotations

import importlib
from collections.abc import Iterable

from captcha_verification.canonical import artifact_hash
from captcha_verification.contracts import RegistryEntry


class Registry:
    def __init__(self, entries: Iterable[RegistryEntry] = ()) -> None:
        self._entries: dict[tuple[str, str, str], RegistryEntry] = {}
        for entry in entries:
            self.register(entry)

    def register(self, entry: RegistryEntry) -> None:
        key = (entry.entry_type, entry.entry_id, entry.version)
        if key in self._entries:
            raise ValueError(f"duplicate registry entry: {key}")
        self._entries[key] = entry

    def list(self, entry_type: str | None = None) -> list[RegistryEntry]:
        entries = self._entries.values()
        if entry_type:
            entries = (entry for entry in entries if entry.entry_type == entry_type)
        return sorted(entries, key=lambda item: (item.entry_type, item.entry_id, item.version))

    def get(self, entry_type: str, entry_id: str, version: str | None = None) -> RegistryEntry:
        candidates = [
            entry
            for (kind, identifier, _), entry in self._entries.items()
            if kind == entry_type and identifier == entry_id and (version is None or entry.version == version)
        ]
        if not candidates:
            raise KeyError(f"unknown registry entry: {(entry_type, entry_id, version)}")
        if version is None:
            active = [entry for entry in candidates if entry.lifecycle_state == "active"]
            candidates = active or candidates
        return sorted(candidates, key=lambda item: item.version)[-1]

    def validate_imports(self) -> list[str]:
        errors: list[str] = []
        for entry in self._entries.values():
            if entry.runtime_eligibility == "negative_eval_only" and entry.lifecycle_state == "active":
                errors.append(f"{entry.entry_id}: negative_eval_only entries cannot be active")
            if entry.runtime_eligibility == "positive_local_reference" and not entry.sha256:
                errors.append(f"{entry.entry_id}: local-reference entry is missing sha256")
            if not entry.import_path:
                continue
            module_name, separator, attribute = entry.import_path.partition(":")
            if not separator:
                errors.append(f"{entry.entry_id}: import_path must use module:attribute")
                continue
            try:
                module = importlib.import_module(module_name)
                value = getattr(module, attribute)
                if not callable(value):
                    errors.append(f"{entry.entry_id}: import target is not callable")
            except (ImportError, AttributeError) as exc:
                errors.append(f"{entry.entry_id}: {exc}")
        return errors


DEFAULT_REGISTRY = Registry(
    [
        RegistryEntry(
            entry_type="classifier",
            entry_id="reference-raster-classifier",
            version="1.0.0",
            lifecycle_state="active",
            capabilities=["local_fixture_classification"],
            supported_challenge_families=["slider", "rotate", "click"],
            input_schema="captcha-classification-request/v1",
            output_schema="captcha-classification/v1",
            import_path="captcha_verification.classification:classify",
            sha256=artifact_hash({"id": "reference-raster-classifier", "version": "1.0.0"}),
            concurrency_safe=True,
            authorization_scopes=["self_owned_local_reference"],
            health_status="ready",
            runtime_eligibility="positive_local_reference",
        ),
        *[
            RegistryEntry(
                entry_type="solver",
                entry_id=f"reference-{family}-solver",
                version="1.0.0",
                lifecycle_state="active",
                capabilities=[f"solve_{family}_fixture"],
                supported_challenge_families=[family],
                input_schema="captcha-solve-request/v1",
                output_schema="captcha-prediction/v1",
                import_path="captcha_verification.solvers.reference:solve",
                sha256=artifact_hash({"id": f"reference-{family}-solver", "version": "1.0.0"}),
                concurrency_safe=True,
                authorization_scopes=["self_owned_local_reference"],
                health_status="ready",
                runtime_eligibility="positive_local_reference",
            )
            for family in ("slider", "rotate", "click")
        ],
        RegistryEntry(
            entry_type="model",
            entry_id="reference-raster-algorithms",
            version="1.0.0",
            lifecycle_state="active",
            capabilities=["deterministic_algorithm_descriptor"],
            supported_challenge_families=["slider", "rotate", "click"],
            input_schema="raster/v1",
            output_schema="captcha-prediction/v1",
            sha256=artifact_hash({"id": "reference-raster-algorithms", "weights": False, "families": ["slider", "rotate", "click"]}),
            authorization_scopes=["self_owned_local_reference"],
            health_status="ready",
            runtime_eligibility="positive_local_reference",
        ),
        RegistryEntry(
            entry_type="dataset",
            entry_id="reference-synthetic-raster",
            version="reference-synthetic-raster-v1",
            lifecycle_state="active",
            capabilities=["development", "calibration", "holdout", "negative"],
            supported_challenge_families=["slider", "rotate", "click"],
            input_schema="captcha-fixture-manifest/v1",
            output_schema="raster/v1",
            sha256=artifact_hash({"generator": "reference-fixtures-v1", "families": ["slider", "rotate", "click"]}),
            authorization_scopes=["self_owned_local_reference"],
            health_status="ready",
            runtime_eligibility="positive_local_reference",
        ),
        RegistryEntry(
            entry_type="action",
            entry_id="reference-action-planner",
            version="1.0.0",
            lifecycle_state="active",
            capabilities=["non_executable_plan"],
            supported_challenge_families=["slider", "rotate", "click"],
            input_schema="captcha-plan-action-request/v1",
            output_schema="captcha-action-plan/v1",
            import_path="captcha_verification.actions.planner:plan_action",
            sha256=artifact_hash({"id": "reference-action-planner", "version": "1.0.0"}),
            concurrency_safe=True,
            authorization_scopes=["self_owned_local_reference"],
            health_status="ready",
            runtime_eligibility="positive_local_reference",
        ),
        RegistryEntry(
            entry_type="target",
            entry_id="local-reference-runtime",
            version="1.0.0",
            lifecycle_state="active",
            capabilities=["localhost_first_party_receipt_chain"],
            supported_challenge_families=["slider", "rotate", "click"],
            input_schema="captcha-authorization/v1",
            output_schema="captcha-business-acceptance-receipt/v1",
            sha256=artifact_hash({"id": "local-reference-runtime", "scope": "localhost"}),
            authorization_scopes=["self_owned_local_reference"],
            health_status="ready",
            runtime_eligibility="positive_local_reference",
        ),
        RegistryEntry(
            entry_type="evidence",
            entry_id="local-reference-receipt-chain",
            version="1.0.0",
            lifecycle_state="candidate",
            capabilities=["sanitized_hash_chain"],
            input_schema="captcha-receipt-chain/v1",
            output_schema="captcha-promotion-decision/v1",
            sha256=artifact_hash({"id": "local-reference-receipt-chain", "version": "1.0.0"}),
            authorization_scopes=["self_owned_local_reference"],
            health_status="unknown",
            runtime_eligibility="documentation_only",
        ),
    ]
)
