# State Management Audit — Agent OS v2

State inside Agent OS is distributed across frontend memory, backend singletons, SQLite persistence layers, and filesystem metadata. This audit maps the five primary state domains, analyzes lifecycle flow, identifies synchronization vulnerabilities, and assesses future scalability.

---

## 1. State Domains

### 1. Project State (`project_state.py`)
- **Scope**: Tracks global project definitions, high-level metadata, requirements progress, and overall phase status (`Brainstorming`, `Planning`, `Building`, `Completed`).
- **Storage**: Persisted to SQLite via `database/` and mirrored in-memory for rapid lookup.

### 2. Workspace State (`workspace_service.py` & `workspace.json`)
- **Scope**: Represents the physical target directory allocated for code generation. Tracks active file tree structures, generated diffs, build timelines, and task execution graphs.
- **Storage**: Persisted directly on disk inside `./workspace/<id>/workspace.json` and synchronized over WebSocket channels.

### 3. Runtime State (`runtime_manager.py` & `sandbox_service.py`)
- **Scope**: Tracks active container allocations, execution ports, process PIDs, and running server logs for testing generated code.
- **Storage**: Ephemeral in-memory dictionaries inside backend service instances.

### 4. Execution State (`job_manager.py` & `build_orchestrator.py`)
- **Scope**: Tracks background thread execution status (`Pending`, `Running`, `Completed`, `Failed`), percentage progress bars, and streaming AI generation tokens.
- **Storage**: Ephemeral in-memory state broadcast via Event Bus to WebSocket listeners.

### 5. Conversation State (`architect_service.py` & `architectStore.js`)
- **Scope**: Tracks user message history, AI responses, active intent classifications, and UI composer typing indicators.
- **Storage**: Maintained on the frontend via reactive singleton store (`architectStore.js`) backed by browser `sessionStorage`, and mirrored on backend memory during chat sessions.

---

## 2. State Flow Through the System

```text
Frontend Action (Chat / Build Click)
       │
       ▼ (HTTP POST / WebSocket)
Backend Service Layer (Updates Ephemeral In-Memory State)
       │
       ├──────────────────────────────┬─────────────────────────────┐
       ▼                              ▼                             ▼
SQLite Database Write        Filesystem JSON Write         Event Bus Publish
(Project State)              (Workspace State)             (WebSocket Broadcast)
                                                                    │
                                                                    ▼
                                                            Frontend App.jsx
                                                            (React State Update)
```

---

## 3. Duplication & Synchronization Issues

### Duplication Analysis
- **Task Graphs**: Stored simultaneously inside SQLite (`ProjectState`), filesystem metadata (`workspace.json`), and frontend React component state.
- **Conversation Logs**: Maintained in `architectStore.js` on the client while duplicate transcripts are retained in Python memory dictionaries during active sessions.

### Potential Synchronization Issues
1. **Race Conditions on Concurrent File Writes**: If multiple background builder threads finish tasks simultaneously, updating `workspace.json` without file locking mechanisms can cause data corruption or lost task status updates.
2. **WebSocket Desynchronization on Reconnect**: If a client browser loses network connectivity briefly during an active build, missed WebSocket envelopes cause UI state to drift out of sync with real backend execution state until a manual page refresh forces a fresh REST fetch.

---

## 4. Scalability Assessment

- **Current Limit**: Excellent performance for single-user local desktop deployment managing 1–5 active workspaces.
- **Scalability Bottleneck**: In-memory singleton stores (`job_manager.py`, `runtime_manager.py`) prevent horizontal scaling across multiple backend worker processes or server instances.
- **Recommendation for v1.0 / v2.0**: Migrate all ephemeral execution state and event broadcasting to Redis or PostgreSQL with advisory locking, and replace local JSON workspace metadata tracking with transactional database tables.
