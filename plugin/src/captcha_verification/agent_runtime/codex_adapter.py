from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from captcha_verification.canonical import artifact_hash, file_sha256

from .contracts import AgentPolicyManifest, BinaryExecutionReceipt, JobManifest, ResultManifest
from .policy import evaluate_policy, policy_receipt, redact_text, scan_file_for_secrets, safe_path


class CodexAdapter:
    """Run a local Codex CLI with a host-side, deny-by-default policy."""

    def __init__(self, executable: str = "codex", *, allowed_roots: tuple[Path, ...] = ()) -> None:
        self.executable = executable
        self.allowed_roots = allowed_roots

    def run(
        self,
        job: JobManifest,
        policy: AgentPolicyManifest,
        *,
        workspace: Path | None = None,
        prompt: str | None = None,
        receipt_path: Path | None = None,
        extra_args: Sequence[str] = (),
    ) -> ResultManifest:
        decision = evaluate_policy(job, policy)
        if not decision.allowed:
            result = self._result(job, "blocked", "policy blocked", policy, decision.denied_reasons)
            return result
        if workspace is None:
            workspace = Path(tempfile.mkdtemp(prefix=f"captcha-job-{job.job_id}-"))
        workspace = safe_path(workspace, self.allowed_roots or (workspace.parent,))
        workspace.mkdir(parents=True, exist_ok=True)
        envelope = {
            "job_id": job.job_id,
            "objective": job.objective,
            "scope": job.scope.model_dump(mode="json"),
            "allowed_tools": job.allowed_tools,
            "forbidden_operations": job.forbidden_operations,
            "acceptance_criteria": [item if isinstance(item, str) else item.model_dump(mode="json") for item in job.acceptance_criteria],
        }
        envelope_path = workspace / ".captcha-job-envelope.json"
        envelope_path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        resolved = shutil.which(self.executable)
        if not resolved:
            result = self._result(job, "blocked", "codex executable unavailable", policy, ["missing_codex_cli"])
            if receipt_path:
                self._write_receipt(receipt_path, self._receipt(job, policy, result, None, workspace, [], "", "", None))
            return result
        command = [resolved, "exec", *[str(item) for item in extra_args]]
        if prompt:
            command.append(redact_text(prompt))
        env = {key: value for key, value in os.environ.items() if key in {"PATH", "HOME", "LANG", "LC_ALL"}}
        started = datetime.now(timezone.utc)
        version_output, help_output = self._introspect(resolved, env, workspace)
        try:
            completed = subprocess.run(
                command,
                cwd=workspace,
                env=env,
                shell=False,
                capture_output=True,
                text=True,
                timeout=job.resource_limits.max_seconds,
                check=False,
            )
            stdout = redact_text(completed.stdout[-job.resource_limits.max_output_bytes :])
            stderr = redact_text(completed.stderr[-job.resource_limits.max_output_bytes :])
            findings = scan_file_for_secrets(envelope_path)
            status = "completed" if completed.returncode == 0 and not findings else "failed"
            changed_files = [str(path.relative_to(workspace)) for path in workspace.rglob("*") if path.is_file() and path != envelope_path]
            result = self._result(job, status, "codex completed" if status == "completed" else "codex failed", policy, findings, commands=command, output=stdout + stderr, changed_files=changed_files, tests_passed=1 if completed.returncode == 0 else 0, tests_failed=0 if completed.returncode == 0 else 1)
            exit_code = completed.returncode
        except subprocess.TimeoutExpired as exc:
            stdout = redact_text(str(exc.stdout or "")[-job.resource_limits.max_output_bytes :])
            stderr = redact_text(str(exc.stderr or "")[-job.resource_limits.max_output_bytes :])
            result = self._result(job, "failed", "codex timed out", policy, ["timeout"], commands=command, output=stdout + stderr)
            exit_code = None
        ended = datetime.now(timezone.utc)
        if receipt_path:
            self._write_receipt(receipt_path, self._receipt(job, policy, result, resolved, workspace, command, stdout, stderr, exit_code, version_output=version_output, help_output=help_output, started=started, ended=ended))
        return result

    @staticmethod
    def _introspect(executable: str, env: dict[str, str], workspace: Path) -> tuple[str, str]:
        def run(args: list[str]) -> str:
            try:
                completed = subprocess.run(args, cwd=workspace, env=env, capture_output=True, text=True, timeout=15, check=False)
            except (OSError, subprocess.TimeoutExpired):
                return ""
            return redact_text((completed.stdout + completed.stderr)[-4096:])
        return run([executable, "--version"]), run([executable, "--help"])

    @staticmethod
    def _receipt(job: JobManifest, policy: AgentPolicyManifest, result: ResultManifest, executable: str | None, workspace: Path, command: Sequence[str], stdout: str, stderr: str, exit_code: int | None, *, version_output: str = "", help_output: str = "", started: datetime | None = None, ended: datetime | None = None) -> BinaryExecutionReceipt:
        now = datetime.now(timezone.utc)
        resolved = Path(executable) if executable else None
        executable_hash = None
        if resolved and resolved.is_file():
            try:
                executable_hash = file_sha256(resolved)
            except OSError:
                executable_hash = None
        return BinaryExecutionReceipt(
            run_id=job.job_id,
            executable=str(resolved or executable or "unresolved"),
            executable_sha256=executable_hash,
            version_command=[str(resolved or executable or "codex"), "--version"],
            version_output_hash=hashlib.sha256(version_output.encode()).hexdigest() if version_output else None,
            help_output_hash=hashlib.sha256(help_output.encode()).hexdigest() if help_output else None,
            command=list(command),
            workspace=str(workspace),
            environment_keys=["PATH", "HOME", "LANG", "LC_ALL"],
            started_at=started or now,
            ended_at=ended or now,
            exit_code=exit_code,
            stdout_hash=hashlib.sha256(stdout.encode()).hexdigest(),
            stderr_hash=hashlib.sha256(stderr.encode()).hexdigest(),
            stdout_excerpt=stdout[-512:],
            stderr_excerpt=stderr[-512:],
            real_binary=executable is not None,
            evidence_stage="E2_local_executed" if result.status == "completed" else "E1_static_validated",
            status="completed" if result.status == "completed" else "blocked" if result.status == "blocked" else "failed",
            missing_evidence=list(result.missing_evidence),
        )

    @staticmethod
    def _write_receipt(path: Path, receipt: BinaryExecutionReceipt) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _result(self, job: JobManifest, status: str, message: str, policy: AgentPolicyManifest, missing: list[str], *, commands: Sequence[str] = (), output: str = "", changed_files: list[str] | None = None, tests_passed: int = 0, tests_failed: int = 0) -> ResultManifest:
        output_hash = artifact_hash({"message": message, "output": output})
        return ResultManifest(
            job_id=job.job_id,
            status=status,
            backend="codex-cli",
            model=None,
            input_hash=artifact_hash(job.input_artifacts),
            output_hash=output_hash,
            prompt_hash=artifact_hash(message),
            config_hash=artifact_hash(policy.model_dump(mode="json")),
            environment_hash=artifact_hash({"workspace": job.scope.repository, "sandbox": job.sandbox_profile.model_dump(mode="json")}),
            changed_files=changed_files or [],
            commands=[" ".join(commands)] if commands else [],
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            evidence_stage="E1_static_validated" if status != "completed" else "E2_local_executed",
            missing_evidence=missing or [message],
            business_success="not_attempted",
        )
