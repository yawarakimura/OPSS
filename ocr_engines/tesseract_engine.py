from __future__ import annotations

from typing import Any

from ocr_engines.base import OCREngine, OCRResult
from ocr_engines.utils import extract_times, preprocess_for_time_ocr


class TesseractEngine(OCREngine):
    name = "Tesseract"

    def __init__(self) -> None:
        self._reason: str | None = None
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self._pytesseract = pytesseract
        except Exception as exc:
            self._pytesseract = None
            self._reason = str(exc)

    @property
    def available(self) -> bool:
        return self._pytesseract is not None

    @property
    def unavailable_reason(self) -> str | None:
        return self._reason

    def recognize(self, image: Any) -> OCRResult:
        if not self.available:
            return OCRResult(engine=self.name, error=self._reason or "利用できません")
        try:
            processed = preprocess_for_time_ocr(image)
            data = self._pytesseract.image_to_data(
                processed,
                config="--psm 6 -c tessedit_char_whitelist=0123456789:",
                output_type=self._pytesseract.Output.DICT,
            )
            words: list[str] = []
            confidences: list[float] = []
            for text, conf in zip(data.get("text", []), data.get("conf", [])):
                text = str(text).strip()
                try:
                    score = float(conf)
                except (TypeError, ValueError):
                    score = -1
                if text:
                    words.append(text)
                if score >= 0:
                    confidences.append(score / 100.0)
            raw_text = " ".join(words)
            times = extract_times(raw_text)
            confidence = sum(confidences) / len(confidences) if confidences else 0.0
            return OCRResult(
                text=raw_text,
                confidence=confidence,
                engine=self.name,
                success=bool(times),
                times=times,
                raw=data,
            )
        except Exception as exc:
            return OCRResult(engine=self.name, error=str(exc))
