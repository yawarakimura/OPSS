from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from app.services.ocr_pipeline import OCRPipeline


class OCRWorker(QObject):
    progress = Signal(int, str)
    completed = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, pipeline: OCRPipeline, source: Path) -> None:
        super().__init__()
        self.pipeline = pipeline
        self.source = source

    @Slot()
    def run(self) -> None:
        try:
            results = self.pipeline.run(
                self.source,
                lambda percent, message: self.progress.emit(percent, message),
            )
            self.completed.emit(results)
        except Exception as exc:
            import traceback
            self.failed.emit(f"{exc}\n\n{traceback.format_exc()}")
        finally:
            self.finished.emit()
