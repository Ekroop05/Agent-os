# Migration Plan: Requirement Intelligence Engine

> [!WARNING]
> This subsystem introduces a massive shift in how requirements are modeled. To ensure 0% downtime and 100% backward compatibility with the active Builder and Planner systems, it MUST be rolled out in isolated, non-breaking phases.

## 1. Migration Phases

### Phase 1: Shadow Intelligence (Read-Only)
In this phase, the Intelligence Engine operates silently in the background, logging its conclusions but NOT affecting the user experience.

1. **Implement `RequirementObject` Schema:** Introduce the new schema in `schemas.py` alongside the existing state dict.
2. **Build the Intelligence Engine (RIE):** Implement the intent, evidence, and confidence logic.
3. **Shadow Execution:** Call the RIE *after* the `RequirementExtractor`. Log the resulting `RequirementObject` and the `readiness_score` to a secure telemetry file (e.g., `logs/intelligence_shadow.log`).
4. **Validation:** Analyze the logs over 100+ project generation runs to compare the rule-based output vs. the RIE output. Ensure the confidence scoring is accurately predicting true missing information.

*User Impact:* Zero.
*System Impact:* Slight increase in CPU/Latency during extraction due to shadow LLM calls.

### Phase 2: Active Validation & Question Generation
Once the RIE's logic is proven reliable in shadow mode, we activate it to drive the Architect's conversation flow.

1. **Activate Validator:** Replace the hardcoded `project_state_manager.unanswered_unasked_fields` logic with the new Validator's prioritized missing-fields list.
2. **Activate Question Generator:** Override the Architect's generic `_conversational_reply` prompt with the new context-aware Question Generator.
3. **State Mapping:** The `RequirementObject` is still flattened back into the simple `state` dictionary before it reaches the `PlannerAgent`, ensuring the Planner continues to receive the exact data format it expects.

*User Impact:* The Architect asks significantly better, fewer, and contextual questions. It correctly rejects contradictions.
*System Impact:* The conversation logic is vastly improved, but downstream planning and building remain untouched.

### Phase 3: Planner Integration
The final phase exposes the rich `RequirementObject` directly to the Planner, unlocking massive quality improvements in task generation.

1. **Expose Object:** Pass the full `RequirementObject` (including confidence and evidence) to the `PlannerAgent` inside `state["intelligence_profile"]`.
2. **Update Prompts:** Update the Planner's system prompts to utilize the evidence when generating architecture descriptions, ensuring tasks directly trace back to user quotes.
3. **Deprecate Old Extractor:** Once the `RequirementObject` fully drives the Planner, the old rule-based `RequirementExtractor` can be safely removed or downgraded to a simple pre-parsing utility.

*User Impact:* Generated plans are highly deterministic, strictly aligned with user quotes, and architecturally sound.
*System Impact:* Complete architectural migration achieved without breaking legacy builds.

## 2. Risk Analysis & Mitigation

### Technical Risks
- **Latency Spikes:** Introducing LLM calls in the RIE could slow down the chat experience.
  - *Mitigation:* Use a fast, small-parameter model (e.g., Llama 3 8B or fine-tuned classification layer) for the RIE instead of the heavy Architect LLM.
- **Hallucinations in Evidence:** The LLM might invent quotes that the user never said.
  - *Mitigation:* The prompt must strictly enforce extracting literal substrings. A post-processing script should assert that `evidence` strings actually exist in the `conversation_history` using `str.find()`. If not, discard the evidence.

### Backward Compatibility Risks
- **Planner Dependency Breakage:** If the flattened state dictionary loses keys that the Planner relies on (e.g., `frontend` becoming a nested object), generation will crash.
  - *Mitigation:* Maintain strict unit tests on the `to_legacy_dict()` mapping function. The output of Phase 2 MUST perfectly match the output of the legacy extractor.

### Failure Modes
- **LLM Timeout:** If the RIE fails, what happens?
  - *Mitigation:* Graceful degradation. If the RIE times out, immediately fall back to the output of the rule-based `RequirementExtractor` and bypass validation. The user gets the legacy experience instead of an error message.

## 3. Summary of Implementation Work Required (For Next Phase)
- **Files to Modify:**
  - `app/schemas.py` (Add RequirementObject)
  - `app/services/architect_service.py` (Inject RIE into the flow)
  - `app/state/project_state.py` (Update missing field logic)
- **Files to Create:**
  - `app/services/requirement_intelligence.py`
  - `app/services/requirement_validator.py`
  - `tests/test_requirement_intelligence.py`
- **Implementation Complexity:** High. Requires careful state management and prompt engineering.
- **Go/No-Go:** Architecture is sound and safely phased. Approved for implementation.
