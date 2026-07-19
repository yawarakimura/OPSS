from __future__ import annotations

from typing import Any

import numpy as np

from ocr_engines.base import OCREngine, OCRResult
from ocr_engines.utils import as_pil, extract_times


class PaddleEngine(OCREngine):
    name = "PaddleOCR"

    def __init__(self) -> None:
        self._reason: str | None = None
        self._ocr = None
        try:
            from paddleocr import PaddleOCR
            # バージョン差を避けるため、広く互換性のある最小引数にする。
            try:
                self._ocr = PaddleOCR(use_angle_cls=False, lang="en", show_log=False)
            except TypeError:
                self._ocr = PaddleOCR(use_angle_cls=False, lang="en")
        except Exception as exc:
            self._reason = str(exc)

    @property
    def available(self) -> bool:
        return self._ocr is not None

    @property
    def unavailable_reason(self) -> str | None:
        return self._reason

    def recognize(self, image: Any) -> OCRResult:
        if not self.available:
            return OCRResult(engine=self.name, error=self._reason or "利用できません")
        try:
            array = np.asarray(as_pil(image).convert("RGB"))
            output = self._ocr.ocr(array, cls=False)
            texts: list[str] = []
            scores: list[float] = []
            # PaddleOCR 2.x の一般的な入れ子形式を再帰的に拾う。
            def walk(value: Any) -> None:
                if isinstance(value, (list, tuple)):
                    if (
                        len(value) == 2
                        and isinstance(value[0], str)
                        and isinstance(value[1], (int, float))
                    ):
                        texts.append(value[0])
                        scores.append(float(value[1]))
                    else:
                        for child in value:
                            walk(child)
                elif isinstance(value, dict):
                    for key in ("rec_texts", "texts"):
                        if key in value:
                            texts.extend(str(x) for x in value[key])
                    for key in ("rec_scores", "scores"):
                        if key in value:
                            scores.extend(float(x) for x in value[key])
            walk(output)
            raw_text = " ".join(texts)
            times = extract_times(raw_text)
            confidence = sum(scores) / len(scores) if scores else 0.0
            return OCRResult(
                text=raw_text,
                confidence=confidence,
                engine=self.name,
                success=bool(times),
                times=times,
                raw=output,
            )
        except Exception as exc:
            return OCRResult(engine=self.name, error=str(exc))
