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
    # Engineering Planning Metadata (Initiative 1)
    task_uid: str | None = None
    epic: str | None = None
    feature: str | None = None
    story: str | None = None
    objective: str | None = None
    expected_output: str | None = None
    acceptance_criteria: list[str] = Field(default_factory=list)
    complexity: str | None = None
    estimated_context: list[str] = Field(default_factory=list)
    context_dependencies: list[str] = Field(default_factory=list)
    engineering_metadata: dict | None = None


class TaskCreate(BaseModel):
    title: str
    description: str
    assigned_agent: str
    priority: str = "Medium"
    workspace_id: str | None = None
    # Engineering Planning Metadata (Initiative 1)
    task_uid: str | None = None
    epic: str | None = None
    feature: str | None = None
    story: str | None = None
    objective: str | None = None
    expected_output: str | None = None
    acceptance_criteria: list[str] = Field(default_factory=list)
    complexity: str | None = None
    estimated_context: list[str] = Field(default_factory=list)
    context_dependencies: list[str] = Field(default_factory=list)
    engineering_metadata: dict | None = None


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
    workspace_id: str | None = None
    # Engineering Planning Metadata (Initiative 1)
    task_uid: str | None = None
    epic: str | None = None
    feature: str | None = None
    story: str | None = None
    objective: str | None = None
    expected_output: str | None = None
    acceptance_criteria: list[str] | None = None
    complexity: str | None = None
    estimated_context: list[str] | None = None
    context_dependencies: list[str] | None = None
    engineering_metadata: dict | None = None


class Workspace(BaseModel):
    id: str
    project_name: str
    name: str
    slug: str
    description: str
    status: str = "Planning"            # Planning | Building | Reviewing | Completed | Failed
    active_agents: int
    task_count: int
    created_at: str
    path: str
    progress: int = 0
    estimated_completion_minutes: float | None = None
    current_agent: str | None = None
    current_task_title: str | None = None
    completed_at: str | None = None


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
    disk_usage: int = 0
    process_memory_mb: float = 0.0
    system_uptime: str = "0m"
    python_processes: int = 0
    agent_os_processes: int = 1
    available_memory_gb: float = 0.0
    agent_os_pid: int = 0


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
    status: str = "Planning"
    last_activity: str | None = None


class BuildStartRequest(BaseModel):
    workspace_id: str


class SecurityReviewResult(BaseModel):
    task_id: str
    approved: bool
    issues: list[str] = Field(default_factory=list)
    notes: str | None = None


class BuildReport(BaseModel):
    workspace_id: str
    project_name: str
    location: str
    files_created: int = 0
    pages_created: int = 0
    components_created: int = 0
    assets_created: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_total: int = 0
    security_reviews_approved: int = 0
    security_reviews_rejected: int = 0
    build_duration_seconds: float = 0
    build_duration_display: str = "0s"
    build_quality_score: int = 0
    warnings: list[str] = Field(default_factory=list)
    status: str = "Completed"
    generated_at: str = ""


class WorkspaceArchiveEntry(BaseModel):
    id: str
    project_name: str
    slug: str
    path: str
    status: str
    created_at: str
    completed_at: str | None = None
    task_count: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    progress: int = 0


# ── Sprint 4.5: Job Engine Schemas ────────────────────────────────────────

class Job(BaseModel):
    job_id: str
    agent: str
    status: str = "Pending"          # Pending | Running | Completed | Failed | Cancelled
    progress: int = 0
    message: str = ""
    started_at: str = ""
    updated_at: str = ""
    completed_at: str | None = None
    workspace_id: str | None = None
    conversation_id: str | None = None
    error: str | None = None


class JobCreateRequest(BaseModel):
    agent: str = "Architect"
    workspace_id: str | None = None
    conversation_id: str | None = None


# ── Sprint 4.5: Runtime Manager Schemas ───────────────────────────────────

class RuntimeEntry(BaseModel):
    workspace_id: str
    project_name: str = ""
    frontend_port: int | None = None
    backend_port: int | None = None
    frontend_pid: int | None = None
    backend_pid: int | None = None
    status: str = "stopped"          # running | stopped | error
    started_at: str = ""
    uptime_seconds: float = 0


class RuntimeStopRequest(BaseModel):
    workspace_id: str


# ── Sprint 4.5: Event Timeline Schema ────────────────────────────────────

class TimelineEvent(BaseModel):
    id: str
    timestamp: str
    event_type: str
    source: str
    message: str
    severity: str = "info"
    workspace_id: str | None = None
    job_id: str | None = None


# ── Sprint 5: Project Editing & Snapshots Schemas ─────────────────────────

class AnalyzeProjectRequest(BaseModel):
    project_path: str


class ProjectAnalysis(BaseModel):
    project_path: str
    project_name: str
    framework: str
    dependencies: dict
    file_tree: list[dict]
    file_counts: dict
    total_files: int
    components: list[str]
    pages: list[str]
    routes: list[str]
    services: list[str]
    assets: list[str]
    configs: list[str]
    component_count: int
    page_count: int
    route_count: int
    service_count: int
    risk_assessment: dict


class ProjectContextUpdate(BaseModel):
    project_name: str | None = None
    framework: str | None = None
    architecture: str | None = None


class SnapshotCreateRequest(BaseModel):
    workspace_id: str
    workspace_path: str
    label: str = ""


class SnapshotRestoreRequest(BaseModel):
    workspace_id: str
    workspace_path: str
    snapshot_id: str
