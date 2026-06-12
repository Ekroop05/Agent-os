"""
Builder Agent Service — executes tasks by generating files and code.

Uses Qwen2.5-Coder 7B via Ollama.
Processes tasks sequentially for a workspace.
Communicates status through the event bus.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime

from app.core.event_bus import event_bus
from app.schemas import Event, TaskUpdate
from app.services.llm_service import generate_response
from app.services.time_service import now_label

BUILDER_MODEL = "qwen2.5-coder:7b"


class BuilderService:
    """Executes individual build tasks."""

    # ── Public API ────────────────────────────────────────────────────────

    async def execute_task(self, task_id: str, workspace_id: str) -> dict:
        """Execute a single task: update status, generate output, create files."""
        from app.services.task_service import task_service
        from app.services.workspace_service import workspace_service
        from app.services.agent_service import agent_service

        task = task_service.get(task_id)
        workspace = workspace_service.get(workspace_id)

        # Update agent status
        agent_service.update("builder-agent", status="Running", current_task=task.title)

        # Mark task as Running
        task = task_service.update(TaskUpdate(
            id=task_id,
            status="Running",
            assigned_agent="Builder Agent",
        ))

        await event_bus.publish(Event(
            type="BUILD_TASK_STARTED",
            source="Builder Agent",
            message=f"Builder started: {task.title}",
            severity="info",
            payload={"task_id": task_id, "workspace_id": workspace_id, "title": task.title},
        ))

        # Update workspace current status
        workspace_service.update_build_status(workspace_id, "Building", "Builder Agent", task.title)

        try:
            # Route to specialized handlers or generic LLM handler
            title_lower = task.title.lower()
            output_files = []

            if "create project folder" in title_lower or "project folder" in title_lower:
                output_files = await self._create_project_folder(workspace)
            elif "base structure" in title_lower or "create base" in title_lower or "folder structure" in title_lower:
                output_files = await self._create_base_structure(workspace)
            elif "readme" in title_lower:
                output_files = await self._create_readme(workspace)
            elif "manifest" in title_lower or "project.json" in title_lower:
                output_files = await self._create_manifest(workspace)
            else:
                output_files = await self._generate_for_task(task, workspace)

            # Mark task as completed
            task = task_service.update(TaskUpdate(
                id=task_id,
                status="Completed",
                output_files=output_files,
            ))

            await event_bus.publish(Event(
                type="BUILD_TASK_COMPLETED",
                source="Builder Agent",
                message=f"Builder completed: {task.title} ({len(output_files)} files)",
                severity="success",
                payload={
                    "task_id": task_id,
                    "workspace_id": workspace_id,
                    "title": task.title,
                    "output_files": output_files,
                },
            ))

            # Update agent to idle
            agent_service.update("builder-agent", current_task="Waiting for next task")

            return {"status": "success", "task_id": task_id, "output_files": output_files}

        except Exception as e:
            # Mark task as failed
            task_service.update(TaskUpdate(
                id=task_id,
                status="Failed",
                security_notes=f"Builder error: {str(e)}",
            ))
            agent_service.update("builder-agent", status="Paused", current_task=f"Error: {str(e)[:80]}")

            await event_bus.publish(Event(
                type="BUILD_TASK_FAILED",
                source="Builder Agent",
                message=f"Builder failed on: {task.title} — {str(e)[:120]}",
                severity="error",
                payload={"task_id": task_id, "workspace_id": workspace_id, "error": str(e)},
            ))

            return {"status": "error", "task_id": task_id, "error": str(e)}

    # ── Specialized Handlers ──────────────────────────────────────────────

    async def _create_project_folder(self, workspace) -> list[str]:
        """Task 1: Create the project root folder on disk."""
        project_path = workspace.path.replace("/", os.sep)
        os.makedirs(project_path, exist_ok=True)

        await event_bus.publish(Event(
            type="FILE_CREATED",
            source="Builder Agent",
            message=f"Created project folder: {workspace.path}",
            severity="success",
            payload={"path": workspace.path},
        ))

        return [workspace.path]

    async def _create_base_structure(self, workspace) -> list[str]:
        """Task 2: Create frontend/, backend/, docs/, .agentos/ directories."""
        base = workspace.path.replace("/", os.sep)
        folders = ["frontend", "backend", "docs", ".agentos"]
        created = []

        for folder in folders:
            folder_path = os.path.join(base, folder)
            os.makedirs(folder_path, exist_ok=True)
            created.append(f"{workspace.path}/{folder}")

            await event_bus.publish(Event(
                type="FILE_CREATED",
                source="Builder Agent",
                message=f"Created directory: {folder}/",
                severity="info",
                payload={"path": f"{workspace.path}/{folder}"},
            ))

        return created

    async def _create_readme(self, workspace) -> list[str]:
        """Task 3: Generate README.md with project info."""
        from app.services.task_service import task_service

        architecture = self._get_architecture_from_workspace(workspace)
        task_count = task_service.count_total(workspace.id)

        tech_stack = architecture.get("tech_stack", []) if architecture else []
        description = architecture.get("architecture", workspace.description) if architecture else workspace.description
        components = architecture.get("major_components", []) if architecture else []

        content = f"""# {workspace.name}

