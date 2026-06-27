# Technical Debt Audit — Agent OS v2

This document catalogs code smells, duplicated logic, hardcoded values, missing abstractions, and temporary fixes across the Agent OS codebase. Items are prioritized by severity to guide refactoring efforts prior to the Version 1.0 production release.

---

## 1. Severity Ranking

### 🚨 Critical Severity (Must Fix Before v1.0)
1. **Unbounded Log Array Buffer Growth in UI**:
   - *Location*: `Activity.jsx`, `TerminalPanel.jsx`
   - *Issue*: Streamed logs append indefinitely without slicing old items, risking browser memory crashes on long-running builds.
2. **Synchronous File Operations Blocking Async Loop**:
   - *Location*: `file_mcp.py`, `builder_service.py`
   - *Issue*: Standard `open()` disk writes are executed synchronously inside `async def` endpoints, degrading API server throughput during multi-file builds.

### ⚠️ High Severity
3. **Hardcoded Model Configurations**:
   - *Location*: `llm_service.py`, `config.py`
   - *Issue*: Default model strings (`Gemini 3.1 Pro`) and timeouts are embedded in code rather than routed through a dynamic Model Registry abstraction.
4. **Multiplexed WebSocket Handshake Overhead**:
   - *Location*: `App.jsx`, `websocket_manager.py`
   - *Issue*: Client initializes 6 separate TCP WebSocket sockets rather than establishing a single multiplexed channel with topic envelopes.
5. **Absence of AST / LSP Syntax Validation Prior to Write**:
   - *Location*: `builder_service.py`
   - *Issue*: Generated code is written directly to disk without passing through an automated syntax linter or AST checker, allowing malformed code drop-ins.

### 🟨 Medium Severity
6. **Duplicated UI Primitive Styling Logic**:
   - *Location*: `StatusPill.jsx` vs `Badge.jsx`, `ProgressBar.jsx` vs `SystemMonitor.jsx`
   - *Issue*: Two pairs of UI components duplicate identical CSS styling classes and animation keyframe logic.
7. **Coarse Task Granularity in Planner**:
   - *Location*: `task_decomposer.py`
   - *Issue*: 1-to-1 mapping of major architectural components to tasks creates overly complex prompts for the Builder agent.

### 🟩 Low Severity
8. **Redundant REST Fetch on Mount**:
   - *Location*: `Tasks.jsx`, `Workspaces.jsx`
   - *Issue*: Components fire `GET` requests upon mounting even when WebSocket subscriptions already maintain up-to-date local state.
9. **Inconsistent Typography Units**:
   - *Location*: `Sandbox.jsx`
   - *Issue*: Older sandbox layout containers use hardcoded pixel values (`14px`) rather than design system variables (`--text-sm`).
