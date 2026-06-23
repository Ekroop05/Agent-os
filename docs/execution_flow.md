# Agent OS Execution Flow

This document traces the complete execution flow for a standard user request.

## Example Request
**User:** *"Build a coffee shop website called Brew"*

---

### 1. User Input & Extraction
↓ **User input via Frontend Chat UI**
↓ **API Endpoint**: `POST /architect/chat`
↓ **Architect Service**: `architect_service.chat(message)`
- Extractor parses "Brew" as the `project_name` and "coffee shop website" as the `project_type` & `theme`.
- `project_state_manager` recalculates progress. Progress goes up, but requirements are not fully complete.
- Architect uses LLM (`_conversational_reply`) to ask follow-up questions (e.g., "Do you want a backend?", "Who is the target audience?").

*(Several chat turns occur until requirements are complete)*

---

### 2. Architecture Generation
↓ **Requirements Complete**
- Architect automatically triggers `_generate_architecture(state)`.
- The LLM generates the JSON architecture (tech stack, major components, task breakdown).
- `spec_engine.generate_spec(state)` runs to create the comprehensive project specification.
↓ **Architect Service**: Replies with the high-level architecture proposal and asks for approval.

---

### 3. Approval & Workspace Creation
↓ **User replies "approve"**
↓ **API Endpoint**: `POST /architect/approve`
↓ **Architect Service**: `architect_service.approve()`
- `workspace_service.create()` initializes the workspace (e.g., `/workspaces/brew`).
- `spec_engine.write_spec()` writes the spec to disk.

---

### 4. Task Creation (Planner Logic)
↓ **Inside `architect_service.approve()`**
- Iterates through `architecture["task_breakdown"]`.
- `spec_engine.enrich_task_description()` adds specific context to each task.
- `task_service.create()` creates the tasks and assigns them to agents (mostly "Builder Agent") via `_route_task_to_agent()`.
- Event bus broadcasts `TASK_CREATED`.

---

### 5. Build Orchestration Start
↓ **Build Pipeline Trigger**
- `build_orchestrator.start_pipeline(workspace.id, architecture)` is called.
- `job_manager` creates an asynchronous background job so the build survives disconnects.
- `_run_pipeline()` begins. It creates foundational tasks ("Create Project Folder", "Create Base Structure", "Create README.md").

---

### 6. File Generation (Builder Execution)
↓ **Task Loop**: `task_service.next_pending_task()` retrieves the first task.
↓ **Builder Service**: `builder_service.execute_task()`
- Marks task as `Running`.
- Retrieves the project `spec` and `architecture`.
- Prompts the `qwen2.5-coder:7b` LLM with the task description, architecture, spec, and current folder structure.
- LLM returns a JSON payload containing file paths and source code.
- Builder uses `validate_write_path()` to ensure files are safely within the workspace.
- Builder writes the files to disk.
- Builder runs basic validation (checks if files are empty, basic imports).
- Task marked as `Completed`. Output files are logged.

---

### 7. Security Review
↓ **Orchestrator routes completed Builder task to Security**
↓ **Security Service**: `security_service.review_task()`
- Verifies files exist and have content.
- Scans files against `DANGEROUS_PATTERNS` regex (e.g., `os.system`, `rm -rf`).
- Uses `validate_command` to ensure no malicious commands are executed in generated scripts.
- Asks LLM to review code for broken imports or missing components.
- If approved, orchestrator moves to the next task.
- If rejected, orchestrator bumps the retry counter and resets the task to `Pending` for the Builder to try again.

---

### 8. Finalization & Autonomous Improvement
↓ **All Tasks Processed**
- `evaluation_engine.evaluate()` runs to check project completion and quality.
- If gaps are found, it generates *improvement tasks* and feeds them back into the loop (up to 3 improvement cycles).
- When the final evaluation passes (or max cycles reached), the orchestrator generates a `build_report.json`.
- The workspace status is set to `Completed` and it is archived.
- Event bus broadcasts `BUILD_COMPLETED` to the frontend.
