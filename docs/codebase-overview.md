# Codebase Overview — Agent OS v2

This document provides a comprehensive inventory of the Agent OS codebase, detailing its folder structure, major modules, services, UI components, state management, APIs, background jobs, build system, agent system, and utilities.

---

## 1. Directory & Folder Structure

Agent OS follows a modern decoupled client-server architecture organized into a Python FastAPI backend and a React (Vite) frontend.

```text
Agent-os/
├── backend/                  # Python 3.10+ FastAPI Server
│   └── app/
│       ├── api/              # HTTP REST routes and WebSocket handlers
│       ├── core/             # Configuration, event bus, and WebSocket connection manager
│       ├── extractors/       # AI requirement extraction pipeline
│       ├── mcp/              # Model Context Protocol (MCP) tool integrations
│       ├── models/           # Data domain models
│       ├── services/         # Core domain services and autonomous agent orchestration
│       ├── state/            # Project state persistence layer
│       ├── main.py           # Application entry point and background loops
│       └── schemas.py        # Pydantic validation schemas
├── frontend/                 # React 19 + Vite SPA
│   └── src/
│       ├── assets/           # Static icons and media
│       ├── components/       # Reusable UI widgets and workspace monitors
│       │   ├── ui/           # Primitive UI components (Buttons, Modals, Badges)
│       │   └── workspace/    # Complex build visualizations (TaskGraph, BuildTimeline)
│       ├── layout/           # App shell layout wrappers
│       ├── pages/            # Primary routing pages (Dashboard, Architect, Workspaces, etc.)
│       ├── services/         # REST client, WebSocket wrapper, and reactive state stores
│       ├── styles/           # Global design tokens and typography
│       ├── App.jsx           # Main application router and channel listener
│       └── main.jsx          # DOM entry point
├── database/                 # SQLite database storage for persistence
├── docker/                   # Containerization and execution sandboxes
├── docs/                     # Architectural documentation and sprint reports
└── workspace/                # Local runtime target directory for generated code
```

---

## 2. Major Modules

### Backend Core (`backend/app/core/`)
- **`config.py`**: Manages environment variables, workspace root paths, model selection (`Gemini 3.1 Pro`), and execution timeouts.
- **`event_bus.py`**: In-memory asynchronous event pub/sub system decoupling service execution from WebSocket broadcasting.
- **`websocket_manager.py`**: Manages multi-channel WebSocket client connections and handles envelope framing.

### MCP Layer (`backend/app/mcp/`)
Implements the Model Context Protocol, enabling agents to safely interact with local filesystem and system resources:
- **`file_mcp.py`**: Read, write, and list workspace files safely within sandboxed boundaries.
- **`git_mcp.py`**: Git initialization, committing, and diffing for version-controlled code generation.
- **`terminal_mcp.py`**: Controlled execution of shell commands and test runners.
- **`task_mcp.py` & `project_mcp.py`**: Agent interfaces for querying and updating task progression and project metadata.

---

## 3. Core Services (`backend/app/services/`)

The business logic is encapsulated inside specialized service modules:
- **`architect_service.py`**: Handles conversational AI interactions, intent pre-filtering (`classify_intent`), and triggers requirement extraction.
- **`builder_service.py`**: Executes autonomous code generation from task specifications.
- **`build_orchestrator.py`**: Coordinates multi-task execution sequences, manages build phases, and emits real-time build telemetry.
- **`planner_agent.py` & `task_decomposer.py`**: Decomposes high-level architectures into directed acyclic graphs (DAGs) of executable tasks.
- **`job_manager.py`**: Manages long-running background tasks with status tracking and percentage progress.
- **`runtime_manager.py` & `sandbox_service.py`**: Manages isolated execution environments for running and testing generated software.
- **`security_service.py` & `command_security.py` & `path_security.py`**: Enforces path traversal prevention and restricts dangerous terminal commands.
- **`workspace_service.py`**: CRUD operations and lifecycle management for workspaces.
- **`system_service.py`**: Monitors system health metrics (CPU, RAM, Disk, active Python/Agent OS processes) via `psutil`.

---

