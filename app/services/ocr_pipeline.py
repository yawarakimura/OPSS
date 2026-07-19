from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image

from ocr_engines import OCRResult, PaddleEngine, TesseractEngine


@dataclass(slots=True)
class DayOCRResult:
    day: int
    times: list[str] = field(default_factory=list)
    tesseract: OCRResult = field(default_factory=OCRResult)
    paddle: OCRResult = field(default_factory=OCRResult)
    status: str = "要確認"
    note: str = ""


class OCRPipeline:
    def __init__(self) -> None:
        self.tesseract = TesseractEngine()
        self.paddle = PaddleEngine()

    def engine_status(self) -> list[str]:
        values = []
        for engine in (self.tesseract, self.paddle):
            if engine.available:
                values.append(f"{engine.name}: 利用可能")
            else:
                values.append(f"{engine.name}: 利用不可 ({engine.unavailable_reason})")
        return values

    def run(
        self,
        source: Path,
        progress: Callable[[int, str], None] | None = None,
    ) -> list[DayOCRResult]:
        page = self._load_first_page(source)
        rows = self._split_day_rows(page, 15)
        results: list[DayOCRResult] = []
        for index, row_image in enumerate(rows, start=1):
            if progress:
                progress(int((index - 1) / 15 * 100), f"{index}日を認識中")
            tess = self.tesseract.recognize(row_image)
            paddle = self.paddle.recognize(row_image)
            results.append(self._judge(index, tess, paddle))
        if progress:
            progress(100, "OCR完了")
        return results

    @staticmethod
    def _load_first_page(source: Path) -> Image.Image:
        if source.suffix.lower() != ".pdf":
            return Image.open(source).convert("RGB")
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(str(source))
        try:
            page = pdf[0]
            bitmap = page.render(scale=3.0)
            return bitmap.to_pil().convert("RGB")
        finally:
            try:
                page.close()
            except Exception:
                pass
            pdf.close()

    def _split_day_rows(self, page: Image.Image, count: int) -> list[Image.Image]:
        """横罫線を優先して日別行を切り出し、失敗時は均等分割する。"""
        detected = self._detect_horizontal_bands(page, count)
        if detected is not None:
            return [page.crop(box) for box in detected]

        width, height = page.size
        # 一般的なタイムカードの見出し・フッターを除外するフォールバック。
        top = int(height * 0.16)
        bottom = int(height * 0.94)
        row_h = (bottom - top) / count
        left = int(width * 0.08)
        right = int(width * 0.98)
        return [
            page.crop((left, int(top + i * row_h), right, int(top + (i + 1) * row_h)))
            for i in range(count)
        ]

    @staticmethod
    def _detect_horizontal_bands(page: Image.Image, count: int) -> list[tuple[int, int, int, int]] | None:
        try:
            import cv2
        except ImportError:
            return None

        gray = np.asarray(page.convert("L"))
        inv = cv2.threshold(gray, 190, 255, cv2.THRESH_BINARY_INV)[1]
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(30, page.width // 5), 1))
        lines = cv2.morphologyEx(inv, cv2.MORPH_OPEN, kernel)
        strength = (lines > 0).sum(axis=1)
        candidates = np.where(strength > page.width * 0.30)[0]
        if len(candidates) < count + 1:
            return None

        grouped: list[int] = []
        start = previous = int(candidates[0])
        for raw in candidates[1:]:
            value = int(raw)
            if value - previous > 3:
                grouped.append((start + previous) // 2)
                start = value
            previous = value
        grouped.append((start + previous) // 2)

        # 連続する16本の線のうち、行高が最も安定する組を選ぶ。
        best: tuple[float, list[int]] | None = None
        for start_index in range(max(1, len(grouped) - count)):
            subset = grouped[start_index : start_index + count + 1]
            if len(subset) != count + 1:
                continue
            gaps = np.diff(subset)
            mean = float(np.mean(gaps))
            if mean < page.height * 0.02:
                continue
            score = float(np.std(gaps) / mean)
            if best is None or score < best[0]:
                best = (score, subset)
        if best is None or best[0] > 0.35:
            return None

        lines_y = best[1]
        left, right = int(page.width * 0.04), int(page.width * 0.99)
        boxes = []
        for top, bottom in zip(lines_y, lines_y[1:]):
            pad = max(1, int((bottom - top) * 0.05))
            boxes.append((left, top + pad, right, bottom - pad))
        return boxes

    @staticmethod
    def _judge(day: int, tess: OCRResult, paddle: OCRResult) -> DayOCRResult:
        t, p = tess.times[:4], paddle.times[:4]
        note_parts: list[str] = []

        if t and p and t == p:
            chosen, status = t, "自動確定"
        elif t and not p:
            chosen, status = t, "採用候補"
            note_parts.append("Tesseractのみ認識")
        elif p and not t:
            chosen, status = p, "採用候補"
            note_parts.append("PaddleOCRのみ認識")
        elif t and p:
            # 共通位置が多い側を初期値にし、必ず人が確認する。
            chosen, status = (t if tess.confidence >= paddle.confidence else p), "要確認"
            note_parts.append("両エンジン不一致")
        else:
            chosen, status = [], "手入力"
            note_parts.append("時刻を認識できません")

        for result in (tess, paddle):
            if result.error:
                note_parts.append(f"{result.engine}: {result.error}")

        return DayOCRResult(
            day=day,
            times=chosen,
            tesseract=tess,
            paddle=paddle,
            status=status,
            note=" / ".join(note_parts),
        )
