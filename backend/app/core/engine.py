from abc import ABC, abstractmethod
from typing import Any

from app.core.models import EngineRequest, EngineResult, WorkflowContext


class AgentEngine(ABC):
    """
    Base contract for all subsystems in Agent OS.
    Engines are stateless domain processors.
    """

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Unique identifier for the engine."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Semantic version of the engine."""
        pass

    @abstractmethod
    def execute(self, request: EngineRequest, context: WorkflowContext) -> EngineResult[Any]:
        """
        The core execution loop for this engine.
        
        Args:
            request: The specific payload required to do the work.
            context: Read-only context containing trace IDs and shared memory.
            
        Returns:
            EngineResult: Standardized success/failure response.
        """
        pass
