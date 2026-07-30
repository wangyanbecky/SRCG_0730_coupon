"""Provider abstractions and stable provider error types."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping, Sequence


class ProviderError(RuntimeError):
    """Base error for text provider failures."""


class ProviderAuthenticationError(ProviderError):
    pass


class ProviderAccessError(ProviderError):
    pass


class ProviderTimeoutError(ProviderError):
    pass


class ProviderRateLimitError(ProviderError):
    pass


class ProviderModelError(ProviderError):
    pass


class ProviderContextLimitError(ProviderError):
    pass


class ProviderResponseError(ProviderError):
    pass


class TextProvider(ABC):
    @property
    @abstractmethod
    def available(self) -> bool:
        """Whether the provider is configured for text generation."""

    @property
    @abstractmethod
    def status(self) -> Mapping[str, Any]:
        """Return non-secret provider status information."""

    @abstractmethod
    def converse(
        self,
        messages: Sequence[Mapping[str, Any]],
        max_tokens: int | None = None,
    ) -> str:
        """Return generated text for a conversation."""

    @abstractmethod
    def list_text_models(self) -> list[dict[str, Any]]:
        """Return foundation models supporting text output."""
