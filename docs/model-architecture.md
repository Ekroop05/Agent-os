# Model Architecture Audit — Agent OS v2

This document audits the AI model integrations across Agent OS. It evaluates coupling between core services and specific inference providers, identifies opportunities for model abstraction, and outlines a future Model Registry architecture to support multi-provider scaling.

---

## 1. Current Model Configuration & Coupling Analysis

### Configuration State
Agent OS currently standardizes on Google DeepMind models configured via environment variables and backend global defaults:
- **Default Inference Model**: `Gemini 3.1 Pro (High)`
- **Core Wrapper**: `llm_service.py` provides a thin API client wrapper initializing Google GenAI client SDK instances.

### Tightly Coupled Services
The following services exhibit tight coupling to specific prompt formatting expectations and context limits of `Gemini 3.1 Pro`:
1. **`builder_service.py`**: Relies heavily on DeepMind-specific instruction adherence for generating multi-file JSON schemas in a single pass without markdown block corruption.
2. **`architect_service.py`**: Uses large system context window allowances (1M+ tokens) to hold extensive multi-turn conversational brainstorming logs without chunking.

### Model-Agnostic Services
The following modules do not execute direct generation and are fully model-agnostic:
- **`requirement_extractor.py`**: Can operate cleanly on smaller, faster models (e.g., `Gemini Flash` or `Claude 3.5 Sonnet`) since extraction requires low reasoning overhead.
- **`security_service.py`**: Operates on deterministic regex patterns and filesystem checks without LLM invocation.

---

## 2. Future Model Registry Architecture Recommendation

To evolve Agent OS into an enterprise-ready platform capable of running local open-source models (Ollama/Llama 3) alongside commercial APIs (OpenAI, Anthropic, Google), the codebase should migrate to a centralized **Model Registry**.

### Proposed Architecture Diagram

```text
+-----------------------------------------------------------------------------------+
|                              AGENT SERVICE COnsUMERS                              |
|   Architect Agent • Planner Agent • Builder Agent • QA Evaluation Engine          |
+-----------------------------------------------------------------------------------+
                                         │
                 Request with Task Profile (Reasoning / Speed / Cost)
                                         ▼
+-----------------------------------------------------------------------------------+
|                            MODEL REGISTRY ROUTER                                  |
|   Selects optimal provider based on task requirements, fallback tiers, & cost    |
+-----------------------------------------------------------------------------------+
                │                        │                        │
                ▼                        ▼                        ▼
      +------------------+     +------------------+     +------------------+
      |  Google GenAI    |     | Anthropic Client |     |  Local Ollama    |
      | (Gemini 3.1 Pro) |     | (Claude 3.5 Son) |     |  (Llama 3 70B)   |
      +------------------+     +------------------+     +------------------+
```

### Key Components of Proposed Registry:
1. **Task-Based Routing**: Agents request inference by capability profile (`REASONING_HEAVY`, `CODE_GENERATION_FAST`, `JSON_EXTRACTION`) rather than specifying hardcoded model names.
2. **Provider Adapters**: Standardize all inputs and outputs into a unified `ChatCompletion` interface, abstracting away provider-specific tool calling APIs.
3. **Automatic Fallback & Rate Limit Retries**: If a primary commercial model encounters `429 Too Many Requests`, the router dynamically downgrades to a secondary backup model to prevent interrupted builds.
