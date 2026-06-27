# Builder Deep-Dive Analysis — Agent OS v2

The Builder persona (`builder_service.py` & `build_orchestrator.py`) is the core engine responsible for synthesizing code from architectural task blueprints. This audit deep-dives into its operational mechanics, prompt construction, file write workflows, error handling, root causes for scaffolding anomalies, and performance bottlenecks.

---

## 1. Work Reception & Task Comprehension

### How Work is Received
1. The `build_orchestrator.py` continuously monitors the workspace task graph.
2. When a task's prerequisites are marked `Completed`, the orchestrator pulls the task object from state.
3. The orchestrator invokes `builder_service.build_task()`, passing the task metadata along with project architectural context.

### How Builder Understands Tasks
The Builder derives comprehension from three primary contextual layers:
- **Task Specifics**: The exact `title` and detailed natural-language `description` generated during planning decomposition.
- **Global Architecture**: The JSON blueprint outlining `tech_stack` (e.g., React, FastAPI, SQLite) and `major_components`.
- **Existing Code Context**: Prior to generating code, Builder uses MCP tools (`file_mcp.py`) to query existing workspace contents, reading `package.json`, `requirements.txt`, and related shared utility headers to ensure naming consistency.

---

## 2. Prompt Assembly & Generation Mechanics

### How Prompts are Assembled
The Builder constructs a massive system prompt divided into rigid operational zones:
```text
[Identity & Constraints]
"You are an expert software developer. Generate complete, production-ready code. Do not use placeholders or ellipses."

[Project Specifications]
Project Name: <name>
Tech Stack: <tech_stack>
Architecture Overview: <architecture>

[Current Task]
Title: <task.title>
Specification: <task.description>

[Existing Workspace Context]
Files present: <list of existing file paths>
Snippet preview of related imports: <content>

[Output Format Instructions]
"Return a valid JSON object mapping file paths to complete code content."
```

### How Files are Generated
The LLM evaluates the prompt and generates a structured JSON payload representing the files required to satisfy the task:
```json
{
  "files": [
    {
      "path": "src/components/Navbar.jsx",
      "content": "import React from 'react';\n\nexport default function Navbar() { ... }"
    }
  ]
}
```

---

## 3. File Writing & Failure Handling

### How Generated Files are Written
1. **JSON Parsing**: `builder_service.py` extracts the `files` array from the LLM response string.
2. **Path Sanitization**: Each relative `path` is passed to `path_security.py` to verify it does not attempt directory traversal out of `./workspace/<id>/`.
3. **MCP File Creation**: Invokes `file_mcp.write_file()`, which creates parent directories automatically if missing and overwrites target files with the new content.
4. **Broadcast Notification**: Emits a `FILE_CREATED` or `FILE_UPDATED` envelope over the `/ws/build` channel.

### How Failures are Handled
- **JSON Malformation**: If the LLM produces invalid JSON (e.g., unescaped quotes inside code strings), the Builder catches `json.JSONDecodeError` and triggers one automatic retry with error formatting instructions.
- **Write Errors / Security Blocks**: Catch blocks intercept filesystem permissions or path security violations, logging a critical error and setting task status to `Failed`.
- **Diagnostic Routing**: Failed tasks pass execution logs into `FailureDiagnostics.jsx` for user review.

---

## 4. Root Cause Analysis: Scaffolding-Only Generation

A critical known issue in automated coding runtimes is that simple projects sometimes result in barebones scaffolding (e.g., empty `index.html` or blank shell structures) rather than fully fleshed-out functional apps. In Agent OS, this stems from three interlocking causes:

1. **Underspecified Task Granularity in Planner**: When a user submits a simple prompt like "Build a todo app", the Planner often generates only 1 or 2 high-level tasks (e.g., "Setup project structure"). Because the Builder strictly obeys task boundaries, it generates exact boilerplate and terminates, awaiting a follow-up feature task that was never created.
2. **Token Economy & Output Truncation Avoidance**: LLMs naturally optimize output lengths. If prompted to generate an entire multi-component application in a single generation response, the model will often generate placeholder structures or shells to avoid hitting maximum token output ceiling limits.
3. **Absence of Mandatory Verification Loops**: Without an automated runtime evaluation step (QA persona) to assert that the generated UI contains functional DOM elements and logic, the system accepts structural boilerplate as a successful completion.

---

## 5. Identified Bottlenecks

### 1. Synchronous I/O During Multi-File Generation
Writing multiple files sequentially through MCP overhead blocks the async event loop during large batch task outputs.

### 2. Context Window Bloat
As the workspace grows, feeding existing file previews into the Builder prompt rapidly consumes context tokens, increasing API latency and billing costs.

### 3. Lack of Incremental Diffing
The Builder currently regenerates entire file contents even for minor single-line modifications, wasting tokens and risking unintended regression of existing code in large files.
