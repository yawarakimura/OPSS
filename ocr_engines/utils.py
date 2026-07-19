from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

_TIME_PATTERN = re.compile(r"(?<!\d)([0-2]?\d)\s*[:：.;]\s*([0-5]\d)(?!\d)")
_FOUR_DIGIT_PATTERN = re.compile(r"(?<!\d)([0-2]\d)([0-5]\d)(?!\d)")


def as_pil(image: Any) -> Image.Image:
    if isinstance(image, Image.Image):
        return image
    return Image.open(Path(image)).convert("RGB")


def preprocess_for_time_ocr(image: Any, scale: int = 3) -> Image.Image:
    pil = as_pil(image).convert("L")
    pil = ImageOps.autocontrast(pil)
    pil = ImageEnhance.Contrast(pil).enhance(2.2)
    pil = pil.resize((pil.width * scale, pil.height * scale))
    pil = pil.filter(ImageFilter.SHARPEN)
    # 罫線や薄い印字に強い単純二値化。文字色を黒に統一する。
    return pil.point(lambda p: 255 if p > 175 else 0)


def normalize_text(text: str) -> str:
    table = str.maketrans({
        "O": "0", "o": "0", "I": "1", "l": "1", "|": "1",
        "：": ":", ";": ":", ".": ":", "，": ":", ",": ":",
    })
    return " ".join(text.translate(table).replace("\n", " ").split())


def extract_times(text: str, limit: int = 4) -> list[str]:
    normalized = normalize_text(text)
    found: list[tuple[int, str]] = []
    occupied: list[tuple[int, int]] = []

    for match in _TIME_PATTERN.finditer(normalized):
        hour, minute = int(match.group(1)), int(match.group(2))
        if 0 <= hour <= 23:
            found.append((match.start(), f"{hour:02d}:{minute:02d}"))
            occupied.append(match.span())

    for match in _FOUR_DIGIT_PATTERN.finditer(normalized):
        if any(start <= match.start() < end for start, end in occupied):
            continue
        hour, minute = int(match.group(1)), int(match.group(2))
        if 0 <= hour <= 23:
            found.append((match.start(), f"{hour:02d}:{minute:02d}"))

    found.sort(key=lambda item: item[0])
    values: list[str] = []
    for _, value in found:
        if not values or values[-1] != value:
            values.append(value)
        if len(values) >= limit:
            break
    return values
