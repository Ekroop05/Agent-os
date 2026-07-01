# Reliability Hotfix v0.8.2 — Documentation

## Overview
This hotfix addresses critical reliability issues in the Requirement Extraction pipeline. The focus of this sprint was to eliminate brittle substring regex matching, improve fallback handling (retry loops + messaging), establish better logging/exception handling, and secure the system with a comprehensive regression test suite.

Zero feature changes were introduced. The pipeline remains 100% backward compatible.

## Bugs Discovered & Fixed

### 1. Regex Substring False Positives (`requirement_extractor.py`)
- **Bug**: The rule-based extraction engine used loose regular expressions (e.g., `r"pet|dog|cat|animal"`) which aggressively matched substrings within unrelated words (e.g., "cat" within "appli**cat**ion"). This led to extreme false classifications (e.g., classifying a B2B SaaS as a Pets/Animals theme).
- **Fix**: All matching logic inside `_THEME_PATTERNS`, `_PURPOSE_PATTERNS`, `_USER_PATTERNS`, `_FEATURE_PATTERNS`, `_PROJECT_TYPE_MAP`, `_FRONTEND_PATTERNS`, `_BACKEND_PATTERNS`, and `_DATABASE_PATTERNS` was updated to explicitly wrap the patterns in word boundaries `\b(?:pattern)\b`.

### 2. Regex Pluralization Failures
- **Bug**: After enforcing word boundaries, exact-match rules broke on pluralized inputs (e.g., `\bclient\b` failed to match "clients").
- **Fix**: Refactored `_USER_PATTERNS` to gracefully support plurals natively (e.g., `r"clients?"`, `r"developers?|programmers?|engineers?"`).

### 3. Classification Specificity Ordering
- **Bug**: Patterns inside `_PROJECT_TYPE_MAP` and `deploy_map` were matched based on their order of definition in the Python dictionary. For example, "website" would match before "portfolio website", truncating the classification to "Website".
- **Fix**: The engine now dynamically sorts these dictionary mappings by string length (longest first) before matching, guaranteeing that the most specific classification pattern always takes precedence.

## Reliability Improvements

### 1. LLM Retry Logic (`architect_service.py`)
- The `_conversational_reply` and `_generate_architecture` LLM calls were notoriously brittle, immediately falling back to rule-based templates if a timeout or exception occurred.
- **Fix**: Introduced `LLM_RETRY_COUNT = 2`. The architect will automatically retry generation twice if it encounters failures (e.g., timeouts, JSON parsing errors) before giving up.

### 2. Explicit Exception Handling
- Caught and differentiated specific exceptions (e.g., `requests.exceptions.Timeout`, `requests.exceptions.ConnectionError`, `requests.exceptions.HTTPError`, `json.JSONDecodeError`, `KeyError`) inside `architect_service.py`, replacing generic `Exception` blocks. 

### 3. Enhanced Logging
- Standardized `logger.warning` traces for each LLM attempt failure, explicitly noting the retry count and failure reason.
- Standardized `logger.error` traces when the ultimate rule-based fallback is triggered, persisting the Conversation ID, Extraction State, and exact Failure Reason.

### 4. Honest Fallback Messaging
- **Bug**: The hardcoded fallback reply used to hallucinate facts when confidence was low: *"Great — so we're building a [Generic Type] with a [False Theme] theme..."*
- **Fix**: Updated `_fallback_reply` to honestly indicate uncertainty: *"I couldn't confidently determine every project detail automatically. Let's clarify a few things before continuing."*

## Testing
- Created `test_hotfix1.py` containing a full suite of unit tests.
- **Regression Tests**: Validated standard extractions for a Coffee Shop, Netflix, Hospital, Bank, CRM, Inventory System, Portfolio, AI SaaS, FlowDesk AI, Weather App, Task Manager, School Portal, Gaming Platform, Restaurant, and Social Media App.
- **Edge-Case Tests**: Validated that edge-case substrings (application, category, competitor, communicate, catalog, pedagogical) yield absolutely 0 false positives.
- **Mock Tests**: Validated the `ArchitectService` LLM retry loop behavior and architecture generation fallback paths.

## Backward Compatibility
- **Architect Conversation**: Unchanged behavior (aside from bug fixes).
- **Planner / Builder**: Entirely Unchanged.
- **UI / API**: Unchanged.
- **Project Structure**: Unchanged.

## Known Limitations
- The extraction remains purely regex-based before the LLM. It still cannot infer complex semantic meaning that falls outside of explicit, hardcoded synonyms.
- Theme mapping is strictly bound to the 20 pre-defined themes inside `_THEME_PATTERNS`. Unique concepts that don't match any aliases will default to `None`.

## Future Improvements
- **Requirement Intelligence**: Deprecate the brittle rule-based regex extractor entirely, replacing it with a localized, fast LLM intent-classification model (e.g., a fine-tuned classification layer) that handles synonyms, spelling errors, and contextual ambiguity gracefully.
- **Confidence Scoring**: Introduce a multi-stage confidence scoring matrix that weighs rule-based heuristics against LLM semantic outputs, prompting human-in-the-loop review if confidence drops below a specified threshold.
