# Distributed Tracing Design

## 1. Problem Statement
When the Builder fails to generate a valid component, the root cause could lie anywhere: the LLM hallucinated, the Planner generated a bad spec, the Requirement Intelligence Engine inferred the wrong constraint, or the user prompted poorly. Without distributed tracing, debugging AI execution flows relies on reading massive text log files.

## 2. Telemetry Model
Agent OS will adopt a lightweight telemetry model inspired by OpenTelemetry, optimized for AI agent workflows.

### 2.1 Trace ID
Every top-level user action (e.g., "Approve Project Architecture") generates a unique UUID called the `Trace ID`. This ID is injected into the `WorkflowContext` and propagates through every Engine and LLM call.

### 2.2 Spans
Every Engine execution represents a "Span". A Span records:
- `span_id`: UUID for this specific step.
- `parent_span_id`: Enables hierarchical tracing (e.g., Task Decomposer span is a child of the Planning span).
- `engine_name`: Which subsystem is running (e.g., `BuilderEngine`).
- `step_name`: Contextual sub-step (e.g., `write_file_content`).

## 3. Telemetry Payload
Every Engine is responsible for logging its execution metrics back to the Orchestrator (or a dedicated Telemetry service) upon completion or failure.

```json
{
  "trace_id": "a1b2c3d4",
  "workflow_id": "create_project_flow",
  "engine_name": "engineering_standards",
  "step_name": "resolve_profile",
  "status": "SUCCESS",
  "duration_ms": 145,
  "retry_count": 0,
  "provider_metrics": {
    "model": "qwen3:14b",
    "prompt_tokens": 0,
    "completion_tokens": 0
  },
  "errors": []
}
```

## 4. Integration with Providers
The Provider Layer (LLM integration) will natively support tracing. Every prompt sent to a model will be timed and logged against the current active `Trace ID`, recording token counts to track LLM costs and latency bottlenecks.

## 5. Future UI Visualization
While the UI is out of scope for this initiative, this data model perfectly supports future "Trace Viewers" in the Agent OS dashboard, allowing engineers to:
1. Click on a failed generation task.
2. View the exact execution tree (Planner -> Decomposer -> Standards -> Builder).
3. Identify exactly which Engine or Prompt caused the failure.
