from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.core.event_bus import event_bus
from app.core.websocket_manager import websocket_manager
from app.schemas import (
    Agent,
    AgentAction,
    ArchitectApprovalRequest,
    ArchitectApprovalResponse,
    ArchitectChatRequest,
    ArchitectChatResponse,
    BuildProgress,
    BuildReport,
    BuildStartRequest,
    Event,
    Job,
    RuntimeEntry,
    RuntimeStopRequest,
    SandboxSettings,
    SandboxState,
    SystemStatus,
    Task,
    TaskCreate,
    TaskUpdate,
    Workspace,
    WorkspaceArchiveEntry,
    WorkspaceCreate,
    MCPExecuteRequest,
)
from pydantic import BaseModel

class LogTraceRequest(BaseModel):
    message: str

from app.services.activity_service import activity_service
from app.services.agent_service import agent_service
from app.services.architect_service import architect_service, project_state_manager
from app.services.build_orchestrator import build_orchestrator
from app.services.job_manager import job_manager
from app.services.runtime_manager import runtime_manager
from app.services.sandbox_service import sandbox_service
from app.services.spec_engine import spec_engine
from app.services.system_service import system_service
from app.services.task_service import task_service
from app.services.workspace_service import workspace_service

# Import MCP modules to register tools
from app.mcp.registry import mcp_registry
import app.mcp.project_mcp
import app.mcp.task_mcp
import app.mcp.file_mcp
import app.mcp.terminal_mcp
import app.mcp.git_mcp
from app.services.execution_logger import execution_logger

import logging

logger = logging.getLogger("agent_os")

app = FastAPI(title="Agent OS API", version="0.7.0")


# ── Task Routing ──────────────────────────────────────────────────────────

_HEAD_KEYWORDS = ["scope", "define", "plan", "design", "architecture", "document", "research"]
_BUILDER_KEYWORDS = ["build", "implement", "create", "frontend", "backend", "feature",
                     "component", "page", "api", "database", "setup", "shell", "scaffold",
                     "model", "schema", "endpoint", "config", "variable", "theme",
                     "context", "route", "routing", "responsive", "layout", "style",
                     "navbar", "footer", "hero", "card", "form", "modal", "service",
                     "crud", "migration", "seed", "middleware", "handler", "controller",
                     "client", "axios", "fetch", "state", "loading", "error",
                     "animation", "transition", "seo", "meta", "optimization",
                     "menu", "section", "gallery", "catalog", "dashboard", "chart",
                     "filter", "search", "toggle", "wrapper", "provider"]
_SECURITY_KEYWORDS = ["test", "review", "security", "integration", "deploy", "polish",
                      "validate", "audit", "performance", "qa"]


def _route_task_to_agent(title: str) -> str:
    """Route a task to the correct agent based on its title keywords."""
    title_lower = title.lower()
    builder_score = sum(1 for kw in _BUILDER_KEYWORDS if kw in title_lower)
    security_score = sum(1 for kw in _SECURITY_KEYWORDS if kw in title_lower)
    head_score = sum(1 for kw in _HEAD_KEYWORDS if kw in title_lower)

    if builder_score > security_score and builder_score > head_score:
        return "Builder Agent"
    if security_score > builder_score and security_score > head_score:
        return "Security Agent"
    if head_score > 0:
        return "Head Agent"
    # Default: anything that looks like implementation goes to Builder
    return "Builder Agent"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup / Shutdown Lifecycle ─────────────────────────────────────────

@app.on_event("startup")
async def startup_lifecycle():
    """Sprint 4.5: On startup, recover interrupted jobs, clean orphan
    processes, and start the health monitor."""
    recovered = job_manager.recover_jobs()
    if recovered:
        logger.info("Recovered %d interrupted jobs", recovered)

    cleaned = runtime_manager.cleanup_orphans()
    if cleaned:
        logger.info("Cleaned %d orphaned runtime entries", cleaned)

    await runtime_manager.start_health_monitor()
    logger.info("Agent OS backend started (Sprint 4.5)")


@app.on_event("shutdown")
async def shutdown_lifecycle():
    """Graceful shutdown: stop health monitor."""
    stopped = runtime_manager.stop_all()
    if stopped:
        logger.info("Stopped %d runtimes on shutdown", stopped)
    logger.info("Agent OS backend shutting down")


# ── Agent Endpoints ───────────────────────────────────────────────────────

@app.get("/agents", response_model=list[Agent])
def get_agents():
    return agent_service.list()


@app.get("/agents/{agent_id}", response_model=Agent)
def get_agent(agent_id: str):
    return agent_service.get(agent_id)


