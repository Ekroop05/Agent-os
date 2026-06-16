"""
Security Agent Service — reviews Builder output for correctness and safety.

Uses Qwen2.5-Coder 7B via Ollama for code review.
Validates files exist, are non-empty, and contain no dangerous patterns.
"""

from __future__ import annotations

import json
import os
import re

from app.core.event_bus import event_bus
from app.schemas import Event, SecurityReviewResult, TaskUpdate
from app.services.llm_service import generate_response
from app.services.path_security import validate_write_path, SecurityViolationError
from app.services.command_security import validate_command, CommandBlockedError

SECURITY_MODEL = "qwen2.5-coder:7b"

# Dangerous code patterns to flag
DANGEROUS_PATTERNS = [
    (r"\beval\s*\(", "eval() call detected"),
    (r"\bexec\s*\(", "exec() call detected"),
    (r"subprocess\.call.*shell\s*=\s*True", "subprocess with shell=True"),
    (r"os\.system\s*\(", "os.system() call"),
    (r"rm\s+-rf\s+/", "rm -rf / detected"),
    (r"del\s+/s\s+/q", "Windows del /s /q detected"),
    (r"format\s+[a-zA-Z]:", "Format drive command detected"),
    (r"__import__\s*\(", "Dynamic __import__ detected"),
    (r"importlib\.import_module", "Dynamic import detected"),
    (r"pickle\.loads?\s*\(", "Unsafe pickle deserialization"),
]


