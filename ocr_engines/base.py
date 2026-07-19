from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class OCRResult:
    text: str = ""
    confidence: float = 0.0
    engine: str = ""
    success: bool = False
    error: str | None = None
    raw: Any = None
    times: list[str] = field(default_factory=list)


class OCREngine(ABC):
    name = "OCR"

    @property
    @abstractmethod
    def available(self) -> bool:
        raise NotImplementedError

    @property
    def unavailable_reason(self) -> str | None:
        return None

    @abstractmethod
    def recognize(self, image: Any) -> OCRResult:
        """PIL Image または画像パスを読み取り、OCR結果を返す。"""
        raise NotImplementedError