@app.post("/agents/start", response_model=Agent)
async def start_agent(action: AgentAction):
    agent = agent_service.update(action.agent_id, status="Running", current_task="Ready for delegated work")
    await event_bus.publish(
        Event(type="AGENT_STARTED", source=agent.name, message=f"{agent.name} started", severity="success", payload=agent.model_dump())
    )
    return agent


@app.post("/agents/stop", response_model=Agent)
async def stop_agent(action: AgentAction):
    agent = agent_service.update(action.agent_id, status="Idle", current_task="Stopped by operator")
    await event_bus.publish(
        Event(type="AGENT_STOPPED", source=agent.name, message=f"{agent.name} stopped", severity="warning", payload=agent.model_dump())
    )
    return agent


@app.post("/agents/pause", response_model=Agent)
async def pause_agent(action: AgentAction):
    agent = agent_service.update(action.agent_id, status="Paused", current_task="Paused by operator")
    await event_bus.publish(
        Event(type="AGENT_PAUSED", source=agent.name, message=f"{agent.name} paused", severity="warning", payload=agent.model_dump())
    )
    return agent


@app.post("/agents/restart", response_model=Agent)
async def restart_agent(action: AgentAction):
    agent = agent_service.update(action.agent_id, status="Running", current_task="Restarted and ready")
    await event_bus.publish(
        Event(type="AGENT_STARTED", source=agent.name, message=f"{agent.name} restarted", severity="success", payload=agent.model_dump())
    )
    return agent


# ── Task Endpoints ────────────────────────────────────────────────────────

@app.get("/tasks", response_model=list[Task])
def get_tasks():
    return task_service.list()


@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: str):
    return task_service.get(task_id)


@app.post("/tasks/create", response_model=Task)
async def create_task(payload: TaskCreate):
    task = task_service.create(payload)
    await event_bus.publish(
        Event(type="TASK_CREATED", source=task.assigned_agent, message=f"Task created: {task.title}", payload=task.model_dump())
    )
    return task


@app.patch("/tasks/update", response_model=Task)
async def update_task(payload: TaskUpdate):
    task = task_service.update(payload)
    event_type = "TASK_COMPLETED" if task.status == "Completed" else "TASK_STARTED"
    await event_bus.publish(
        Event(type=event_type, source=task.assigned_agent, message=f"Task updated: {task.title}", payload=task.model_dump())
    )
    return task


# ── Workspace Endpoints ───────────────────────────────────────────────────

@app.get("/workspaces", response_model=list[Workspace])
def get_workspaces():
    return workspace_service.list()


@app.get("/workspaces/archive", response_model=list[WorkspaceArchiveEntry])
def get_workspace_archive():
    return workspace_service.list_archive()


@app.get("/workspaces/{workspace_id}", response_model=Workspace)
def get_workspace(workspace_id: str):
    return workspace_service.get(workspace_id)


@app.post("/workspaces/create", response_model=Workspace)
async def create_workspace(payload: WorkspaceCreate):
    workspace = workspace_service.create(payload)
    await event_bus.publish(
        Event(type="WORKSPACE_CREATED", source="Workspace Service", message=f"Workspace created: {workspace.name}", payload=workspace.model_dump())
    )
    return workspace


@app.delete("/workspaces/{workspace_id}")
async def delete_workspace(workspace_id: str):
    workspace = workspace_service.get(workspace_id)
    workspace_service.delete(workspace_id)
    await event_bus.publish(
        Event(
            type="WORKSPACE_UPDATED",
            source="Workspace Service",
            message=f"Workspace deleted: {workspace.name}",
            severity="warning",
            payload={"id": workspace_id, "deleted": True},
        )
    )
    return {"ok": True}


# ── Architect Endpoints ───────────────────────────────────────────────────

@app.post("/architect/chat", response_model=ArchitectChatResponse)
async def architect_chat(payload: ArchitectChatRequest):
    return architect_service.chat(payload.message, payload.conversation_id)


