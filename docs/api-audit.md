# API Comprehensive Audit — Agent OS v2

This document audits all REST HTTP endpoints and WebSocket streaming channels exposed by the FastAPI backend (`backend/app/api/routes.py`). It identifies active consumers, underlying dependencies, redundant endpoints, and required future APIs.

---

## 1. Active REST Endpoints & WebSocket Channels

| Endpoint / Channel | Type | Purpose | Primary Consumers | Underlying Dependencies |
| :--- | :--- | :--- | :--- | :--- |
| `/api/workspaces` | GET, POST | List existing workspaces or create a new workspace project | `Dashboard.jsx`, `Workspaces.jsx` | `workspace_service.py`, `project_state.py` |
| `/api/workspaces/{id}` | GET, DELETE | Fetch detailed manifest or delete workspace files | `Workspaces.jsx` | `workspace_service.py` |
| `/api/architect/chat` | POST | Send user message to Architect AI persona | `Architect.jsx`, `architectStore.js` | `architect_service.py`, `requirement_extractor.py` |
| `/api/architect/approve` | POST | Approve generated spec and initiate task planning | `Architect.jsx` | `spec_engine.py`, `planner_agent.py` |
| `/api/build/start` | POST | Trigger background Builder execution loop | `Workspaces.jsx` | `build_orchestrator.py`, `job_manager.py` |
| `/api/tasks` | GET | Retrieve master list of tasks across workspaces | `Tasks.jsx` | `project_state.py` |
| `/api/agents` | GET | Retrieve current status and persona metadata | `Agents.jsx` | `agent_service.py` |
| `/api/activity` | GET | Retrieve historical execution log entries | `Activity.jsx` | `execution_logger.py` |
| `/api/runtime/start` | POST | Mount container and boot dev server for testing | `Sandbox.jsx` | `runtime_manager.py`, `sandbox_service.py` |
| `/ws/workspaces` | WebSocket | Stream real-time workspace creation and metadata diffs | `App.jsx`, `Workspaces.jsx` | `websocket_manager.py`, Event Bus |
| `/ws/build` | WebSocket | Stream generated code files and terminal build logs | `App.jsx`, `Workspaces.jsx` | `websocket_manager.py`, Event Bus |
| `/ws/system` | WebSocket | Stream 3-second psutil hardware metrics heartbeat | `App.jsx`, `SystemMonitor.jsx` | `system_service.py` |
| `/ws/task` | WebSocket | Stream task progression status updates | `App.jsx`, `Tasks.jsx` | `websocket_manager.py`, Event Bus |
| `/ws/activity` | WebSocket | Stream global system log events | `App.jsx`, `Activity.jsx` | `websocket_manager.py`, Event Bus |
| `/ws/agents` | WebSocket | Stream AI persona status transitions (`Running`/`Idle`) | `App.jsx`, `Agents.jsx` | `websocket_manager.py`, Event Bus |

---

## 2. Unused & Redundant APIs

- **`/api/activity` (GET)**: While exposed by routes, the frontend `Activity.jsx` relies almost exclusively on live streamed payloads from `/ws/activity`, rendering historical pagination endpoints rarely consumed after initial page load.
- **Multiplexed Socket Overheads**: Maintaining 6 distinct WebSocket endpoints requires 6 separate TCP handshake procedures per client browser. These should be consolidated into a single multiplexed `/ws/stream` endpoint with topic routing envelopes.

---

## 3. Missing & Potential Future APIs

### 1. `/api/workspaces/{id}/export` (GET)
Allow users to download the generated workspace directory as a compressed `.zip` or `.tar.gz` bundle directly from the dashboard.

### 2. `/api/workspaces/{id}/git/push` (POST)
Enable direct integration with GitHub/GitLab APIs, allowing Agent OS to commit generated builds and open Pull Requests directly against remote repositories.

### 3. `/api/models/test` (POST)
Allow frontend Settings page to ping configured LLM API keys and return latency/token validation metrics before attempting expensive code generation tasks.
