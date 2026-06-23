# Agent OS: Master Analysis

## Introduction
Agent OS is an ambitious project aimed at creating a multi-agent software development system. The core vision is to allow a user to describe a project in natural language, and have a coordinated team of AI agents—acting as Architect, Planner, Builder, and Security/QA—autonomously design, scaffold, write, and review the software.

This document serves as an onboarding guide and architectural overview of the system's current state, what it excels at, where it struggles, and how it must evolve.

---

## 1. What Agent OS Is Today
Currently, Agent OS is a highly observable, event-driven orchestration engine built on FastAPI (backend) and React/Vite (frontend). It uses Local/API LLMs (like `qwen2.5-coder` and `qwen3`) to drive agent behaviors.

The system is structured as a pipeline rather than a free-flowing agent swarm. It follows a strict lifecycle:
1. **Discovery**: Gather requirements.
2. **Design**: Generate architecture and tasks.
3. **Execution**: Sequentially build files and review them.
4. **Completion**: Evaluate and archive the workspace.

---

## 2. How It Currently Works (The Architecture)

### The Agents
- **Architect**: The user-facing "CTO". It extracts requirements into a structured state (`ProjectStateManager`) and generates the final JSON architecture and project spec.
- **Planner (Orchestrator)**: Converts the Architect's JSON into discrete `Task` records. It assigns these tasks and manages the execution queue.
- **Builder**: The executor. It takes a task, reads the project spec, and uses an LLM to generate code files. It writes these files directly to the workspace directory.
- **Security**: The reviewer. It acts as a gatekeeper, scanning the Builder's output for empty files, path traversal violations, and dangerous commands (via regex). It can trigger a retry if it rejects a task.

### State and Communication
- **State Management**: Conversational state is tracked in-memory per session. Workspaces and tasks are serialized to disk (`.agentos/project.json`).
- **Communication**: The backend broadcasts real-time events (`BUILD_STARTED`, `TASK_COMPLETED`, etc.) via an `event_bus` to WebSocket channels. This gives the frontend unparalleled real-time observability into the agents' actions.

---

## 3. What It Can Do Today (Strengths)

- **Excellent User Experience**: The requirement gathering phase is natural and contextual. The real-time WebSocket feedback makes the autonomous build process transparent and engaging.
- **Robust Scaffolding**: It reliably creates proper folder structures, manifests, and READMEs.
- **Resilient Pipelines**: Through background jobs and fallback templates, a build will usually finish and yield a basic project skeleton, even if the LLM encounters errors.
- **Basic Security Isolation**: Path security prevents agents from writing malicious code outside of the designated workspace.

---

## 4. What Prevents It from Being Fully Autonomous (Weaknesses)

To become a true autonomous developer, Agent OS must address several core limitations:

1. **Coarse Task Granularity**: The Planner creates tasks that are too large (e.g., "Build the backend"). The Builder LLM is forced to generate too much code in one shot, leading to hallucinated context and truncated files.
2. **Lack of True Sandboxed Compilation**: The Security agent relies on static analysis and regex. Agents cannot run the code they write. Without seeing compiler errors or test failures, the Builder cannot effectively debug its own output.
3. **In-Memory Volatility**: The heavy reliance on in-memory dictionaries for state tracking means the system is not yet horizontally scalable and is vulnerable to server restarts.
4. **Rigid Pipeline Flow**: Agents do not collaborate dynamically; they operate in a strict assembly line. The Builder cannot ask the Architect for clarification mid-build.

---

## 5. What It Should Become (The Roadmap)

The path forward requires shifting from a rigid assembly line to a dynamic, feedback-driven environment. 

1. **Near Term (Phases 1-2)**: Focus on task micro-management. Teach the Planner to break down tasks into component-level work. Enforce API contract generation *before* UI or backend implementation.
2. **Mid Term (Phases 3-4)**: Implement sandboxed execution. Allow agents to run `npm run dev` or `pytest`, read the console errors, and iteratively fix the code. Introduce the ability to open and edit existing codebases using vector indexing or AST manipulation.
3. **Long Term (Phases 5-6)**: Enable true multi-agent collaboration frameworks where agents share a global memory space, debate implementations, and eventually manage the full deployment and monitoring lifecycle of applications.

---
*End of Master Analysis.*
