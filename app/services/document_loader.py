from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QImage


class DocumentLoadError(RuntimeError):
    pass


class DocumentLoader:
    IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}

    def load_preview(self, path: Path) -> QImage:
        if not path.exists():
            raise DocumentLoadError(f"ファイルが見つかりません。\n{path}")

        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return self._load_pdf_first_page(path)

        if suffix in self.IMAGE_SUFFIXES:
            return self._load_image(path)

        raise DocumentLoadError(
            "対応していないファイル形式です。\n"
            "PDF、PNG、JPEG、BMP、TIFFを使用してください。"
        )

    def _load_image(self, path: Path) -> QImage:
        image = QImage(str(path))
        if image.isNull():
            raise DocumentLoadError(f"画像を読み込めませんでした。\n{path}")
        return image

    def _load_pdf_first_page(self, path: Path) -> QImage:
        try:
            import pypdfium2 as pdfium
        except ImportError as exc:
            raise DocumentLoadError(
                "PDF表示には pypdfium2 が必要です。\n"
                "仮想環境で次を実行してください。\n\n"
                "python -m pip install pypdfium2"
            ) from exc

        try:
            pdf = pdfium.PdfDocument(str(path))
            if len(pdf) == 0:
                raise DocumentLoadError("PDFにページがありません。")

            page = pdf[0]
            bitmap = page.render(scale=2.0)
            pil_image = bitmap.to_pil().convert("RGB")
            data = pil_image.tobytes("raw", "RGB")

            qimage = QImage(
                data,
                pil_image.width,
                pil_image.height,
                pil_image.width * 3,
                QImage.Format_RGB888,
            ).copy()

            page.close()
            pdf.close()

            if qimage.isNull():
                raise DocumentLoadError("PDFの画像化に失敗しました。")

            return qimage

        except DocumentLoadError:
            raise
        except Exception as exc:
            raise DocumentLoadError(
                f"PDFを読み込めませんでした。\n{path}\n\n{exc}"
            ) from exc
