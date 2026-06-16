"""
Job Manager — background execution engine for Agent OS.

Decouples agent execution from UI state. Agents continue working even when
the user navigates away, refreshes the browser, or closes pages.

Job lifecycle: Pending → Running → Completed | Failed | Cancelled

Jobs persist to disk so that on restart we can detect interrupted jobs
and mark them appropriately.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Callable, Coroutine

from app.core.config import settings
from app.schemas import Event, Job
from app.services.time_service import now_label

logger = logging.getLogger("job_manager")


class JobManager:
    """Manages background jobs for all agents."""

    def __init__(self):
        self.jobs: dict[str, Job] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._jobs_path = os.path.join(
            settings.data_dir.replace("/", os.sep), "jobs.json"
        )
        self._load_jobs()

    # ── Job Creation ──────────────────────────────────────────────────────

    def create_job(
        self,
        agent: str,
        workspace_id: str | None = None,
        conversation_id: str | None = None,
    ) -> Job:
        """Create a new job record (does not start execution)."""
        job_id = f"job-{uuid.uuid4().hex[:8]}"
        now = now_label()

        job = Job(
            job_id=job_id,
            agent=agent,
            status="Pending",
            progress=0,
            message="Job created",
            started_at=now,
            updated_at=now,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
        )

        self.jobs[job_id] = job
        self._persist_jobs()

        logger.info("Job created: %s (agent=%s, workspace=%s)", job_id, agent, workspace_id)
        return job

    async def start_job(
        self,
        job_id: str,
        coroutine_factory: Callable[..., Coroutine],
        *args: Any,
        **kwargs: Any,
    ) -> Job:
        """Start executing a job as a background asyncio task.

        coroutine_factory will be called with (job_id, *args, **kwargs).
        """
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        if job.status == "Running":
            return job  # Already running

        # Update status
        job = self._update_job(job_id, status="Running", message="Job started")

        # Publish event
        await self._publish_event(job, "JOB_STARTED", f"Job started: {job.agent}", "info")

        # Create background task
        task = asyncio.create_task(
            self._run_job(job_id, coroutine_factory, *args, **kwargs)
        )
        self._tasks[job_id] = task

        return job

    async def _run_job(
        self,
        job_id: str,
        coroutine_factory: Callable[..., Coroutine],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Wrapper that catches exceptions and updates job status."""
        try:
            await coroutine_factory(job_id, *args, **kwargs)

            # Mark completed (factory may have already done this)
            job = self.get_job(job_id)
            if job and job.status == "Running":
                self._update_job(job_id, status="Completed", progress=100, message="Job completed")
                await self._publish_event(
                    self.get_job(job_id), "JOB_COMPLETED",
                    f"Job completed: {job.agent}", "success"
                )

        except asyncio.CancelledError:
            self._update_job(job_id, status="Cancelled", message="Job cancelled")
            job = self.get_job(job_id)
            if job:
                await self._publish_event(job, "JOB_CANCELLED", f"Job cancelled: {job.agent}", "warning")

        except Exception as e:
            logger.exception("Job %s failed", job_id)
            self._update_job(
                job_id,
                status="Failed",
                message=f"Job failed: {str(e)[:200]}",
                error=str(e),
            )
            job = self.get_job(job_id)
            if job:
                await self._publish_event(
                    job, "JOB_FAILED",
                    f"Job failed: {job.agent} — {str(e)[:100]}", "error"
                )

        finally:
            self._tasks.pop(job_id, None)

    # ── Job Control ───────────────────────────────────────────────────────

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        task = self._tasks.get(job_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    def update_progress(
        self,
        job_id: str,
        progress: int,
        message: str = "",
    ) -> Job | None:
        """Update job progress (called by the executing agent)."""
        return self._update_job(job_id, progress=progress, message=message)

    # ── Job Queries ───────────────────────────────────────────────────────

    def get_job(self, job_id: str) -> Job | None:
        """Get a job by ID."""
        return self.jobs.get(job_id)

    def list_jobs(self) -> list[Job]:
        """List all jobs, most recent first."""
        return sorted(
            self.jobs.values(),
            key=lambda j: j.started_at,
            reverse=True,
        )

    def active_jobs(self) -> list[Job]:
        """List only running/pending jobs."""
        return [j for j in self.jobs.values() if j.status in ("Pending", "Running")]

    def jobs_for_workspace(self, workspace_id: str) -> list[Job]:
        """List all jobs for a workspace."""
        return [j for j in self.jobs.values() if j.workspace_id == workspace_id]

    # ── Crash Recovery ────────────────────────────────────────────────────

    def recover_jobs(self) -> int:
        """On startup, mark any "Running" jobs as "Failed" (interrupted).

        We don't attempt re-execution — it's too risky without knowing
        where the job left off.

        Returns the number of jobs recovered.
        """
        recovered = 0
        for job_id, job in self.jobs.items():
            if job.status in ("Running", "Pending"):
                self._update_job(
                    job_id,
                    status="Failed",
                    message="Interrupted: Agent OS restarted during execution",
                    error="Process interrupted by restart",
                )
                recovered += 1
                logger.warning("Recovered interrupted job: %s", job_id)

        if recovered:
            self._persist_jobs()
            logger.info("Recovered %d interrupted jobs", recovered)

        return recovered

    # ── Internal ──────────────────────────────────────────────────────────

    def _update_job(self, job_id: str, **changes: Any) -> Job | None:
        """Update a job's fields and persist."""
        job = self.jobs.get(job_id)
        if not job:
            return None

        changes["updated_at"] = now_label()

        if changes.get("status") in ("Completed", "Failed", "Cancelled"):
            changes.setdefault("completed_at", now_label())

        updated = job.model_copy(update={k: v for k, v in changes.items() if v is not None})
        self.jobs[job_id] = updated
        self._persist_jobs()

        return updated

    async def _publish_event(
        self, job: Job, event_type: str, message: str, severity: str
    ) -> None:
        """Publish a job event to the event bus."""
        from app.core.event_bus import event_bus

        await event_bus.publish(Event(
            type=event_type,
            source=f"Job Manager ({job.agent})",
            message=message,
            severity=severity,
            payload={
                "job_id": job.job_id,
                "agent": job.agent,
                "status": job.status,
                "progress": job.progress,
                "workspace_id": job.workspace_id,
            },
        ))

    # ── Persistence ───────────────────────────────────────────────────────

    def _persist_jobs(self) -> None:
        """Save all jobs to disk."""
        try:
            os.makedirs(os.path.dirname(self._jobs_path), exist_ok=True)
            data = {jid: job.model_dump() for jid, job in self.jobs.items()}
            with open(self._jobs_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except OSError as e:
            logger.warning("Failed to persist jobs: %s", e)

    def _load_jobs(self) -> None:
        """Load jobs from disk."""
        if not os.path.exists(self._jobs_path):
            return
        try:
            with open(self._jobs_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for jid, job_data in data.items():
                self.jobs[jid] = Job(**job_data)
            logger.info("Loaded %d jobs from disk", len(self.jobs))
        except Exception as e:
            logger.warning("Failed to load jobs: %s", e)


# ── Singleton ─────────────────────────────────────────────────────────────

job_manager = JobManager()
