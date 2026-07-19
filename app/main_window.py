from __future__ import annotations

import csv
import traceback
from pathlib import Path
from typing import Iterable

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QHeaderView,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.services.document_loader import DocumentLoader, DocumentLoadError
from app.widgets.image_viewer import ImageViewer
from app.services.ocr_pipeline import OCRPipeline, DayOCRResult
from app.workers.ocr_worker import OCRWorker


TABLE_HEADERS = [
    "日",
    "出勤",
    "外出",
    "戻り",
    "退勤",
    "Tesseract",
    "PaddleOCR",
    "判定",
    "備考",
]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.current_file: Path | None = None
        self.document_loader = DocumentLoader()
        self.ocr_pipeline = OCRPipeline()
        self.ocr_thread: QThread | None = None
        self.ocr_worker: OCRWorker | None = None

        self.setWindowTitle("OPSS v0.1 GUI β2")
        self.resize(1440, 900)
        self.setMinimumSize(1050, 700)

        self._build_actions()
        self._build_menu()
        self._build_toolbar()
        self._build_central_ui()
        self._build_statusbar()
        self._apply_style()

        self._populate_empty_rows()
        self.log("OPSSを起動しました。")
        for engine_status in self.ocr_pipeline.engine_status():
            self.log(engine_status)
        self.statusBar().showMessage("準備完了")

    # ---------- UI構築 ----------

    def _build_actions(self) -> None:
        self.open_action = QAction("開く", self)
        self.open_action.setShortcut(QKeySequence.Open)
        self.open_action.setStatusTip("タイムカードPDFまたは画像を開く")
        self.open_action.triggered.connect(self.open_document)

        self.run_ocr_action = QAction("OCR実行", self)
        self.run_ocr_action.setShortcut("Ctrl+R")
        self.run_ocr_action.setStatusTip("OCRを実行する")
        self.run_ocr_action.triggered.connect(self.run_ocr)

        self.export_csv_action = QAction("CSV保存", self)
        self.export_csv_action.setShortcut(QKeySequence.SaveAs)
        self.export_csv_action.setStatusTip("日別結果をCSVへ保存する")
        self.export_csv_action.triggered.connect(self.export_csv)

        self.clear_action = QAction("結果クリア", self)
        self.clear_action.triggered.connect(self.clear_results)

        self.exit_action = QAction("終了", self)
        self.exit_action.setShortcut(QKeySequence.Quit)
        self.exit_action.triggered.connect(self.close)

        self.about_action = QAction("OPSSについて", self)
        self.about_action.triggered.connect(self.show_about)

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("ファイル")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.export_csv_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        ocr_menu = self.menuBar().addMenu("OCR")
        ocr_menu.addAction(self.run_ocr_action)
        ocr_menu.addAction(self.clear_action)

        help_menu = self.menuBar().addMenu("ヘルプ")
        help_menu.addAction(self.about_action)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("メインツールバー", self)
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        toolbar.addAction(self.open_action)
        toolbar.addSeparator()
        toolbar.addAction(self.run_ocr_action)
        toolbar.addSeparator()
        toolbar.addAction(self.export_csv_action)
        self.addToolBar(toolbar)

    def _build_central_ui(self) -> None:
        root_splitter = QSplitter(Qt.Vertical, self)
        main_splitter = QSplitter(Qt.Horizontal, root_splitter)

        self.image_viewer = ImageViewer()
        self.image_viewer.file_dropped.connect(self.load_document)
        main_splitter.addWidget(self.image_viewer)

        self.result_table = QTableWidget(15, len(TABLE_HEADERS))
        self.result_table.setHorizontalHeaderLabels(TABLE_HEADERS)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.setSelectionMode(QTableWidget.SingleSelection)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.result_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.Stretch)
        self.result_table.setMinimumWidth(680)
        main_splitter.addWidget(self.result_table)

        main_splitter.setSizes([700, 740])

        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(0, 0, 0, 0)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(175)
        self.log_view.setPlaceholderText("処理ログ")
        log_layout.addWidget(self.log_view)

        root_splitter.addWidget(main_splitter)
        root_splitter.addWidget(log_container)
        root_splitter.setSizes([760, 140])

        self.setCentralWidget(root_splitter)

    def _build_statusbar(self) -> None:
        status = QStatusBar(self)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setFixedWidth(220)
        self.progress_bar.setVisible(False)
        status.addPermanentWidget(self.progress_bar)
        self.setStatusBar(status)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f3f5f7;
            }
            QToolBar {
                spacing: 8px;
                padding: 6px;
                border-bottom: 1px solid #c8ced6;
                background: #ffffff;
            }
            QTableWidget {
                background: #ffffff;
                gridline-color: #d7dce2;
                border: 1px solid #c8ced6;
                border-radius: 4px;
            }
            QHeaderView::section {
                background: #e9edf2;
                padding: 7px;
                border: 0;
                border-right: 1px solid #c8ced6;
                border-bottom: 1px solid #c8ced6;
                font-weight: 600;
            }
            QTextEdit {
                background: #171a1f;
                color: #e6edf3;
                border: 1px solid #323843;
                padding: 6px;
                font-family: Menlo, Monaco, monospace;
            }
            QStatusBar {
                background: #ffffff;
                border-top: 1px solid #c8ced6;
            }
            """
        )

    # ---------- データ ----------

    def _populate_empty_rows(self) -> None:
        for row in range(15):
            day_item = QTableWidgetItem(str(row + 1))
            day_item.setFlags(day_item.flags() & ~Qt.ItemIsEditable)
            day_item.setTextAlignment(Qt.AlignCenter)
            self.result_table.setItem(row, 0, day_item)

            for column in range(1, len(TABLE_HEADERS)):
                item = QTableWidgetItem("")
                if column == 7:
                    item.setText("未実行")
                    item.setTextAlignment(Qt.AlignCenter)
                self.result_table.setItem(row, column, item)

    def table_rows(self) -> Iterable[list[str]]:
        for row in range(self.result_table.rowCount()):
            yield [
                self.result_table.item(row, column).text()
                if self.result_table.item(row, column) is not None
                else ""
                for column in range(self.result_table.columnCount())
            ]

    # ---------- ファイル ----------

    def open_document(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "タイムカードを開く",
            "",
            "対応ファイル (*.pdf *.png *.jpg *.jpeg *.bmp *.tif *.tiff);;"
            "PDF (*.pdf);;"
            "画像 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;"
            "すべてのファイル (*)",
        )
        if filename:
            self.load_document(filename)

    def load_document(self, filename: str | Path) -> None:
        path = Path(filename)

        try:
            self.statusBar().showMessage("ファイルを読み込んでいます…")
            self.log(f"読み込み開始: {path}")

            image = self.document_loader.load_preview(path)
            self.image_viewer.set_image(image)
            self.current_file = path

            self.setWindowTitle(f"OPSS v0.1 GUI β2 — {path.name}")
            self.log(f"読み込み完了: {path.name}")
            self.statusBar().showMessage(f"読込完了: {path.name}", 5000)

        except DocumentLoadError as exc:
            self.log(f"読込エラー: {exc}")
            QMessageBox.critical(self, "ファイル読込エラー", str(exc))
            self.statusBar().showMessage("読込失敗", 5000)

        except Exception as exc:
            self.log(traceback.format_exc())
            QMessageBox.critical(
                self,
                "予期しないエラー",
                f"ファイルを読み込めませんでした。\n\n{exc}",
            )
            self.statusBar().showMessage("読込失敗", 5000)

    # ---------- OCR ----------

    def run_ocr(self) -> None:
        if self.current_file is None:
            QMessageBox.information(
                self,
                "OCR実行",
                "先にタイムカードPDFまたは画像を開いてください。",
            )
            return

        if not self.ocr_pipeline.tesseract.available and not self.ocr_pipeline.paddle.available:
            QMessageBox.warning(
                self,
                "OCRエンジン未準備",
                "TesseractとPaddleOCRのどちらも利用できません。\n"
                "requirements-beta2.txt をインストールし、Tesseract本体も確認してください。",
            )
            return

        self.run_ocr_action.setEnabled(False)
        self.open_action.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.statusBar().showMessage("OCR開始…")
        self.log(f"OCR開始: {self.current_file.name}")

        self.ocr_thread = QThread(self)
        self.ocr_worker = OCRWorker(self.ocr_pipeline, self.current_file)
        self.ocr_worker.moveToThread(self.ocr_thread)
        self.ocr_thread.started.connect(self.ocr_worker.run)
        self.ocr_worker.progress.connect(self._on_ocr_progress)
        self.ocr_worker.completed.connect(self._on_ocr_completed)
        self.ocr_worker.failed.connect(self._on_ocr_failed)
        self.ocr_worker.finished.connect(self.ocr_thread.quit)
        self.ocr_worker.finished.connect(self.ocr_worker.deleteLater)
        self.ocr_thread.finished.connect(self.ocr_thread.deleteLater)
        self.ocr_thread.finished.connect(self._on_ocr_finished)
        self.ocr_thread.start()

    def _on_ocr_progress(self, percent: int, message: str) -> None:
        self.progress_bar.setValue(percent)
        self.statusBar().showMessage(message)

    def _on_ocr_completed(self, results: object) -> None:
        for result in results:
            if isinstance(result, DayOCRResult):
                self._set_day_result(result)
        confirmed = sum(1 for result in results if result.status == "自動確定")
        review = sum(1 for result in results if result.status in {"要確認", "採用候補", "手入力"})
        self.log(f"OCR完了: 自動確定 {confirmed}日 / 確認対象 {review}日")
        self.statusBar().showMessage("OCR完了。要確認行を修正してください。", 7000)

    def _set_day_result(self, result: DayOCRResult) -> None:
        row = result.day - 1
        values = (result.times + ["", "", "", ""])[:4]
        for offset, value in enumerate(values, start=1):
            self.result_table.item(row, offset).setText(value)

        tess_text = " / ".join(result.tesseract.times)
        paddle_text = " / ".join(result.paddle.times)
        self.result_table.item(row, 5).setText(tess_text)
        self.result_table.item(row, 6).setText(paddle_text)
        self.result_table.item(row, 7).setText(result.status)
        self.result_table.item(row, 8).setText(result.note)

        status_item = self.result_table.item(row, 7)
        status_item.setTextAlignment(Qt.AlignCenter)
        if result.status == "自動確定":
            status_item.setBackground(Qt.GlobalColor.lightGray)
        elif result.status in {"要確認", "採用候補"}:
            status_item.setBackground(Qt.GlobalColor.yellow)
        else:
            status_item.setBackground(Qt.GlobalColor.red)

    def _on_ocr_failed(self, details: str) -> None:
        self.log(f"OCRエラー:\n{details}")
        QMessageBox.critical(self, "OCRエラー", details.split("\n\n", 1)[0])
        self.statusBar().showMessage("OCR失敗", 5000)

    def _on_ocr_finished(self) -> None:
        self.run_ocr_action.setEnabled(True)
        self.open_action.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.ocr_worker = None
        self.ocr_thread = None

    # ---------- CSV ----------

    def export_csv(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "OCR結果をCSV保存",
            "opss_result.csv",
            "CSV (*.csv)",
        )
        if not filename:
            return

        output_path = Path(filename)
        if output_path.suffix.lower() != ".csv":
            output_path = output_path.with_suffix(".csv")

        try:
            with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(TABLE_HEADERS)
                writer.writerows(self.table_rows())

            self.log(f"CSV保存完了: {output_path}")
            self.statusBar().showMessage(f"CSV保存完了: {output_path.name}", 5000)

        except OSError as exc:
            self.log(f"CSV保存エラー: {exc}")
            QMessageBox.critical(
                self,
                "CSV保存エラー",
                f"CSVを保存できませんでした。\n\n{exc}",
            )

    # ---------- その他 ----------

    def clear_results(self) -> None:
        answer = QMessageBox.question(
            self,
            "結果クリア",
            "入力・OCR結果をすべてクリアしますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        self.result_table.clearContents()
        self._populate_empty_rows()
        self.log("OCR結果をクリアしました。")
        self.statusBar().showMessage("結果をクリアしました", 3000)

    def log(self, message: str) -> None:
        self.log_view.append(message)

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            "OPSSについて",
            "OPSS v0.1 GUI β2\n"
            "Odagiri Payroll Support System\n\n"
            "タイムカード読取・確認・給与計算支援システム",
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        event.accept()
