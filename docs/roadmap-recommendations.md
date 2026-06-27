# Strategic Roadmap Recommendations — Agent OS v2

Based on the comprehensive architectural audit, this roadmap defines the prioritized strategic milestones required to transition Agent OS from a local desktop development prototype into a stable Version 1.0 release, and eventually into an enterprise-grade Version 2.0 platform.

---

## 1. Prioritized Strategic Milestones

### Milestone 1: Builder Intelligence & Recursive Task Decomposition (Highest Priority)
- **Why Come Next**: The audit revealed that simple prompts often generate scaffolding-only builds because the Planner emits overly coarse tasks. Enhancing Builder intelligence with recursive sub-task decomposition ensures that complex components are automatically broken down into atomic, highly focused generation prompts.
- **Architectural Scope**: Upgrade `task_decomposer.py` with AST-aware complexity estimation and introduce intermediate validation loops inside `builder_service.py`.

### Milestone 2: Automated QA Integration & Self-Healing Loops
- **Why Come Next**: Code generation without automated verification requires manual debugging. Implementing an autonomous QA persona completes the core execution pipeline by running unit tests, checking syntax, and feeding bug tracebacks directly back to the Builder.
- **Architectural Scope**: Integrate Playwright/Puppeteer into `sandbox_service.py` and create a dedicated `qa_agent.py` orchestrator subscribing to completed build events.

### Milestone 3: Project Editing & Incremental Diffing
- **Why Come Next**: Currently, modifying existing projects requires full file rewrites. Implementing semantic diff generation saves LLM tokens and prevents accidental regressions in established code.
- **Architectural Scope**: Extend `file_mcp.py` and `git_mcp.py` to support unified diff patching (`patch` command application) rather than full file overwrites.

### Milestone 4: Centralized Model Registry & Multi-Provider Fallback
- **Why Come Next**: Tightly coupling core builders to a single API provider creates vendor lock-in and vulnerability to rate limits (`429 Too Many Requests`). A Model Registry unlocks cost optimization and local open-source model execution.
- **Architectural Scope**: Create `backend/app/models/registry.py` routing inference requests based on task capability profiles (`REASONING`, `SPEED`, `LOCAL`).

### Milestone 5: Version 1.0 Production Readiness Release
- **Why Come Next**: Consolidating Milestones 1–4 resolves all Critical and High technical debt items, stabilizing the platform for general developer adoption.
- **Architectural Scope**: Implement multiplexed WebSocket channels, virtualized log scrolling in UI panels, and asynchronous external task queueing (Celery/Redis).

---

## 2. Version 2.0 Enterprise Expansion Milestones

### Milestone 6: Plugin & Extension System
- **Objective**: Allow third-party developers to contribute custom MCP tool adapters (e.g., AWS S3 deployment, Figma design import, Jira ticket sync).

### Milestone 7: One-Click Cloud Deployment
- **Objective**: Integrate direct automated container deployment pipelines pushing generated sandboxes directly to Vercel, Railway, AWS ECS, or Docker Hub.
