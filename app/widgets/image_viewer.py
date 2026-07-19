from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QImage, QPixmap, QResizeEvent
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget


SUPPORTED_SUFFIXES = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tif",
    ".tiff",
}


class ImageViewer(QWidget):
    file_dropped = Signal(str)

    def __init__(self) -> None:
        super().__init__()

        self._pixmap: QPixmap | None = None
        self.setAcceptDrops(True)

        self.image_label = QLabel(
            "タイムカードPDFまたは画像を\nここへドラッグ＆ドロップ\n\n"
            "または上部の「開く」を押してください"
        )
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(500, 600)
        self.image_label.setStyleSheet(
            """
            QLabel {
                color: #66717f;
                background: #ffffff;
                border: 2px dashed #aeb7c2;
                border-radius: 7px;
                font-size: 17px;
                padding: 24px;
            }
            """
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignCenter)
        scroll.setWidget(self.image_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    def set_image(self, image: QImage) -> None:
        self._pixmap = QPixmap.fromImage(image)
        self._refresh_scaled_image()

    def clear_image(self) -> None:
        self._pixmap = None
        self.image_label.clear()

    def _refresh_scaled_image(self) -> None:
        if self._pixmap is None or self._pixmap.isNull():
            return

        available = self.size()
        target_width = max(300, available.width() - 36)
        target_height = max(400, available.height() - 36)

        scaled = self._pixmap.scaled(
            target_width,
            target_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._refresh_scaled_image()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        urls = event.mimeData().urls()
        if not urls:
            event.ignore()
            return

        path = Path(urls[0].toLocalFile())
        if path.suffix.lower() in SUPPORTED_SUFFIXES:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if not urls:
            return

        path = Path(urls[0].toLocalFile())
        if path.suffix.lower() in SUPPORTED_SUFFIXES:
            self.file_dropped.emit(str(path))
            event.acceptProposedAction()
