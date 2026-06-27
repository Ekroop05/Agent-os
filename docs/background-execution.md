# Background Execution Audit — Agent OS v2

This document audits threading, async execution models, navigation lifecycle effects, and UI dependencies during lengthy code generation builds. It evaluates why historical builds stopped upon page navigation and recommends architecture improvements for robust background processing.

---

## 1. Execution & Threading Model

### Asyncio Event Loop (`main.py`)
The backend operates on an asynchronous uvicorn event loop. HTTP REST requests and WebSocket connections share this loop. Lightweight non-blocking operations (e.g., querying status, reading JSON manifests) execute directly on the main thread.

### Background Job Threads (`job_manager.py`)
When a build is initiated (`/api/build/start`), `job_manager.py` spawns a dedicated Python background thread (`threading.Thread` or `asyncio.create_task`) to execute `build_orchestrator.run_build()`. This ensures long-running LLM generation loops do not block concurrent HTTP traffic.

---

## 2. Navigation Effects & UI Dependency Analysis

### Why Builds Stopped During Navigation (Historical Root Cause)
Prior to the Stabilization Sprint, navigating away from the Architect or Workspaces page caused builds to appear halted or abort prematurely due to two architectural flaws:

1. **Component-Coupled Execution State**: The frontend trigger for proceeding to sequential tasks was tied inside React `useEffect` hooks in `Workspaces.jsx`. When the user navigated away, the component unmounted, destroying the local polling or acknowledgment timer needed to advance the build step.
2. **WebSocket Lifecycle Destruction**: The WebSocket listener socket was originally initialized inside individual route views. Unmounting closed the socket (`1001 Going Away`). When the backend attempted to push `FILE_CREATED` envelopes over the closed channel, broken pipe exceptions raised inside unhandled callback blocks terminated the underlying Python build thread.

### Current State (Stabilization Sprint Resolution)
- **UI Independence**: The backend execution engine (`build_orchestrator.py`) is fully decoupled from client sockets. If a WebSocket broadcast encounters a disconnected client, it silently catches `WebSocketDisconnect` and continues building on disk.
- **Persistent Global Store**: `architectStore.js` and `App.jsx` maintain global socket channels at the root DOM hierarchy, allowing page routing without severing communication.

---

## 3. Recommended Architectural Improvements (No Implementation)

To transition from a local desktop engine to a fault-tolerant enterprise server (v1.0 / v2.0), the following structural improvements are recommended:

### 1. External Task Queueing (Celery / RQ / ARQ)
Replace in-memory `job_manager.py` threads with an external worker pool backed by Redis. This isolates LLM generation execution completely from the FastAPI server process. If the API server crashes or restarts, background workers continue executing tasks uninterrupted.

### 2. Persistent Build Checkpointing
Implement transactional progress checkpoints after each generated file write. If a power loss or kernel OOM event occurs during task 14 of 20, restarting the backend should automatically resume execution from task 14 rather than restarting the entire workspace pipeline from scratch.

### 3. Server-Sent Events (SSE) Fallback
While WebSockets provide bi-directional streaming, network firewalls or VPNs often drop long-lived socket connections. Implementing SSE fallback for unidirectional build telemetry streaming will guarantee log delivery across restrictive corporate networks.
