# Planner Deep-Dive Analysis — Agent OS v2

The Planner subsystem (`planner_agent.py`, `task_decomposer.py`, `requirement_extractor.py`, and `spec_engine.py`) serves as the architectural brain of Agent OS. It bridges abstract user vision with atomic engineering tasks. This audit evaluates its stage-by-stage pipelines, task granularity, dependency graphs, and missing capabilities.

---

## 1. Pipeline Stage Audits

### Requirement Extraction (`requirement_extractor.py`)
- **Mechanism**: Analyzes user conversation turns during Architect sessions to extract structured features, user personas, and stack constraints.
- **Evaluation**: Computes a cumulative `confidence_score` (0 to 100%). It enforces a threshold of ≥75% before permitting transition to formal architectural specification.
- **Strength**: Prevents premature code generation on vague prompts.
- **Weakness**: Keyword-heavy evaluation can sometimes artificially inflate confidence scores when users repeat generic terms without clarifying technical depth.

### Architecture Generation (`spec_engine.py`)
- **Mechanism**: Synthesizes extracted requirements into a standardized JSON specification containing `tech_stack` and `major_components`.
- **Evaluation**: Provides a clear separation of concerns (Frontend vs. Backend vs. Database).
- **Weakness**: Static prompt structures do not dynamically adapt to unconventional project typologies (e.g., browser extensions, CLI tools, embedded scripts).

### Task Decomposition & Micro-Task Planning (`task_decomposer.py`)
- **Mechanism**: Takes the JSON architecture specification and converts each major component into executable tasks.
- **Evaluation**: Assigns sequential IDs (`task-1`, `task-2`) and generates explicit dependency lists (`depends_on: ["task-1"]`).

---

## 2. Evaluation of Planning Capabilities

### Task Quality & Granularity
- **Current State**: Tasks tend to map 1-to-1 with `major_components`. For example, a component named "User Authentication" becomes a single task: "Implement User Authentication".
- **Critique**: Granularity is often too coarse. A single task asking to implement authentication requires building DB schemas, API routes, JWT middlewares, and React UI forms. This overloads the Builder agent's context window and leads to partial or scaffolding-only code generation.

### Duplicate Prevention
- **Current State**: `task_decomposer.py` relies on the LLM prompt instructions ("Do not generate duplicate tasks") rather than post-processing deduplication algorithms.
- **Critique**: While semantic duplication is rare on initial generation, subsequent re-planning or incremental additions often create overlapping tasks (e.g., "Create header" vs "Build navbar").

### Dependency Generation & Task Ordering
- **Current State**: Builds a directed acyclic graph (DAG) where task $N$ typically depends on $N-1$ or on foundational setup tasks (`task-1`).
- **Critique**: Dependency chains are often strictly linear rather than parallelizable. For instance, frontend UI tasks and backend API routing tasks could run concurrently once database models are built, but the current planner serializes them.

---

## 3. Missing Capabilities

### 1. Dynamic Granularity Tuning
The planner lacks an automated recursive decomposition loop. If a generated task exceeds a complexity threshold (e.g., estimated lines of code > 200), the planner should automatically sub-divide it into smaller sub-tasks ("Create DB User Model" -> "Build Auth API Endpoint" -> "Create Login UI Modal").

### 2. Interface Contract Generation
Tasks currently lack formal API contract definitions (OpenAPI specs, GraphQL schemas, or TypeScript interfaces) passed between dependent tasks. Frontend builder tasks often guess backend route payload structures.

### 3. Acceptance Criteria & Test Case Definition
Tasks are generated with descriptive instructions but lack verifiable acceptance criteria (e.g., "POST /login must return 200 OK with JWT token"). Adding structured criteria is essential for enabling automated QA agent loops.
