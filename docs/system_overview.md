# Agent OS System Overview

## 1. How Architect works
The Architect agent serves as the user-facing orchestrator for requirement gathering and system design.
- **Requirement Extraction**: As the user chats, it uses a mix of rule-based keyword extraction and LLM inference to incrementally build up the project requirements (e.g., project name, frontend, backend, target audience).
- **State Evaluation**: It evaluates the `ProjectStateManager` after each message to determine the "Progress" and "Confidence Score". 
- **Architecture Generation**: Once enough context is gathered, it prompts a high-level LLM (e.g., `qwen3:14b`) to generate an architecture JSON, which includes the tech stack, major components, and a task breakdown. A `spec_engine` also generates a project specification file.
- **Approval**: It presents the architecture to the user. Once the user says "approve", it creates the workspace and routes the tasks to the Planner/Orchestrator.

## 2. How Planner works
While there is a dedicated `PlannerAgent` module, the logical planning function currently happens at the intersection of the Architect's final output and the `build_orchestrator`.
- **Task Conversion**: The Planner component converts the high-level architecture tasks (from the JSON `task_breakdown`) into executable `Task` objects in the system.
- **Task Enrichment**: It enriches the task descriptions with the project context from the specification.
- **Agent Assignment**: It assigns each task to the appropriate agent (e.g., Builder Agent, Security Agent, or Head Agent) based on keyword routing.

## 3. How Builder works
The Builder Agent is the executor that generates the actual files and code.
- **Execution**: The `build_orchestrator` assigns a pending task to the Builder.
- **LLM Generation**: The Builder uses a coding LLM (`qwen2.5-coder:7b`) and provides it with the project spec, architecture, task description, and the existing file structure. The LLM is instructed to return a JSON array containing file paths and file contents.
- **Fallback Mechanism**: If the LLM fails, the Builder falls back to generating standard boilerplate code using predefined project templates.
- **File System**: It writes the generated files to the active workspace on disk.
- **Validation Layer**: The Builder performs a basic check to ensure the output files exist, are not empty, and that basic imports resolve.

## 4. How Security works
The Security Agent acts as an automated reviewer that validates the Builder's output.
- **Trigger**: Runs immediately after the Builder marks a task as "Completed".
- **Static Checks**: It verifies that the generated files exist and are not empty.
- **Vulnerability Scanning**: It uses regex patterns to scan for dangerous commands (e.g., `eval()`, `exec()`, `rm -rf /`, `os.system`).
- **Path Isolation**: It ensures no files were written outside the designated workspace boundary.
- **LLM Code Review**: If static checks pass, it uses the LLM to inspect the code for missing imports, broken routes, or syntactical errors.
- **Outcome**: If approved, the orchestrator moves to the next task. If rejected, the task is reset to "Pending" and the Builder retries (up to a configured `MAX_RETRIES`).

## 5. How state is stored
- **Project State**: Conversational state and project requirements are stored in memory via the `ProjectStateManager` (a singleton dictionary keyed by `conversation_id`).
- **Job & Workspace State**: Asynchronous build jobs are tracked by the `job_manager`. Workspace metadata and Tasks are managed by `workspace_service` and `task_service` (currently persisting in-memory or in local flat files depending on the service implementation).
- **Manifests**: State is persisted on disk in the project directory under `.agentos/project.json` and a `build_report.json`.

## 6. How projects are created
- The user approves an architecture proposal.
- The `workspace_service` creates a new workspace record and generates a path for the project.
- The `build_orchestrator` initiates the build pipeline asynchronously.
- The Orchestrator injects foundational tasks (`Create Project Folder`, `Create Base Structure`, `Create README.md`, `Create Project Manifest`) into the queue.
- The Builder executes these foundational tasks to set up the physical directory structure.

## 7. How files are generated
- The Builder Agent receives a task and formats a prompt containing the specification, architecture, and current folder tree.
- The LLM responds with a structured JSON format containing the `path` and `content` for each required file.
- The Builder intercepts this JSON, validates the paths against the workspace root (path security), and writes the content to disk.

## 8. How task assignment works
- During task creation, a simple heuristic (`_route_task_to_agent`) looks at the keywords in the task title. 
- Words like "build", "frontend", or "database" route to the Builder.
- Words like "test", "security", or "review" route to Security.
- The `build_orchestrator` pulls tasks sequentially. It loops through them, handing them to the Builder to execute and then to Security to review.

## 9. How the frontend communicates with the backend
- **REST APIs**: The frontend uses FastAPI endpoints for standard actions (e.g., `/architect/chat`, `/build/start`, `/tasks/create`).
- **WebSockets**: The frontend maintains active WebSocket connections (`/ws/activity`, `/ws/agents`, `/ws/tasks`, `/ws/workspaces`, `/ws/build`) which stream real-time updates pushed by the backend's `event_bus`. This ensures the UI reflects agent statuses, build progress, and new tasks instantly without polling.
