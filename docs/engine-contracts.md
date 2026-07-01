# Engine Contracts

## Overview
To prevent tight coupling, spaghetti code, and cyclic dependencies, every engine in Agent OS must adhere to a standard **Engine Contract**. An Engine is a stateless processor that accepts a standardized request, performs a discrete domain of work, and returns a standardized result.

## The Contract Interface

Every future Engine must define the following metadata and implement the core execution method.

### 1. Engine Metadata
- **Engine Name:** A unique string identifier (e.g., `"engineering_standards"`).
- **Purpose:** A one-sentence description of its domain responsibility.
- **Version:** Semantic versioning to support backward-compatible migrations (e.g., `v1.0`).

### 2. Execution Signature
All engines must expose a single primary entry point (usually `execute` or `process`).

```python
def execute(self, request: EngineRequest, context: WorkflowContext) -> EngineResult:
    pass
```

### 3. Inputs (`EngineRequest`)
Engines must explicitly declare what data they require.
- **Payload:** The specific data required to do the work.
- **Strict Typing:** Inputs must be validated (e.g., using Pydantic schemas) before execution begins. Engines should *never* extract data directly from an arbitrary shared global state dict.

### 4. Outputs (`EngineResult`)
Engines must return a standardized response object.
- **Status:** `SUCCESS`, `FAILURE`, or `DEFERRED`.
- **Payload:** The domain-specific output data.
- **Errors:** If `FAILURE`, a structured list of errors must be provided.

### 5. Dependencies
Engines should NOT call other Engines directly. 
If Engine A requires the output of Engine B, the **Workflow Orchestrator** is responsible for calling Engine B, retrieving the output, and passing it as part of the `EngineRequest` to Engine A.

### 6. Failure Modes
Engines must declare how they fail:
- **Transient Failures:** (e.g., LLM timeout, network error). The Orchestrator may retry these.
- **Terminal Failures:** (e.g., Validation error, unrecoverable constraint). The Orchestrator must halt the workflow.
- **Graceful Degradation:** (e.g., Rule-based fallback if LLM intelligence fails). The Engine handles this internally and returns `SUCCESS` with the degraded payload.

### 7. Lifecycle & Extension Points
- Engines are initialized at application startup (Stateless Singletons).
- Engines may define explicit extension points (e.g., Plugins, Profiles, or Hooks) where domain logic can be extended without modifying the Engine's core loop.
