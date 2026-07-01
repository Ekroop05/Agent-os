# Workflow Orchestrator Design

## 1. Problem Statement
Currently, engines in Agent OS invoke one another directly. For example, `ArchitectService` calls `RequirementExtractor`. `PlannerAgent` calls `SpecEngine`. This point-to-point coupling makes the system brittle, hard to test, and difficult to observe. When an error occurs deep in the stack, managing retries or rollbacks becomes overly complex.

## 2. The Solution: Workflow Orchestrator
The **Workflow Orchestrator** is a centralized coordinating service. Engines no longer know about each other. Instead, the Orchestrator defines a "Workflow" (a directed acyclic graph of engine executions) and routes data between them.

## 3. Core Responsibilities
- **Start Workflows:** Initiate a sequence of engine executions based on a trigger (e.g., "User Approved Architecture").
- **Execute Steps:** Invoke engines via their standard `execute(EngineRequest, WorkflowContext)` contract.
- **Track Progress:** Record which steps have completed, which are pending, and the current state of the workflow payload.
- **Handle Retries:** If an Engine returns a transient error (e.g., `LLM_TIMEOUT`), the Orchestrator manages backoff and retry policies.
- **Handle Failures:** If a step fails terminally, the Orchestrator halts execution, records the failure, and triggers any compensation/rollback logic if applicable.
- **Manage Execution Order:** Ensure dependencies are met. (e.g., The Planner Engine must finish before the Task Decomposer Engine starts).

## 4. Architecture Diagram

```mermaid
graph TD
    A[Trigger / API] --> B(Workflow Orchestrator)
    B -->|1. execute()| C[Engine A (e.g., Planner)]
    C -->|EngineResult| B
    B -->|2. execute()| D[Engine B (e.g., Standards)]
    D -->|EngineResult| B
    B -->|3. execute()| E[Engine C (e.g., Builder)]
    E -->|EngineResult| B
    
    %% Tracing and State
    B -.->|Logs State| F[(Shared State / Trace DB)]
```

## 5. Workflow Definitions
Workflows will be defined declaratively or via builder patterns.

**Example Conceptual Definition:**
```python
workflow = (
    WorkflowBuilder("ProjectCreation")
    .add_step(name="plan", engine=PlannerEngine)
    .add_step(name="standards", engine=EngineeringStandardsEngine, depends_on=["plan"])
    .add_step(name="decompose", engine=TaskDecomposerEngine, depends_on=["standards"])
    .build()
)
```

## 6. Migration Strategy
We will NOT rewrite the entire application to use the Orchestrator immediately. 
1. **Scaffold:** Define the `WorkflowOrchestrator` interfaces.
2. **Phase In:** Migrate one small background process (e.g., Task Evaluation) to use the Orchestrator.
3. **Full Adoption:** Gradually refactor the main Architect -> Planner -> Builder flow to be managed by the Orchestrator.
