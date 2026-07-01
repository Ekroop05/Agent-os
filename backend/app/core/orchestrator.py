from abc import ABC, abstractmethod
from typing import Any

from app.core.models import EngineResult, WorkflowContext


class WorkflowOrchestrator(ABC):
    """
    Abstract interface for coordinating engines.
    Engines do not call each other; the Orchestrator routes data between them.
    """

    @abstractmethod
    def start_workflow(self, workflow_name: str, initial_payload: dict[str, Any]) -> str:
        """
        Starts a workflow execution.
        Returns the Trace ID associated with this run.
        """
        pass

    @abstractmethod
    def get_status(self, trace_id: str) -> dict[str, Any]:
        """
        Retrieves the current execution status and progress of a workflow.
        """
        pass