@app.post("/architect/approve", response_model=ArchitectApprovalResponse)
async def approve_architecture(payload: ArchitectApprovalRequest):
    import os
    os.makedirs("logs", exist_ok=True)
    with open("logs/approve_project_trace.log", "a") as f:
        f.write("APPROVE_REQUEST_RECEIVED\n")
    from app.services.task_decomposer import task_decomposer
    from app.services.task_validator import task_validator
    from app.services.task_graph import task_graph

    state = architect_service.approve(payload.conversation_id)
    try:
        architecture = state["architecture"]
        workspace = workspace_service.create(
            WorkspaceCreate(
                name=architecture["project_name"],
                description=architecture["architecture"],
                active_agents=1,
                path=workspace_service.path_for_project(architecture["project_name"]),
            )
        )
        with open("logs/approve_project_trace.log", "a") as f:
            f.write("WORKSPACE_CREATED\n")
        await event_bus.publish(
            Event(
                type="WORKSPACE_CREATED",
                source="Architect Agent",
                message=f"Workspace created from approved architecture: {workspace.name}",
                severity="success",
                payload=workspace.model_dump(),
            )
        )
        # Sprint 4: Ensure spec exists and write it to disk
        spec = state.get("spec")
        if not spec:
            spec = spec_engine.generate_spec(state)
            state["spec"] = spec
            
        # Write spec to the workspace
        spec_engine.write_spec(workspace.path, spec)

        # ── Sprint M1: Atomic Task Decomposition ──────────────────────────
        architecture_tasks = architecture.get("task_breakdown", [])
        original_titles = [t.get("title", "") for t in architecture_tasks]

        # Step 1: Decompose coarse tasks into atomic micro-tasks
        atomic_tasks = task_decomposer.decompose(architecture_tasks, spec)

        # Step 2: Validate atomic tasks (reject vague, duplicate, planning tasks)
        validation = task_validator.validate(atomic_tasks, original_titles=original_titles)

        # Step 3: Log the planning trace
        task_graph.save(
            workspace_path=workspace.path,
            architecture_tasks=architecture_tasks,
            expansion_log=task_decomposer.last_expansion_log,
            final_tasks=validation.accepted,
            validation_report=validation.to_dict(),
        )

        # Step 4: Create validated atomic tasks in the system
        tasks = []
        for item in validation.accepted:
            task_title = item.get("title", "Atomic task")
            base_desc = item.get("description", "Generated from atomic decomposition.")
            
            # Enrich task description with project context
            enriched_desc = spec_engine.enrich_task_description(task_title, base_desc, spec)
            
            task = task_service.create(
                TaskCreate(
                    title=task_title,
                    description=enriched_desc,
                    assigned_agent=_route_task_to_agent(task_title),
                    priority=item.get("priority", "Medium"),
                    workspace_id=workspace.id,
                )
            )
            tasks.append(task)
            await event_bus.publish(
                Event(
                    type="TASK_CREATED",
                    source="Architect Agent",
                    message=f"Atomic task created: {task.title}",
                    severity="success",
                    payload=task.model_dump(),
                )
            )

        logger.info(
            "Sprint M1: Decomposed %d coarse tasks → %d atomic tasks (%d rejected)",
            len(architecture_tasks), len(tasks), validation.rejected_count,
        )
        with open("logs/approve_project_trace.log", "a") as f:
            f.write("TASKS_CREATED\n")

        workspace = workspace_service.update(workspace.id, task_count=len(tasks))
        await event_bus.publish(
            Event(
                type="WORKSPACE_UPDATED",
                source="Architect Agent",
                message=f"Workspace atomic tasks attached: {workspace.name} ({len(tasks)} tasks)",
                severity="success",
                payload=workspace.model_dump(),
            )
        )
        await event_bus.publish(
            Event(
                type="ARCHITECT_APPROVED",
                source="Architect Agent",
                message=f"Architecture approved for {workspace.name}",
                severity="success",
                payload={"conversation_id": payload.conversation_id, "workspace_id": workspace.id},
            )
        )

        # ── AUTO-START BUILD PIPELINE ─────────────────────────────────────
        await build_orchestrator.start_pipeline(workspace.id, architecture)
        with open("logs/approve_project_trace.log", "a") as f:
            f.write("BUILD_STARTED\n")

        return ArchitectApprovalResponse(conversation_id=payload.conversation_id, approved=True, workspace=workspace, tasks=tasks)
    except Exception as e:
        with open("logs/approve_project_trace.log", "a") as f:
            f.write("BUILD_FAILED\n")
        raise e


# ── Build Pipeline Endpoints ──────────────────────────────────────────────

@app.post("/build/start")
async def start_build(payload: BuildStartRequest):
    workspace = workspace_service.get(payload.workspace_id)
    await build_orchestrator.start_pipeline(payload.workspace_id)
    return {"ok": True, "workspace_id": payload.workspace_id, "message": f"Build started for {workspace.name}"}


@app.get("/build/progress/{workspace_id}", response_model=BuildProgress)
def get_build_progress(workspace_id: str):
    return build_orchestrator.get_build_progress(workspace_id)


@app.post("/build/cancel/{workspace_id}")
def cancel_build(workspace_id: str):
    cancelled = build_orchestrator.cancel_build(workspace_id)
    return {"ok": cancelled, "workspace_id": workspace_id}


@app.get("/build/report/{workspace_id}")
def get_build_report(workspace_id: str):
    report = workspace_service.get_build_report(workspace_id)
    if not report:
        return {"error": "No build report found", "workspace_id": workspace_id}
    return report


# ── Activity, Sandbox, System Endpoints ───────────────────────────────────

