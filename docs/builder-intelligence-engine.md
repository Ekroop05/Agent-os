# Builder Intelligence Engine v1.0

The Builder Intelligence Engine is a critical sub-system of Agent OS designed to transform the Builder Agent from a simple LLM wrapper into a deterministic, context-aware execution engine.

## Mission
To ensure that the Builder behaves like a Senior Software Engineer: analyzing requirements, retrieving only relevant context, applying strict engineering standards, and verifying outputs before completing tasks.

## Architecture

The Builder Intelligence Engine relies on two main components within `app.services.builder_intelligence`:

1.  **Context Retrieval Engine**
2.  **Prompt Assembler**

These integrate tightly with the `builder_service.py` execution pipeline.

### Context Retrieval Engine
Instead of indiscriminately loading large chunks of the project, the Context Retrieval Engine uses the `engineering_metadata` generated during the Planning phase (specifically `expected_files.read` and `expected_files.modify`). It parses these targeted lists to load only the exact files the Builder needs to complete its task. If no metadata is present, it falls back to providing a structural directory outline.

### Prompt Assembler
The Prompt Assembler constructs a highly structured, deterministic prompt for the LLM. It pieces together:
- Project Specification (from `spec.json`)
- Project Architecture Summary
- Task Description & Acceptance Criteria
- Required Deliverables
- Engineering Standards (from `engineering_standards.py`)
- Targeted File Context (from the Context Retrieval Engine)

### Validation & Retry Pipeline
In `builder_service.py`, the builder writes the generated files and immediately runs them through `_validate_build_output`. The engine checks:
1.  Are all files specified in `required_deliverables` accounted for?
2.  Are any of the generated files empty?
3.  Are there any broken imports within the generated frontend components?

If the validation fails, the engine retries the LLM generation once, appending the validation error to the prompt for self-correction. If the retry fails, it gracefully falls back to template scaffolding.

## Execution Flow

1.  **Orchestration**: `execute_task()` receives a Task ID.
2.  **Context Loading**: `builder_intelligence.retrieve_context()` fetches relevant file contents.
3.  **Prompt Building**: `builder_intelligence.assemble_prompt()` constructs the comprehensive LLM instructions.
4.  **Generation**: LLM processes the prompt.
5.  **Write & Validate**: Files are written safely via `path_security`. `_validate_build_output` runs checks.
6.  **Retry on Failure**: If validation fails, loop back to step 4 (max 1 retry).
7.  **Finalization**: Task marked completed and events published.

## Backward Compatibility
The system is designed to degrade gracefully. If `engineering_metadata` is missing (e.g. from an older workspace or direct manual task injection), the Context Retrieval Engine falls back to the directory structure approach, and the Validation engine skips the `required_deliverables` check.