> Generated by Agent OS on {now_label()}

## Description

{description}

## Tech Stack

{chr(10).join(f'- {t}' for t in tech_stack) if tech_stack else '- To be determined'}

## Major Components

{chr(10).join(f'- {c}' for c in components) if components else '- To be determined'}

## Project Info

| Field | Value |
|-------|-------|
| Generated | {now_label()} |
| Tasks | {task_count} |
| Status | Building |
| Workspace ID | {workspace.id} |

## Getting Started

This project was generated by Agent OS. Check the `.agentos/project.json` manifest for full project metadata.

---

*Built with Agent OS — Local Multi-Agent Runtime*
"""
        readme_path = os.path.join(workspace.path.replace("/", os.sep), "README.md")
        os.makedirs(os.path.dirname(readme_path), exist_ok=True)
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(content)

        await event_bus.publish(Event(
            type="FILE_CREATED",
            source="Builder Agent",
            message="Created README.md",
            severity="success",
            payload={"path": f"{workspace.path}/README.md"},
        ))

        return [f"{workspace.path}/README.md"]

    async def _create_manifest(self, workspace) -> list[str]:
        """Task 4: Generate .agentos/project.json manifest."""
        from app.services.task_service import task_service

        architecture = self._get_architecture_from_workspace(workspace)
        tasks = task_service.list_by_workspace(workspace.id)

        manifest = {
            "workspace_id": workspace.id,
            "project_name": workspace.name,
            "path": workspace.path,
            "created_at": workspace.created_at,
            "architecture": architecture,
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status,
                    "priority": t.priority,
                }
                for t in tasks
            ],
            "status": "Building",
            "agent_os_version": "0.5.0",
        }

        manifest_path = os.path.join(workspace.path.replace("/", os.sep), ".agentos", "project.json")
        os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, default=str)

        await event_bus.publish(Event(
            type="FILE_CREATED",
            source="Builder Agent",
            message="Created .agentos/project.json",
            severity="success",
            payload={"path": f"{workspace.path}/.agentos/project.json"},
        ))

        return [f"{workspace.path}/.agentos/project.json"]

    # ── Generic LLM-Driven Task Execution ─────────────────────────────────

    async def _generate_for_task(self, task, workspace) -> list[str]:
        """Use LLM to generate files for a coding task."""
        architecture = self._get_architecture_from_workspace(workspace)
        arch_summary = json.dumps(architecture, default=str) if architecture else "No architecture available"

        prompt = f"""You are the Builder Agent of Agent OS. Generate the code files needed for this task.

PROJECT: {workspace.name}
PROJECT PATH: {workspace.path}
ARCHITECTURE: {arch_summary}

TASK: {task.title}
DESCRIPTION: {task.description}

Return ONLY valid JSON with this structure:
{{
  "files": [
    {{
      "path": "relative/path/to/file.ext",
      "content": "file content here"
    }}
  ]
}}

Rules:
- Use paths relative to the project root
- Generate complete, working code
- Follow the architecture and tech stack
- Do NOT use placeholder or lorem ipsum content
- Do NOT wrap JSON in markdown code fences
- Keep files focused and modular"""

        try:
            raw = generate_response(BUILDER_MODEL, prompt)
            # Strip think tags
            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            parsed = json.loads(self._extract_json(raw))
            files = parsed.get("files", [])
        except Exception:
            # Fallback: create a placeholder file
            files = [{
                "path": f"docs/{task.title.lower().replace(' ', '_')}.md",
                "content": f"# {task.title}\n\n{task.description}\n\nStatus: Generated by Builder Agent\nDate: {now_label()}\n",
            }]

        created = []
        for file_info in files:
            rel_path = file_info.get("path", "")
            content = file_info.get("content", "")
            if not rel_path:
                continue

            abs_path = os.path.join(workspace.path.replace("/", os.sep), rel_path.replace("/", os.sep))
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)

            normalized = f"{workspace.path}/{rel_path.replace(os.sep, '/')}"
            created.append(normalized)

            await event_bus.publish(Event(
                type="FILE_CREATED",
                source="Builder Agent",
                message=f"Created: {rel_path}",
                severity="info",
                payload={"path": normalized},
            ))

        return created

    # ── Helpers ───────────────────────────────────────────────────────────

    def _get_architecture_from_workspace(self, workspace) -> dict | None:
        """Retrieve architecture from the project state manager if available."""
        from app.state.project_state import project_state_manager
        for state in project_state_manager._store.values():
            if state.get("project_name") and state.get("architecture"):
                project_name = state["project_name"]
                # Match by workspace name
                if project_name.lower().replace(" ", "-") in workspace.id.lower():
                    return state["architecture"]
        return None

    def _extract_json(self, raw: str) -> str:
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "")
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("No JSON found")
        return cleaned[start:end + 1]


# ── Singleton ─────────────────────────────────────────────────────────────

builder_service = BuilderService()
