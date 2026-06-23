# Approve Project Flow

## 1. Frontend Interaction
- **Component**: `frontend/src/pages/Architect.jsx`
- **Action**: User clicks the "Approve Project" button.
- **Handler**: `approveProject()` executes.

## 2. API Request
- **Function**: `api.approveArchitecture(conversationId)` in `frontend/src/services/api.js`
- **Request**: Sends a `POST` request to `/architect/approve` with `conversation_id`.

## 3. Backend Route & Service
- **Route**: `@app.post("/architect/approve")` in `backend/app/main.py`.
- **Validation**: Checks if conversation exists and requirements are complete via `architect_service.approve()`.
- **State Update**: Updates `state["approved"] = True`.

## 4. Workspace Creation
- **Function**: `workspace_service.create()` in `backend/app/main.py`.
- **Action**: Creates the workspace record in memory and persists to disk.
- **Event**: Publishes `WORKSPACE_CREATED` to `event_bus`. (Frontend `App.jsx` handles this via WebSocket and updates global `workspaces` state).
- **Spec Writing**: `spec_engine.write_spec` creates the `.agentos/spec.json` on disk.

## 5. Task Decomposition & Creation (The Root Cause of Delay)
- **Function**: `task_decomposer.decompose()` is invoked on the coarse `architecture["task_breakdown"]`.
- **Delay**: If tasks do not match templates, it synchronously calls an LLM (`qwen3:14b`), blocking the HTTP thread for 10-60+ seconds.
- **Validation**: `task_validator.validate()` checks tasks for vagueness, duplication, etc.
- **Logging**: `task_graph.save()` writes the task graph to `.agentos/planning/task_graph.json`.
- **Creation**: Validated tasks are created via `task_service.create()`.
- **Event**: Publishes `TASK_CREATED` to `event_bus`. (Frontend `App.jsx` handles this and updates global `tasks` state).

## 6. Build Orchestration
- **Function**: `build_orchestrator.start_pipeline()`
- **Action**: Creates a background Job (`agent="Builder"`) via `job_manager`.
- **Event**: The `start_job` publishes `JOB_STARTED`. Inside the async task, `_run_pipeline` publishes `BUILD_STARTED`. 
- **Frontend Sync**: Frontend receives `BUILD_STARTED` and explicitly re-fetches workspaces and tasks from the REST API to ensure global state consistency.

## 7. API Response & UI Update
- **Response**: The `POST` endpoint finally returns the `ArchitectApprovalResponse`.
- **Frontend State**: `Architect.jsx`'s `approveProject` promise resolves. It calls `setStatus(...)` to show the button as "✓ Project Approved", `setMessages(...)` to display the confirmation chat, and `setData(...)` to apply the workspace mappings to the local sandbox state.
