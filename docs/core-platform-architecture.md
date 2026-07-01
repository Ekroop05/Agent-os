# Core Platform Architecture

## Overview
Agent OS is transitioning from an AI wrapper into a **Software Engineering Platform**. The Core Platform Architecture defines logical boundaries between subsystems. Moving forward, the system is structured as a **Modular Monolith** where distinct "Engines" own specific domains of responsibility.

## Logical Engines and Subsystems

### 1. Requirements & Discovery
- **Architect Engine:** Manages the conversational flow with the user to discover project goals.
- **Requirement Intelligence Engine:** (Planned) Analyzes raw prompts semantically to extract intent, constraints, and dependencies, wrapping them in a confidence model.
- **Requirement Extractor:** (Legacy) Rule-based extraction of simple keywords.

### 2. Engineering & Planning
- **Engineering Planner Engine:** Breaks down the intelligent requirement object into a structured software architecture and discrete execution tasks.
- **Engineering Standards Engine:** Injects non-negotiable coding conventions, folder structures, and security best practices into tasks based on the chosen tech stack.
- **Spec Engine:** Manages the immutable `spec.json` representing the final contract of what is being built.

### 3. Execution & Building
- **Builder Engine (Execution):** The core autonomous loop that writes code, runs terminal commands, and resolves errors.
- **Builder Intelligence Engine:** Retrieves localized context and structures prompts dynamically to prevent context-window explosion during execution.
- **Task Decomposer:** Breaks coarse architectural tasks into atomic, actionable steps for the Builder.

### 4. Workspace & Environment
- **Workspace Engine:** Manages the physical directories, project metadata, and file structures.
- **Runtime Manager:** Manages background processes, ports, and development servers (e.g., `npm run dev`) isolated per workspace.
- **Sandbox Engine:** Ensures the workspace operates within restricted directories and standardizes path normalization.

### 5. Platform State & Telemetry
- **Project State Manager:** Owns the mutable state of the conversation and requirement gathering phase.
- **Activity Stream / Timeline Engine:** Maintains an immutable ledger of all system events, errors, and task completions.
- **Job Engine:** (Planned/Scaffolded) Manages asynchronous execution statuses across the system.

## Future Architecture Goal
Currently, these services invoke one another directly (e.g., Architect calls Requirement Extractor directly, Planner calls Spec Engine directly). The future state replaces point-to-point coupling with a **Workflow Orchestrator**, where Engines act as isolated processors adhering to strict contracts.
