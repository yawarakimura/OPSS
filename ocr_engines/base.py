from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class OCRResult:
    text: str
    confidence: float
    engine: str
    success: bool
    error: str | None = None


class OCREngine(ABC):
    @abstractmethod
    def recognize(self, image_path: str | Path) -> OCRResult:
        """画像を読み取り、OCR結果を返す"""
        raise NotImplementedError