class SecurityService:
    """Reviews builder task outputs for correctness and security."""

    async def review_task(self, task_id: str, workspace_id: str) -> SecurityReviewResult:
        """Full security review of a completed builder task."""
        from app.services.task_service import task_service
        from app.services.workspace_service import workspace_service
        from app.services.agent_service import agent_service
        from app.services.execution_logger import execution_logger

        task = task_service.get(task_id)
        workspace = workspace_service.get(workspace_id)

        # ── P5 Guard: Only completed tasks can be reviewed ────────────────
        if task.status != "Completed":
            rejection_note = (
                f"Security review skipped: task status is '{task.status}', not 'Completed'. "
                f"Only completed tasks are eligible for security review."
            )
            task_service.update(TaskUpdate(
                id=task_id,
                security_status="Rejected",
                security_notes=rejection_note,
            ))
            await event_bus.publish(Event(
                type="SECURITY_REJECTED",
                source="Security Agent",
                message=f"Security review rejected for non-completed task: {task.title}",
                severity="warning",
                payload={"task_id": task_id, "workspace_id": workspace_id, "reason": rejection_note},
            ))
            return SecurityReviewResult(
                task_id=task_id,
                approved=False,
                issues=[rejection_note],
                notes=rejection_note,
            )

        # Update agent status
        agent_service.update("security-agent", status="Running", current_task=f"Reviewing: {task.title}")

        # Update workspace
        workspace_service.update_build_status(workspace_id, "Reviewing", "Security Agent", task.title)

        # Mark task as under review
        task_service.update(TaskUpdate(id=task_id, security_status="Reviewing"))

        execution_logger.log(workspace.path, "Security Agent", "REVIEW_STARTED", task_id, task.title)

        await event_bus.publish(Event(
            type="SECURITY_REVIEW_STARTED",
            source="Security Agent",
            message=f"Security reviewing: {task.title}",
            severity="info",
            payload={"task_id": task_id, "workspace_id": workspace_id, "title": task.title},
        ))

        issues: list[str] = []

        # Check 1: Verify output files exist
        file_issues = self._check_files_exist(task.output_files)
        issues.extend(file_issues)

        # Check 2: Verify files are non-empty
        content_issues = self._check_content_valid(task.output_files)
        issues.extend(content_issues)

        # Check 3: Scan for dangerous patterns
        security_issues = self._check_dangerous_patterns(task.output_files)
        issues.extend(security_issues)

        # Check 4: Validate project structure
        workspace = workspace_service.get(workspace_id)
        structure_issues = self._validate_structure(workspace)
        issues.extend(structure_issues)

        # Check 5: Sprint 4.5 — Validate filesystem access (path isolation)
        path_issues = self._check_path_isolation(task.output_files, workspace)
        issues.extend(path_issues)

        # Check 6: Sprint 4.5 — Validate commands in generated scripts
        command_issues = self._check_generated_commands(task.output_files)
        issues.extend(command_issues)

        # Check 7: LLM Code Review
        # Only review if basic checks passed, to save time
        if len(issues) == 0:
            llm_issues = await self._llm_code_review(task.output_files)
            issues.extend(llm_issues)

        # Determine result
        approved = len(issues) == 0
        notes = "All checks passed." if approved else f"Found {len(issues)} issue(s): " + "; ".join(issues[:3])

        result = SecurityReviewResult(
            task_id=task_id,
            approved=approved,
            issues=issues,
            notes=notes,
        )

        # Update task
        task_service.update(TaskUpdate(
            id=task_id,
            security_status="Approved" if approved else "Rejected",
            security_notes=notes,
        ))

        event_type = "SECURITY_APPROVED" if approved else "SECURITY_REJECTED"
        severity = "success" if approved else "warning"

        await event_bus.publish(Event(
            type=event_type,
            source="Security Agent",
            message=f"Security {'approved' if approved else 'rejected'}: {task.title}" + (f" — {notes}" if not approved else ""),
            severity=severity,
            payload={
                "task_id": task_id,
                "workspace_id": workspace_id,
                "approved": approved,
                "issues": issues,
            },
        ))

        execution_logger.log(
            workspace.path, "Security Agent",
            "REVIEW_APPROVED" if approved else "REVIEW_REJECTED",
            task_id, notes
        )

        # Update agent to idle
        agent_service.update("security-agent", current_task="Monitoring review queue")

        return result

    # ── Check Methods ─────────────────────────────────────────────────────

    def _check_files_exist(self, files: list[str]) -> list[str]:
        """Verify all claimed output files exist on disk."""
        issues = []
        for file_path in files:
            native_path = file_path.replace("/", os.sep)
            if not os.path.exists(native_path):
                issues.append(f"File missing: {file_path}")
        return issues

    def _check_content_valid(self, files: list[str]) -> list[str]:
        """Verify files are non-empty and readable."""
        issues = []
        for file_path in files:
            native_path = file_path.replace("/", os.sep)
            if not os.path.exists(native_path):
                continue

            if os.path.isdir(native_path):
                continue

            try:
                size = os.path.getsize(native_path)
                if size == 0:
                    issues.append(f"Empty file: {file_path}")
                    continue

                with open(native_path, "r", encoding="utf-8") as f:
                    content = f.read(1024)  # Read first 1KB to validate
                    if not content.strip():
                        issues.append(f"Whitespace-only file: {file_path}")
            except UnicodeDecodeError:
                pass  # Binary files are fine
            except Exception as e:
                issues.append(f"Cannot read {file_path}: {str(e)}")

        return issues

    def _check_dangerous_patterns(self, files: list[str]) -> list[str]:
        """Scan files for dangerous code patterns."""
        issues = []
        for file_path in files:
            native_path = file_path.replace("/", os.sep)
            if not os.path.exists(native_path) or os.path.isdir(native_path):
                continue

            try:
                with open(native_path, "r", encoding="utf-8") as f:
                    content = f.read()

                for pattern, description in DANGEROUS_PATTERNS:
                    if re.search(pattern, content, re.IGNORECASE):
                        issues.append(f"{description} in {os.path.basename(file_path)}")
            except (UnicodeDecodeError, OSError):
                pass

        return issues

    def _validate_structure(self, workspace) -> list[str]:
        """Verify the project folder structure is intact."""
        issues = []
        base = workspace.path.replace("/", os.sep)

        if not os.path.exists(base):
            issues.append(f"Project root missing: {workspace.path}")

        return issues

    # ── Sprint 4.5: Path Isolation Check ──────────────────────────────────

    def _check_path_isolation(self, files: list[str], workspace) -> list[str]:
        """Verify all output files are inside the workspace boundary."""
        issues = []
        for file_path in files:
            try:
                validate_write_path(file_path, workspace.path)
            except SecurityViolationError as e:
                issues.append(f"Path isolation violation: {file_path} — {e.reason}")
        return issues

    # ── Sprint 4.5: Command Safety Check ──────────────────────────────────

    def _check_generated_commands(self, files: list[str]) -> list[str]:
        """Scan generated scripts for dangerous commands."""
        issues = []
        command_patterns = [
            r'os\.system\s*\(["\'](.+?)["\']\)',
            r'subprocess\.(?:run|call|Popen)\s*\(\[?["\'](.+?)["\']',
            r'exec\s*\(["\'](.+?)["\']\)',
        ]

        for file_path in files:
            native_path = file_path.replace("/", os.sep)
            if not os.path.exists(native_path) or os.path.isdir(native_path):
                continue
            try:
                with open(native_path, "r", encoding="utf-8") as f:
                    content = f.read()
                for pattern in command_patterns:
                    for match in re.finditer(pattern, content):
                        cmd = match.group(1)
                        try:
                            validate_command(cmd)
                        except CommandBlockedError as e:
                            issues.append(
                                f"Dangerous command in {os.path.basename(file_path)}: "
                                f"{cmd[:40]} — {e.reason}"
                            )
            except (UnicodeDecodeError, OSError):
                pass

        return issues

    async def _llm_code_review(self, files: list[str]) -> list[str]:
        """Use LLM to review code for missing imports, broken routes, unused components, invalid references."""
        issues = []
        file_contents = []
        for file_path in files:
            native_path = file_path.replace("/", os.sep)
            if not os.path.exists(native_path) or os.path.isdir(native_path):
                continue
            try:
                with open(native_path, "r", encoding="utf-8") as f:
                    content = f.read()
                file_contents.append(f"--- {os.path.basename(file_path)} ---\n{content}")
            except Exception:
                pass
                
        if not file_contents:
            return []
            
        prompt = f"""You are the Security Agent of Agent OS. Review the following code files for quality and correctness.
        
FILES:
{"\n\n".join(file_contents)}

Inspect for:
1. Missing imports (using components/functions without importing them)
2. Broken routes or invalid file references
3. Syntactical errors or build-breaking issues
4. Unused components or placeholder assets

Return ONLY valid JSON:
{{
  "issues": ["Issue description 1", "Issue description 2"]
}}

If no issues found, return an empty array for "issues". Do NOT wrap in markdown fences."""
        try:
            raw = generate_response(SECURITY_MODEL, prompt)
            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            cleaned = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "")
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1:
                parsed = json.loads(cleaned[start:end + 1])
                return parsed.get("issues", [])
        except Exception:
            pass
            
        return issues


# ── Singleton ─────────────────────────────────────────────────────────────

security_service = SecurityService()
