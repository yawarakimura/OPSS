from ocr_engines.base import OCRResult
from ocr_engines.utils import extract_times
from app.services.ocr_pipeline import OCRPipeline


def test_extract_times_colon_and_four_digits():
    assert extract_times('08:36 1200 13：00 18.05') == ['08:36', '12:00', '13:00', '18:05']


def test_double_engine_agreement():
    t = OCRResult(engine='Tesseract', success=True, times=['08:30', '18:00'])
    p = OCRResult(engine='PaddleOCR', success=True, times=['08:30', '18:00'])
    result = OCRPipeline._judge(1, t, p)
    assert result.status == '自動確定'
    assert result.times == ['08:30', '18:00']


def test_single_engine_candidate():
    t = OCRResult(engine='Tesseract', success=True, times=['08:30', '18:00'])
    p = OCRResult(engine='PaddleOCR', success=False)
    result = OCRPipeline._judge(1, t, p)
    assert result.status == '採用候補'
