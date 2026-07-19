from ocr_engines.base import OCREngine, OCRResult
from ocr_engines.paddle_engine import PaddleEngine
from ocr_engines.tesseract_engine import TesseractEngine

__all__ = ["OCREngine", "OCRResult", "TesseractEngine", "PaddleEngine"]
