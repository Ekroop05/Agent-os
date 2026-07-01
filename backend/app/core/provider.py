from abc import ABC, abstractmethod
from typing import Any, Iterator, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class Message(BaseModel):
    role: str
    content: str


class ChatResponse(BaseModel):
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMProvider(ABC):
    """
    Abstract interface for interacting with LLM APIs.
    Isolates Agent OS engines from specific model providers (Ollama, Anthropic, Google).
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g., 'ollama', 'anthropic')"""
        pass

    @abstractmethod
    def chat_completion(
        self, messages: list[Message], model: str, **kwargs: Any
    ) -> ChatResponse:
        """Standard text generation."""
        pass

    @abstractmethod
    def stream_completion(
        self, messages: list[Message], model: str, **kwargs: Any
    ) -> Iterator[str]:
        """Streamed text generation."""
        pass

    @abstractmethod
    def structured_completion(
        self, messages: list[Message], schema: type[T], model: str, **kwargs: Any
    ) -> T:
        """Generate structured JSON output matching the Pydantic schema."""
        pass