## 4. UI Components (`frontend/src/`)

### Page Views (`pages/`)
- **`Dashboard.jsx`**: Command center displaying active builds, system health, and quick navigation.
- **`Architect.jsx`**: Conversational interface for planning and defining technical specifications.
- **`Workspaces.jsx`**: Live inspection of code generation, file tree exploration, task graphs, and diagnostics.
- **`Tasks.jsx`**: Tabular and status view of all scheduled and completed development tasks.
- **`Agents.jsx`**: Status overview of active AI personas (Architect, Builder, QA, Security).
- **`Activity.jsx`**: Real-time system log feed.
- **`Sandbox.jsx`**: Runtime execution preview and container management.
- **`Settings.jsx`**: Configuration interface for models and system preferences.

### Workspace Widgets (`components/workspace/`)
- **`TaskGraph.jsx`**: Interactive visualization of task dependency trees.
- **`BuildTimeline.jsx` & `EditTimeline.jsx`**: Chronological progression of file modifications and build phases.
- **`SystemMonitor.jsx`**: Animated 4-card gauge showing live CPU load, RAM allocation, storage, and WebSocket uptime.
- **`FileExplorer.jsx`**: Tree view of workspace files with code preview capabilities.
- **`FailureDiagnostics.jsx`**: Detailed error reporting and stack trace analysis for failed tasks.

---

## 5. State Management

### Backend State
- **`state/project_state.py`**: Maintains global JSON/SQLite representation of projects, workspaces, and active execution flags.
- **In-Memory Singletons**: Services hold ephemeral state (e.g., active background tasks in `job_manager.py`, WebSocket subscribers in `websocket_manager.py`).

### Frontend State
- **Reactive Store (`services/architectStore.js`)**: Decouples chat messages, typing state, and approval phase from React component unmounting, preventing data loss during route transitions.
- **Global App Shell (`App.jsx`)**: Maintains WebSocket connections across 6 distinct channels (`workspaces`, `system`, `build`, `jobs`, `activity`, `agents`) and pushes real-time updates into local React state.

---

## 6. API & Communication Interfaces

### REST Endpoints (`backend/app/api/routes.py`)
- Standard CRUD operations for `/workspaces`, `/tasks`, `/agents`, `/activity`, and `/jobs`.
- Action endpoints: `/architect/chat`, `/architect/approve`, `/build/start`, `/runtime/start`.

### WebSocket Channels
Envelopes are streamed over dedicated multiplexed WebSocket endpoints:
- `/ws/activity`: System log events.
- `/ws/agent`: Agent lifecycle state changes.
- `/ws/task`: Task creation and progress updates.
- `/ws/workspaces`: Workspace synchronization.
- `/ws/build`: Live file generation and execution streaming.
- `/ws/system`: Periodic 3-second hardware telemetry broadcasts.

---

## 7. Background Jobs & Build System

- **Asyncio Background Tasks**: In `main.py`, background loops (`_system_broadcaster_loop`) continuously gather hardware metrics and broadcast them to connected clients.
- **Job Manager (`job_manager.py`)**: Spawns non-blocking execution threads for lengthy build sequences, allowing HTTP requests to respond immediately while work continues asynchronously.
- **Build Orchestrator (`build_orchestrator.py`)**: Traverses task dependencies sequentially or in parallel, invoking the Builder agent for each task and validating outputs.

---

## 8. Agent System

Agent OS implements four core AI personas:
1. **Architect**: Analyzes user intent, extracts requirements, and generates formal system specifications.
2. **Planner**: Translates specifications into ordered, atomic development tasks.
3. **Builder**: Consumes tasks, inspects existing workspace context via MCP, and generates clean code files.
4. **Security / QA**: Scans generated code for vulnerabilities and verifies build correctness.

---

## 9. Utilities & Security

- **Path Security (`path_security.py`)**: Restricts all file writes strictly within designated workspace paths, preventing directory traversal attacks.
- **Command Security (`command_security.py`)**: Filters terminal executions against a strict allowlist/denylist of OS commands.
- **Pydantic Schemas (`schemas.py`)**: Strongly types all inter-service and network communication payloads.
