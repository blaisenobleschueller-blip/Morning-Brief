from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class FetchResult:
    source_name: str
    content: str
    success: bool
    error: str | None = None


class BaseFetcher(ABC):
    @abstractmethod
    def fetch(self) -> FetchResult:
        ...
