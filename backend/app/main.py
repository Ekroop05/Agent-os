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
    BuildStartRequest,
    Event,
    SandboxSettings,
    SandboxState,
    SystemStatus,
    Task,
    TaskCreate,
    TaskUpdate,
    Workspace,
    WorkspaceCreate,
    MCPExecuteRequest,
)
from app.services.activity_service import activity_service
from app.services.agent_service import agent_service
from app.services.architect_service import architect_service
from app.services.build_orchestrator import build_orchestrator
from app.services.sandbox_service import sandbox_service
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

app = FastAPI(title="Agent OS API", version="0.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    state = architect_service.approve(payload.conversation_id)
    architecture = state["architecture"]
    workspace = workspace_service.create(
        WorkspaceCreate(
            name=architecture["project_name"],
            description=architecture["architecture"],
            active_agents=1,
            path=workspace_service.path_for_project(architecture["project_name"]),
        )
    )
    await event_bus.publish(
        Event(
            type="WORKSPACE_CREATED",
            source="Architect Agent",
            message=f"Workspace created from approved architecture: {workspace.name}",
            severity="success",
            payload=workspace.model_dump(),
        )
    )

    tasks = []
    for item in architecture.get("task_breakdown", []):
        task = task_service.create(
            TaskCreate(
                title=item.get("title", "Architecture task"),
                description=item.get("description", "Generated from approved architecture."),
                assigned_agent="Head Agent",
                priority=item.get("priority", "Medium"),
                workspace_id=workspace.id,
            )
        )
        tasks.append(task)
        await event_bus.publish(
            Event(
                type="TASK_CREATED",
                source="Architect Agent",
                message=f"Task created from approved architecture: {task.title}",
                severity="success",
                payload=task.model_dump(),
            )
        )

    workspace = workspace_service.update(workspace.id, task_count=len(tasks))
    await event_bus.publish(
        Event(
            type="WORKSPACE_UPDATED",
            source="Architect Agent",
            message=f"Workspace planning tasks attached: {workspace.name}",
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

    return ArchitectApprovalResponse(conversation_id=payload.conversation_id, approved=True, workspace=workspace, tasks=tasks)


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


# ── Activity, Sandbox, System Endpoints ───────────────────────────────────

@app.get("/activity")
def get_activity():
    return activity_service.list()


@app.get("/sandbox", response_model=SandboxState)
def get_sandbox():
    return sandbox_service.get_state()


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


async def stream_channel(channel: str, websocket: WebSocket, initial_messages: list[dict]):
    await websocket_manager.connect(channel, websocket)
    try:
        for message in initial_messages:
            await websocket.send_json(message)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(channel, websocket)
