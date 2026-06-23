# Current Weaknesses of Agent OS

While the foundation is strong, several architectural and implementation limitations currently prevent Agent OS from being a fully reliable autonomous development system.

## 1. Task Granularity
- **Too Coarse**: The Planner currently breaks down projects into 5-8 high-level tasks (e.g., "Build frontend shell", "Build backend API"). 
- **Impact**: This forces the Builder LLM to attempt to generate massive amounts of code across multiple files in a single turn. This frequently hits context window limits, leading to truncated files, hallucinated imports, or generic placeholder code.

## 2. Builder & Project Generation Quality
- **Single-Shot Vulnerability**: The Builder relies heavily on single-shot JSON generation. If the LLM produces malformed JSON or hallucinates file paths, the task fails.
- **Lack of Iteration**: While there is an "Autonomous Improvement Loop" (Sprint 4), it is rudimentary. The Builder doesn't incrementally write, compile, and fix code. It guesses the whole feature, and if it fails, the orchestrator just retries the same prompt up to `MAX_RETRIES`.
- **Template Fallback**: When generation fails entirely, the system falls back to hardcoded React/FastAPI templates, meaning the user gets a generic boilerplate instead of their requested application.

## 3. Error Handling and Feedback Loops
- **Superficial Security Review**: The Security Agent relies heavily on static regex checks (e.g., checking for `eval` or `rm -rf`). Its LLM-based code review only looks for basic missing imports. 
- **Missing Sandboxed Execution**: The system does not actually compile the code, run a linter (like ESLint or Ruff), or execute unit tests. Without compiler/runtime feedback, the LLM cannot effectively debug its own output.

## 4. State Management
- **In-Memory Volatility**: The `ProjectStateManager`, `build_orchestrator` active tasks, and `job_manager` state are currently stored in memory (`dict`). If the FastAPI server restarts, all active conversational state and build tracking are lost.
- **File-based Persistence**: Workspaces and Tasks are stored in flat JSON files (`project.json`). While this works for prototypes, it will lead to race conditions and data corruption under high concurrency.

## 5. Scalability
- **Sequential Bottleneck**: The `build_orchestrator` processes tasks strictly sequentially. It cannot execute a frontend task and a backend task in parallel.
- **LLM Rate Limiting**: Firing large prompts containing the entire project structure and spec repeatedly for every task is highly inefficient and expensive. Context management needs optimization (e.g., RAG or localized file embeddings) to scale to larger codebases.
