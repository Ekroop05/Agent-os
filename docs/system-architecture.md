# System Architecture — Agent OS v2

This document maps the end-to-end system architecture of Agent OS, illustrating how user requests flow through the React frontend, FastAPI backend services, AI agent orchestrators, and local filesystem sandboxes to produce generated software projects.

---

## 1. Architectural Flow Diagram

The following diagram illustrates the vertical hierarchy and communication flow across the platform:

```text
+-----------------------------------------------------------------------------------+
|                                     USER                                          |
|            Interacts via Web Browser (Dashboard, Architect Chat, Workspaces)      |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                              FRONTEND (React + Vite)                              |
|   App Shell • Pages • Components • Reactive Store (architectStore.js)            |
|   Communicates via HTTP REST & 6 Multiplexed WebSocket Channels                  |
+-----------------------------------------------------------------------------------+
                                         │
                        HTTP REST / WebSocket Envelopes
                                         ▼
+-----------------------------------------------------------------------------------+
|                           API LAYER (FastAPI Backend)                             |
|   routes.py • websocket_manager.py • Request Validation (schemas.py)             |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                                  SERVICE LAYER                                    |
|   architect_service • build_orchestrator • job_manager • system_service          |
|   Event Bus Pub/Sub • SQLite & In-Memory Project State Management                |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                                  AGENT SYSTEM                                     |
|   Architect Agent ──► Planner Agent ──► Task Decomposer ──► Builder Agent         |
|   Powered by LLM Service (Gemini 3.1 Pro High)                                   |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                           MODEL CONTEXT PROTOCOL (MCP)                            |
|   file_mcp • git_mcp • terminal_mcp • Security Sandboxing & Path Enforcers        |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                               WORKSPACE RUNTIME                                   |
|   Local Filesystem Target Directory (./workspace/<project_id>/)                   |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                               GENERATED PROJECT                                   |
|   Source Code Files • Package Manifests • Git Repository • Execution Logs         |
+-----------------------------------------------------------------------------------+
```

---

## 2. Layer Responsibilities

### Frontend Layer
- **Responsibility**: Render interactive UI panels, maintain ephemeral chat/execution state, and display live streaming build events.
- **Key Modules**: `App.jsx`, `Architect.jsx`, `Workspaces.jsx`, `architectStore.js`.
- **Dependencies**: REST client (`api.js`), WebSocket client (`websocket.js`).

### API & Gateway Layer
- **Responsibility**: Terminate HTTP and WebSocket connections, authenticate/validate incoming requests using Pydantic schemas, and route traffic to appropriate internal services.
- **Key Modules**: `routes.py`, `websocket_manager.py`, `schemas.py`.

### Service Layer
- **Responsibility**: Maintain system workflows, schedule background execution jobs, manage workspace persistence, and broadcast system health heartbeats.
- **Key Modules**: `architect_service.py`, `build_orchestrator.py`, `job_manager.py`, `workspace_service.py`, `system_service.py`.

### Agent Orchestration Layer
- **Responsibility**: Emulate a multi-agent software engineering team.
  - **Architect**: Converts conversational prompts into structured specifications.
  - **Planner**: Decomposes specs into dependency-ordered atomic tasks.
  - **Builder**: Consumes tasks and generates working source code.
  - **Security**: Validates file operations and terminal execution commands.

### MCP & Sandbox Layer
- **Responsibility**: Provide safe, standardized interfaces for AI agents to interact with host operating system resources (filesystem, terminal, Git). Enforces strict boundary checks against directory traversal (`path_security.py`).

---

## 3. Communication Paths & Data Flow

### Synchronous Request-Response (HTTP REST)
Used for discrete, immediate actions such as querying workspace lists, fetching task graphs, submitting chat messages, and starting new projects.
```text
React Client ──REST POST /api/architect/chat──► FastAPI Router ──► Architect Service ──► LLM API
React Client ◄──REST 200 OK (Status + Reply)─── FastAPI Router ◄── Architect Service ◄── Response
```

### Asynchronous Telemetry & Event Streaming (WebSockets)
Used for continuous background updates where long-running operations occur outside the request-response lifecycle.
```text
Job Manager / Builder Agent ──► Event Bus ──► WebSocket Manager ──► Streamed Envelope ──► React Client App.jsx
```
The frontend listens across 6 dedicated channels:
1. `workspaces`: Triggers when workspace metadata or progress changes.
2. `tasks`: Streamlines task execution updates.
3. `agents`: Reports status changes (`Running`, `Idle`, `Reviewing`).
4. `build`: Emits real-time code generation diffs and terminal logs.
5. `system`: Broadcasts hardware utilization gauges every 3 seconds.
6. `activity`: Emits global event log stream.

---

## 4. Subsystem Dependencies

```text
+-------------------+       +---------------------+       +-------------------+
|  Frontend Client  | ───►  |  FastAPI Router     | ───►  |  Service Layer    |
+-------------------+       +---------------------+       +-------------------+
                                                                    │
                                                                    ▼
+-------------------+       +---------------------+       +-------------------+
|  Local Workspace  | ◄───  |  MCP Tool Handlers  | ◄───  |  Agent Orchestrator|
+-------------------+       +---------------------+       +-------------------+
```
1. **Frontend** depends exclusively on **API Router** definitions.
2. **API Router** depends on **Service Layer** instances.
3. **Service Layer** depends on **Agent Orchestrators** and the **Event Bus**.
4. **Agent Orchestrators** depend on the **LLM Service** and **MCP Handlers**.
5. **MCP Handlers** depend on **Path & Command Security** enforcers before touching the **Local Workspace**.
