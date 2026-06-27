# Agent Audit — Agent OS v2

This document audits the AI agent personas operating inside Agent OS: **Architect**, **Builder**, **Security**, and the planned future **QA Integration**. Each persona is analyzed across its core architectural dimensions.

---

## 1. Architect Agent (`architect_service.py`)

### Responsibilities
Act as a technical co-founder. Engages the user in conversational dialogue to extract product vision, clarify ambiguities, define target technical stacks, and produce formal system architecture specs.

### Inputs & Outputs
- **Inputs**: User conversational strings, conversation ID, existing partial project status.
- **Outputs**: Clarifying questions, updated requirements progress (0–100%), confidence score, and JSON architecture specifications (`tech_stack`, `major_components`, `task_breakdown`).

### Dependencies & Model Usage
- **Dependencies**: `requirement_extractor.py`, `spec_engine.py`, `project_state.py`.
- **Model Usage**: Uses `Gemini 3.1 Pro (High)`. Relies heavily on system prompting to maintain a professional, analytical tone and enforce JSON output formatting when synthesizing blueprints.

### Execution Lifecycle & State Management
1. Activated upon HTTP request to `/api/architect/chat`.
2. Evaluates intent pre-filters (`classify_intent`).
3. Updates conversational history in session state.
4. When approved, transitions project phase to `Project Ready` and hands control to Planner.

### Weaknesses & Extension Opportunities
- **Weaknesses**: Stateless LLM calls require sending full conversation transcripts repeatedly, consuming high token counts on long brainstorming sessions.
- **Extension Opportunities**: Implement semantic vector summarization to condense older context turns into compact architectural memory blocks.

---

## 2. Builder Agent (`builder_service.py`)

### Responsibilities
Act as an autonomous software developer. Converts atomic task descriptions into production-ready code files written directly to the workspace filesystem.

### Inputs & Outputs
- **Inputs**: Task object (`title`, `description`), architecture blueprint, workspace file inventory retrieved via MCP.
- **Outputs**: Generated code content, file path mappings, build execution log entries.

### Dependencies & Model Usage
- **Dependencies**: `build_orchestrator.py`, `file_mcp.py`, `path_security.py`.
- **Model Usage**: Uses `Gemini 3.1 Pro`. Instructed via strict system prompts to generate complete code drop-ins without placeholder comments (`// TODO: implement logic here`).

### Execution Lifecycle & State Management
1. Invoked asynchronously by `build_orchestrator.py`.
2. Reads existing context files via MCP.
3. Streams generation tokens or returns parsed code blocks.
4. Updates task state from `Running` to `Completed` (or `Failed`).

### Weaknesses & Extension Opportunities
- **Weaknesses**: Lack of multi-file cross-referencing memory during single-shot task generation can lead to slight naming mismatches between imports across separate builds.
- **Extension Opportunities**: Introduce an intermediate AST (Abstract Syntax Tree) verification step or language server protocol (LSP) integration before writing files to disk.

---

## 3. Security Agent (`security_service.py` & `command_security.py`)

### Responsibilities
Act as a DevSecOps guardian. Enforces sandbox boundaries, prevents directory traversal attacks, and blocks destructive terminal commands during code build and execution.

### Inputs & Outputs
- **Inputs**: File paths requested for write/read, shell strings proposed for execution.
- **Outputs**: Boolean authorization permit (`True`/`False`), security violation exception logs.

### Dependencies & Model Usage
- **Dependencies**: Regular expression engines, OS path normalization libraries (`os.path.abspath`).
- **Model Usage**: Currently deterministic rule-based logic (regex lists of forbidden commands like `rm -rf /`, `mkfs`, fork bombs). Does not consume LLM tokens.

### Execution Lifecycle & State Management
1. Intercepts every MCP call synchronously before disk or shell execution occurs.
2. Raises immediate `SecurityViolationError` stopping build loops upon breach attempt.
3. Stateless execution across requests.

### Weaknesses & Extension Opportunities
- **Weaknesses**: Pure regex/rule-based filtering can be bypassed by complex shell obfuscation techniques.
- **Extension Opportunities**: Upgrade into a hybrid LLM-assisted security auditor that analyzes semantic intent of shell scripts before authorization.

---

## 4. Future QA Integration (Planned)

### Responsibilities
Act as an automated test engineer and reviewer. Validate generated build outputs by running unit tests, linting code, checking visual layout formatting, and executing automated browser testing.

### Inputs & Outputs
- **Inputs**: Completed workspace directory, task acceptance criteria, runtime sandbox URL.
- **Outputs**: QA pass/fail score, automated bug reports, regression test logs, patch suggestions.

### Planned Dependencies & Model Usage
- **Dependencies**: `sandbox_service.py`, `terminal_mcp.py`, headless browser runtimes (Playwright/Puppeteer).
- **Model Usage**: Will utilize vision-capable models (`Gemini 3.1 Pro Vision`) to analyze visual UI rendering screenshots against design specifications.

### Planned Lifecycle & Extension Opportunities
- **Lifecycle**: Triggers automatically when all tasks in a workspace transition to `Completed`.
- **Extension Opportunities**: Automated self-healing loops where QA failures re-queue bug fix tasks directly back to the Builder agent without requiring human intervention.
