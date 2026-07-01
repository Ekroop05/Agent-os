# Shared State Model Design

## 1. Problem Statement
In distributed agent systems, mutating state randomly across different files causes catastrophic race conditions, phantom bugs, and lost context. Currently, `project_state.py` holds conversation state, while `spec_engine.py` generates the physical build state. As Agent OS introduces concurrency and multiple workflow steps, we must strictly define who owns state, how it is updated, and who can read it.

## 2. State Ownership & Scopes
State in Agent OS is strictly separated by lifecycle phases.

### 2.1 Conversation State (The "What")
- **Owner:** `ProjectStateManager` (Memory)
- **Scope:** Ephemeral to the active chat session (Keyed by `conversation_id`).
- **Writers:** ONLY the Requirements phase (Requirement Extractor / Intelligence Engine).
- **Readers:** Architect, Planner, Validators.
- **Purpose:** Accumulate the user's intent, constraints, and raw requirements before the build begins.

### 2.2 Specification State (The "How")
- **Owner:** `SpecEngine` (Disk - `.agentos/spec.json`)
- **Scope:** Persistent per Workspace.
- **Writers:** ONLY the Planner Engine. Once written, it is immutable during a build.
- **Readers:** Task Decomposer, Engineering Standards, Builder Engine, Evaluation Engine.
- **Purpose:** The single source of truth for the physical architecture being generated.

### 2.3 Execution State (The "Progress")
- **Owner:** `JobManager` / `TaskGraph`
- **Scope:** Persistent per Workspace Build Run.
- **Writers:** ONLY the Workflow Orchestrator and Execution logger.
- **Readers:** UI, Telemetry, Evaluators.
- **Purpose:** Track which files have been created, which tasks failed, and the current progress percentage.

## 3. Concurrency Strategy (Future Proofing)
- **Single Writer Principle:** For any given scope (Conversation, Specification, Execution), only ONE engine is authorized to mutate that state. Other engines MUST read it as a deep-copy or receive it immutably via the `WorkflowContext`.
- **Versioning:** When an Editing Mode is introduced (modifying an existing specification), the `SpecEngine` will create `spec.v2.json`. The older state is never overwritten, supporting rollbacks.
- **Locking:** When the Orchestrator initiates a build, the Conversation State is "locked". The user cannot chat with the Architect to change requirements while the Builder is actively generating the project.

## 4. WorkflowContext (Data Transfer Object)
To prevent engines from reaching into global state singletons directly, the Orchestrator passes a `WorkflowContext` into every engine's `execute` method.

```python
class WorkflowContext(BaseModel):
    conversation_id: str
    workspace_id: str
    trace_id: str
    shared_memory: dict  # Read-only snapshot of current relevant state
```

Engines return payload updates in their `EngineResult`. The Orchestrator is responsible for committing those updates back to the persistent state owners.