@app.get("/activity")
def get_activity():
    return activity_service.list()


@app.get("/sandbox", response_model=SandboxState)
def get_sandbox():
    return sandbox_service.get_state()

@app.post("/log_trace")
def log_trace(payload: LogTraceRequest):
    import os
    os.makedirs("logs", exist_ok=True)
    with open("logs/approve_project_trace.log", "a") as f:
        f.write(f"FRONTEND: {payload.message}\n")
    return {"status": "ok"}

@app.patch("/sandbox/settings", response_model=SandboxState)
def update_sandbox_settings(payload: SandboxSettings):
    return sandbox_service.update_root(payload.project_root)


@app.get("/system/status", response_model=SystemStatus)
def get_system_status():
    return system_service.status()


# ── MCP Execute ───────────────────────────────────────────────────────────

@app.post("/mcp/execute")
async def execute_mcp(payload: MCPExecuteRequest):
    return await mcp_registry.execute(
        agent_role=payload.agent_role,
        namespace=payload.namespace,
        tool_name=payload.tool_name,
        params=payload.params,
    )


# ── Logs Endpoint ─────────────────────────────────────────────────────────

@app.get("/logs/{workspace_id}")
def get_logs(workspace_id: str, agent: str | None = None, limit: int = 100):
    return execution_logger.read_logs(workspace_id, agent_filter=agent, limit=limit)


# ── Sprint 4.5: Job Endpoints ────────────────────────────────────────────

@app.get("/jobs", response_model=list[Job])
def get_jobs():
    return job_manager.list_jobs()


@app.get("/jobs/{job_id}", response_model=Job)
def get_job(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        return {"error": "Job not found"}
    return job


@app.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    cancelled = job_manager.cancel_job(job_id)
    return {"ok": cancelled, "job_id": job_id}


# ── Sprint 4.5: Runtime Endpoints ────────────────────────────────────────

@app.get("/runtimes", response_model=list[RuntimeEntry])
def get_runtimes():
    return runtime_manager.list_runtimes()


@app.get("/runtimes/{workspace_id}")
def get_runtime(workspace_id: str):
    health = runtime_manager.check_health(workspace_id)
    return health


@app.post("/runtimes/stop")
async def stop_runtime(payload: RuntimeStopRequest):
    stopped = runtime_manager.stop_runtime(payload.workspace_id)
    if stopped:
        await event_bus.publish(Event(
            type="RUNTIME_STOPPED",
            source="Runtime Manager",
            message=f"Runtime stopped for workspace {payload.workspace_id}",
            severity="warning",
            payload={"workspace_id": payload.workspace_id},
        ))
    return {"ok": stopped, "workspace_id": payload.workspace_id}


# ── Sprint 4.5: Timeline Endpoint ────────────────────────────────────────

@app.get("/timeline")
def get_timeline(limit: int = 100):
    return event_bus.get_timeline(limit)


# ── WebSocket Channels ───────────────────────────────────────────────────

@app.websocket("/ws/activity")
async def activity_socket(websocket: WebSocket):
    await stream_channel("activity", websocket, [event.model_dump() for event in activity_service.list()[:20]])


@app.websocket("/ws/agents")
async def agents_socket(websocket: WebSocket):
    await stream_channel("agents", websocket, [agent.model_dump() for agent in agent_service.list()])


@app.websocket("/ws/tasks")
async def tasks_socket(websocket: WebSocket):
    await stream_channel("tasks", websocket, [task.model_dump() for task in task_service.list()])


@app.websocket("/ws/workspaces")
async def workspaces_socket(websocket: WebSocket):
    await stream_channel("workspaces", websocket, [workspace.model_dump() for workspace in workspace_service.list()])


@app.websocket("/ws/system")
async def system_socket(websocket: WebSocket):
    await stream_channel("system", websocket, [system_service.status().model_dump()])


@app.websocket("/ws/build")
async def build_socket(websocket: WebSocket):
    await stream_channel("build", websocket, [])


@app.websocket("/ws/jobs")
async def jobs_socket(websocket: WebSocket):
    """Sprint 4.5: WebSocket channel for job status updates."""
    await stream_channel("jobs", websocket, [job.model_dump() for job in job_manager.active_jobs()])


@app.websocket("/ws/runtimes")
async def runtimes_socket(websocket: WebSocket):
    """Sprint 4.5: WebSocket channel for runtime status updates."""
    await stream_channel("runtimes", websocket, [rt.model_dump() for rt in runtime_manager.list_runtimes()])


async def stream_channel(channel: str, websocket: WebSocket, initial_messages: list[dict]):
    await websocket_manager.connect(channel, websocket)
    try:
        for message in initial_messages:
            await websocket.send_json(message)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(channel, websocket)
