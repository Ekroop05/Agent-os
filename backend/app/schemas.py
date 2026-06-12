from pydantic import BaseModel, Field


class Agent(BaseModel):
    id: str
    name: str
    role: str
    status: str
    model: str
    current_task: str
    uptime: str
    memory_usage: int = Field(ge=0, le=100)


class AgentCreate(BaseModel):
    name: str
    role: str
    model: str
    current_task: str = "Waiting for assignment"


class AgentAction(BaseModel):
    agent_id: str


class Task(BaseModel):
    id: str
    title: str
    description: str
    assigned_agent: str
    priority: str
    status: str
    created_at: str
    completed_at: str | None = None
    workspace_id: str | None = None
    started_at: str | None = None
    duration_seconds: float | None = None
    output_files: list[str] = Field(default_factory=list)
    security_status: str = "Pending"          # Pending | Reviewing | Approved | Rejected
    security_notes: str | None = None


class TaskCreate(BaseModel):
    title: str
    description: str
    assigned_agent: str
    priority: str = "Medium"
    workspace_id: str | None = None


class TaskUpdate(BaseModel):
    id: str
    title: str | None = None
    description: str | None = None
    assigned_agent: str | None = None
    priority: str | None = None
    status: str | None = None
    completed_at: str | None = None
    started_at: str | None = None
    duration_seconds: float | None = None
    output_files: list[str] | None = None
    security_status: str | None = None
    security_notes: str | None = None


class Workspace(BaseModel):
    id: str
    name: str
    description: str
    status: str
    active_agents: int
    task_count: int
    created_at: str
    path: str
    progress: int = 0
    estimated_completion_minutes: float | None = None
    current_agent: str | None = None
    current_task_title: str | None = None
    build_status: str = "Planning"            # Planning | Building | Reviewing | Completed | Failed


class WorkspaceCreate(BaseModel):
    name: str
    description: str
    active_agents: int = 0
    path: str | None = None


class ActivityLog(BaseModel):
    id: str
    timestamp: str
    source: str
    type: str
    message: str
    severity: str


class SystemStatus(BaseModel):
    cpu_usage: int = Field(ge=0, le=100)
    memory_usage: int = Field(ge=0, le=100)
    active_connections: int
    active_agents: int
    active_tasks: int
    active_workspaces: int


class Event(BaseModel):
    type: str
    source: str
    message: str
    severity: str = "info"
    payload: dict = Field(default_factory=dict)


class ArchitectChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ArchitectChatResponse(BaseModel):
    conversation_id: str
    reply: str
    requirements_complete: bool
    approval_required: bool
    project_name: str | None = None
    architecture: dict | None = None
    approved: bool = False
    current_phase: str = "Discovering Requirements"
    requirements_progress: int = 0
    confidence_score: int = 0


class ArchitectApprovalRequest(BaseModel):
    conversation_id: str


class ArchitectApprovalResponse(BaseModel):
    conversation_id: str
    approved: bool
    workspace: Workspace
    tasks: list[Task]


class SandboxSettings(BaseModel):
    project_root: str = "D:/Projects"


class SandboxState(BaseModel):
    project_root: str
    projects: list[dict]
    workspace_mappings: list[dict]


class MCPExecuteRequest(BaseModel):
    agent_role: str
    namespace: str
    tool_name: str
    params: dict = Field(default_factory=dict)


# ── Build Pipeline Schemas ────────────────────────────────────────────────

class BuildProgress(BaseModel):
    workspace_id: str
    total_tasks: int = 0
    completed_tasks: int = 0
    progress_percent: int = 0
    estimated_minutes_remaining: float | None = None
    current_agent: str | None = None
    current_task_title: str | None = None
    build_status: str = "Planning"
    last_activity: str | None = None


class BuildStartRequest(BaseModel):
    workspace_id: str


class SecurityReviewResult(BaseModel):
    task_id: str
    approved: bool
    issues: list[str] = Field(default_factory=list)
    notes: str | None = None
