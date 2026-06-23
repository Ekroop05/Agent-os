# HTTP 400 Error Analysis

This document identifies all possible HTTP 400 errors thrown by the backend that could impact the Approval Workflow and other related systems.

## 1. Architecture Not Generated
- **File**: `backend/app/services/architect_service.py`
- **Function**: `approve(self, conversation_id: str)`
- **Condition**: `if not state["architecture_generated"]:`
- **Message**: "Architecture has not been generated yet"
- **Context**: Thrown if the user tries to approve a project before the architect agent has finished gathering requirements and generated the architecture output.

## 2. Project Already Approved
- **File**: `backend/app/services/architect_service.py`
- **Function**: `approve(self, conversation_id: str)`
- **Condition**: `if state["approved"]:`
- **Message**: "Project has already been approved"
- **Context**: Thrown if an approval request is sent for a conversation that has already been approved.

## 3. Project Root is Required
- **File**: `backend/app/services/workspace_service.py`
- **Function**: `update_settings(self, project_root: str)`
- **Condition**: `if not project_root or not project_root.strip():`
- **Message**: "Project root is required"
- **Context**: Thrown when setting the sandbox root path to an empty value.

## 4. Invalid Workspace Path
- **File**: `backend/app/services/workspace_service.py`
- **Function**: `normalize_project_path(self, path: str)`
- **Condition**: `if normalized != root and not normalized.startswith(f"{root}/"):`
- **Message**: "Workspace path must be inside configured project root"
- **Context**: Thrown when trying to create a workspace path that breaks out of the configured global sandbox root.

## 5. Planner - Architecture Not Generated
- **File**: `backend/app/services/planner_agent.py`
- **Function**: `approve(self, conversation_id: str)`
- **Condition**: `if not state["architecture_generated"]:`
- **Message**: "Architecture has not been generated yet"
- **Context**: Same as the architect service, but for the deprecated/alternative planner agent.

## 6. Planner - Project Already Approved
- **File**: `backend/app/services/planner_agent.py`
- **Function**: `approve(self, conversation_id: str)`
- **Condition**: `if state["approved"]:`
- **Message**: "Project has already been approved"
- **Context**: Same as the architect service, but for the deprecated/alternative planner agent.
