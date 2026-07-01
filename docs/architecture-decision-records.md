# Architecture Decision Records (ADR) Ledger

## What is an ADR?
An Architecture Decision Record (ADR) captures a single, significant architectural decision along with its context and consequences. This ledger ensures future contributors understand *why* Agent OS is designed the way it is.

---

## ADR 1: The Modular Monolith

**Context:** 
Agent OS requires distinct subsystems (Requirements, Planning, Execution, State). Initially, these were tightly coupled scripts. We considered breaking them into independent microservices.

**Decision:**
We will adopt a **Modular Monolith** architecture based around "Engines". All code runs in a single process/server, but domain boundaries are strictly enforced via Engine Contracts.

**Why?**
Microservices introduce immense operational complexity (network latency, distributed transactions, deployment overhead) that Agent OS does not yet need. A Modular Monolith gives us the boundary enforcement of microservices while maintaining the deployment simplicity of a single Python app. If the Builder Engine needs to scale horizontally in the future, the boundary already exists to extract it into a worker.

---

## ADR 2: Deterministic Logic Before AI

**Context:**
Building software requires hundreds of small decisions. Initially, we relied on the LLM to make all of these decisions via massive prompts.

**Decision:**
Agent OS will push as much logic as possible into deterministic, rule-based systems (e.g., Engineering Standards Engine, Requirement Validator) *before* invoking an LLM.

**Why?**
LLMs are non-deterministic, expensive, and subject to hallucination. By using standard Python logic to constrain the problem space, we provide the LLM with a narrow, highly structured prompt. This dramatically increases the reliability and consistency of the generated code.

---

## ADR 3: Workflow Orchestration vs. Choreography

**Context:**
As new engines were added, they started calling each other directly (Choreography). The `ArchitectService` called the `Planner`, which called the `Builder`.

**Decision:**
We will introduce a central **Workflow Orchestrator**. Engines will never call each other directly.

**Why?**
Point-to-point choreography leads to spaghetti execution paths where error handling and retries are impossible to coordinate. A central Orchestrator allows us to see the exact execution graph, pause workflows, resume from failures, and test engines in complete isolation.

---

## ADR 4: The Provider Abstraction Layer

**Context:**
The system relied on hardcoded HTTP calls to a local Ollama instance (`llm_service.py`). 

**Decision:**
We will implement an `LLMProvider` abstract interface. All engines will request capabilities (Chat, Structured Output) against this interface, never against a specific provider.

**Why?**
The AI landscape is moving too fast to lock into a single provider. Users may want to use local models (Ollama/Llama 3) for privacy, or cloud models (Claude 3.5/GPT-4o) for maximum intelligence. This abstraction allows hot-swapping models via configuration without rewriting any Engine logic.
