"""
Build Orchestrator — coordinates the full Builder → Security pipeline.

After architecture approval, this runs as a background asyncio task:
1. Create project folder
2. Create base structure
3. Create README.md
4. Create project manifest
5. Execute coding tasks sequentially
Each step: Builder executes → Security reviews → proceed or retry.

Task State Machine:
  Pending → Assigned → Running → (Completed | Failed)
  Security: Pending → Reviewing → (Approved | Rejected)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from app.core.event_bus import event_bus
from app.schemas import BuildProgress, Event, TaskCreate, TaskUpdate
from app.services.time_service import now_label

logger = logging.getLogger("build_orchestrator")

MAX_RETRIES = 2


class BuildOrchestrator:
    """Manages end-to-end build pipelines."""

    def __init__(self):
        self.active_builds: dict[str, asyncio.Task] = {}
        self.build_states: dict[str, dict] = {}

    async def start_pipeline(self, workspace_id: str, architecture: dict | None = None) -> None:
        """Entry point: start building a workspace. Runs as background task."""
        if workspace_id in self.active_builds:
            return  # Already building

        self.build_states[workspace_id] = {
            "status": "Building",
            "started_at": datetime.now(),
            "last_activity": now_label(),
            "architecture": architecture,  # Store for builder access
        }

        task = asyncio.create_task(self._run_pipeline(workspace_id, architecture))
        self.active_builds[workspace_id] = task

    def get_architecture(self, workspace_id: str) -> dict | None:
        """Retrieve stored architecture for a workspace build."""
        state = self.build_states.get(workspace_id, {})
        return state.get("architecture")

    async def _run_pipeline(self, workspace_id: str, architecture: dict | None) -> None:
        """Run the full build pipeline sequentially."""
        from app.services.builder_service import builder_service
        from app.services.security_service import security_service
        from app.services.task_service import task_service
        from app.services.workspace_service import workspace_service
        from app.services.agent_service import agent_service
        from app.services.execution_logger import execution_logger

        try:
            # Update agents
            agent_service.update("builder-agent", status="Running", current_task="Starting build pipeline")
            agent_service.update("security-agent", status="Running", current_task="Monitoring review queue")

            await event_bus.publish(Event(
                type="BUILD_STARTED",
                source="Build Orchestrator",
                message=f"Build pipeline started for workspace {workspace_id}",
                severity="success",
                payload={"workspace_id": workspace_id},
            ))

            workspace = workspace_service.get(workspace_id)
            workspace_service.update_build_status(workspace_id, "Building", "Builder Agent", "Starting...")

            # Log pipeline start
            execution_logger.log(workspace.path, "Build Orchestrator", "PIPELINE_STARTED", details=f"Building {workspace.name}")

            # ── Create foundation tasks if they don't exist ───────────────
            existing_tasks = task_service.list_by_workspace(workspace_id)
            existing_titles = {t.title.lower() for t in existing_tasks}

            foundation_tasks = [
                ("Create Project Folder", "Create the project root directory on disk.", "Critical", "Builder Agent"),
                ("Create Base Structure", "Create frontend/, backend/, docs/, .agentos/ directories.", "Critical", "Builder Agent"),
                ("Create README.md", "Generate project README with name, description, tech stack, and metadata.", "High", "Builder Agent"),
                ("Create Project Manifest", "Generate .agentos/project.json with full project metadata.", "High", "Builder Agent"),
            ]

            for title, desc, priority, agent in foundation_tasks:
                if title.lower() not in existing_titles:
                    task_service.create(TaskCreate(
                        title=title,
                        description=desc,
                        assigned_agent=agent,
                        priority=priority,
                        workspace_id=workspace_id,
                    ))

            # Ensure all existing tasks belong to this workspace
            for task in existing_tasks:
                if not task.workspace_id:
                    task_service.update(TaskUpdate(id=task.id, workspace_id=workspace_id))

            # Recalculate progress
            workspace_service.recalculate_progress(workspace_id)

            # ── Process tasks one by one ──────────────────────────────────
            while True:
                next_task = task_service.next_pending_task(workspace_id)
                if not next_task:
                    break  # All tasks done

                # Determine which agent should handle this task
                is_builder_task = next_task.assigned_agent in ("Builder Agent", "Head Agent") or \
                    self._is_build_task(next_task.title)
                is_security_task = next_task.assigned_agent == "Security Agent"

                if is_builder_task:
                    # Builder executes
                    agent_service.update("builder-agent", status="Running", current_task=next_task.title)
                    workspace_service.update_build_status(workspace_id, "Building", "Builder Agent", next_task.title)

                    build_result = await builder_service.execute_task(
                        next_task.id, workspace_id, architecture=architecture
                    )

                    if build_result["status"] == "error":
                        logger.error(f"Builder failed on task {next_task.id}: {build_result.get('error')}")
                        # Explicitly mark task as failed
                        task_service.update(TaskUpdate(
                            id=next_task.id,
                            status="Failed",
                            security_notes=f"Builder error: {build_result.get('error', 'Unknown')}",
                        ))

                        execution_logger.log(
                            workspace.path, "Build Orchestrator", "TASK_FAILED",
                            next_task.id, build_result.get("error", "Unknown")
                        )

                        await event_bus.publish(Event(
                            type="BUILD_TASK_FAILED",
                            source="Build Orchestrator",
                            message=f"Task failed: {next_task.title}",
                            severity="error",
                            payload={"task_id": next_task.id, "workspace_id": workspace_id},
                        ))

                        await asyncio.sleep(0.5)
                        # Recalculate and continue to next task
                        workspace_service.recalculate_progress(workspace_id)
                        continue

                    # Security reviews builder output
                    agent_service.update("security-agent", status="Running", current_task=f"Reviewing: {next_task.title}")
                    workspace_service.update_build_status(workspace_id, "Reviewing", "Security Agent", next_task.title)

                    review_result = await security_service.review_task(next_task.id, workspace_id)

                    if not review_result.approved:
                        # Retry logic
                        retry_count = self.build_states.get(workspace_id, {}).get(f"retry_{next_task.id}", 0)
                        if retry_count < MAX_RETRIES:
                            self.build_states[workspace_id][f"retry_{next_task.id}"] = retry_count + 1
                            # Reset task to Pending for retry
                            task_service.update(TaskUpdate(
                                id=next_task.id,
                                status="Pending",
                                security_status="Pending",
                                security_notes=f"Retry {retry_count + 1}/{MAX_RETRIES}: {review_result.notes}",
                            ))

                            await event_bus.publish(Event(
                                type="BUILD_TASK_RETRY",
                                source="Build Orchestrator",
                                message=f"Retrying task: {next_task.title} (attempt {retry_count + 2})",
                                severity="warning",
                                payload={"task_id": next_task.id, "workspace_id": workspace_id},
                            ))
                            continue
                        else:
                            # Max retries reached — log and move on
                            execution_logger.log(
                                workspace.path, "Build Orchestrator", "TASK_MAX_RETRIES",
                                next_task.id, f"Skipped after {MAX_RETRIES} retries"
                            )
                            await event_bus.publish(Event(
                                type="BUILD_TASK_SKIPPED",
                                source="Build Orchestrator",
                                message=f"Skipping task after {MAX_RETRIES} retries: {next_task.title}",
                                severity="warning",
                                payload={"task_id": next_task.id, "workspace_id": workspace_id},
                            ))

                elif is_security_task:
                    # Security-only tasks (review, testing, etc.)
                    agent_service.update("security-agent", status="Running", current_task=next_task.title)
                    workspace_service.update_build_status(workspace_id, "Reviewing", "Security Agent", next_task.title)

                    # Mark as running
                    task_service.update(TaskUpdate(id=next_task.id, status="Running"))

                    review_result = await security_service.review_task(next_task.id, workspace_id)

                    task_service.update(TaskUpdate(
                        id=next_task.id,
                        status="Completed",
                    ))

                    execution_logger.log(
                        workspace.path, "Security Agent", "TASK_COMPLETED",
                        next_task.id, next_task.title
                    )

                else:
                    # Head Agent planning tasks — mark as completed (planning is done)
                    task_service.update(TaskUpdate(
                        id=next_task.id,
                        status="Completed",
                    ))

                    await event_bus.publish(Event(
                        type="BUILD_TASK_COMPLETED",
                        source="Head Agent",
                        message=f"Planning task completed: {next_task.title}",
                        severity="success",
                        payload={"task_id": next_task.id, "workspace_id": workspace_id, "title": next_task.title},
                    ))

                # Update progress after each task
                workspace = workspace_service.recalculate_progress(workspace_id)
                self.build_states[workspace_id]["last_activity"] = now_label()

                await event_bus.publish(Event(
                    type="BUILD_PROGRESS_UPDATED",
                    source="Build Orchestrator",
                    message=f"Build progress: {workspace.progress}%",
                    severity="info",
                    payload={
                        "workspace_id": workspace_id,
                        "progress": workspace.progress,
                        "eta_minutes": workspace.estimated_completion_minutes,
                    },
                ))

                # Small delay between tasks for UI readability
                await asyncio.sleep(0.5)

            # ── Pipeline complete ─────────────────────────────────────────
            workspace_service.update_build_status(workspace_id, "Completed")
            workspace = workspace_service.recalculate_progress(workspace_id)

            agent_service.update("builder-agent", status="Idle", current_task="Build complete")
            agent_service.update("security-agent", status="Idle", current_task="Build complete")

            execution_logger.log(workspace.path, "Build Orchestrator", "PIPELINE_COMPLETED", details=f"Progress: {workspace.progress}%")

            await event_bus.publish(Event(
                type="BUILD_COMPLETED",
                source="Build Orchestrator",
                message=f"Build completed for workspace {workspace_id}",
                severity="success",
                payload={"workspace_id": workspace_id},
            ))

            self.build_states[workspace_id]["status"] = "Completed"

        except asyncio.CancelledError:
            workspace_service.update_build_status(workspace_id, "Failed")
            agent_service.update("builder-agent", status="Paused", current_task="Build cancelled")
            agent_service.update("security-agent", status="Idle", current_task="Monitoring review queue")

            await event_bus.publish(Event(
                type="BUILD_FAILED",
                source="Build Orchestrator",
                message=f"Build cancelled for workspace {workspace_id}",
                severity="error",
                payload={"workspace_id": workspace_id},
            ))

        except Exception as e:
            logger.exception(f"Build pipeline failed for {workspace_id}")
            workspace_service.update_build_status(workspace_id, "Failed")
            agent_service.update("builder-agent", status="Paused", current_task=f"Error: {str(e)[:80]}")
            agent_service.update("security-agent", status="Idle", current_task="Monitoring review queue")

            try:
                workspace = workspace_service.get(workspace_id)
                execution_logger.log(workspace.path, "Build Orchestrator", "PIPELINE_FAILED", details=str(e))
            except Exception:
                pass

            await event_bus.publish(Event(
                type="BUILD_FAILED",
                source="Build Orchestrator",
                message=f"Build failed: {str(e)[:120]}",
                severity="error",
                payload={"workspace_id": workspace_id, "error": str(e)},
            ))

        finally:
            self.active_builds.pop(workspace_id, None)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _is_build_task(self, title: str) -> bool:
        """Check if a task title indicates a build/implementation task."""
        build_keywords = ["build", "create", "implement", "frontend", "backend",
                          "component", "feature", "setup", "scaffold", "shell",
                          "readme", "manifest", "folder", "structure"]
        title_lower = title.lower()
        return any(kw in title_lower for kw in build_keywords)

    # ── Query Methods ─────────────────────────────────────────────────────

    def get_build_progress(self, workspace_id: str) -> BuildProgress:
        """Get current build progress for a workspace."""
        from app.services.task_service import task_service
        from app.services.workspace_service import workspace_service

        try:
            workspace = workspace_service.get(workspace_id)
        except Exception:
            return BuildProgress(workspace_id=workspace_id)

        total = task_service.count_total(workspace_id)
        completed = task_service.count_completed(workspace_id)
        progress = int((completed / total) * 100) if total > 0 else 0

        state = self.build_states.get(workspace_id, {})

        return BuildProgress(
            workspace_id=workspace_id,
            total_tasks=total,
            completed_tasks=completed,
            progress_percent=progress,
            estimated_minutes_remaining=workspace.estimated_completion_minutes,
            current_agent=workspace.current_agent,
            current_task_title=workspace.current_task_title,
            build_status=workspace.build_status,
            last_activity=state.get("last_activity"),
        )

    def cancel_build(self, workspace_id: str) -> bool:
        """Cancel an active build."""
        task = self.active_builds.get(workspace_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    def is_building(self, workspace_id: str) -> bool:
        task = self.active_builds.get(workspace_id)
        return task is not None and not task.done()


# ── Singleton ─────────────────────────────────────────────────────────────

build_orchestrator = BuildOrchestrator()
