from enum import Enum
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field


class EngineStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    DEFERRED = "DEFERRED"


class EngineError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class WorkflowContext(BaseModel):
    """
    Context passed to every engine during execution.
    Contains telemetry identifiers and shared read-only state.
    """
    trace_id: str
    workflow_id: str
    conversation_id: str | None = None
    workspace_id: str | None = None
    shared_memory: dict[str, Any] = Field(default_factory=dict)


class EngineRequest(BaseModel):
    """
    Standardized request sent to an Engine by the Orchestrator.
    """
    payload: dict[str, Any]


T = TypeVar("T")


class EngineResult(BaseModel, Generic[T]):
    """
    Standardized response returned by an Engine.
    """
    status: EngineStatus
    payload: T | None = None
    errors: list[EngineError] = Field(default_factory=list)

    @classmethod
    def success(cls, payload: T) -> "EngineResult[T]":
        return cls(status=EngineStatus.SUCCESS, payload=payload)

    @classmethod
    def failure(cls, errors: list[EngineError]) -> "EngineResult[T]":
        return cls(status=EngineStatus.FAILURE, errors=errors)
