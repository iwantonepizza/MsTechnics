from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypedDict


class DeliveryResult(TypedDict):
    succeeded: bool
    error: str | None
    response: dict[str, Any]


class BaseChannel(ABC):
    name: str

    @abstractmethod
    def can_deliver(self, recipient) -> bool:
        ...

    @abstractmethod
    def deliver(self, recipient, text: str, *, context: dict | None = None) -> DeliveryResult:
        ...
