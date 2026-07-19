# OPSS v0.1 GUI β1

## 含まれる機能

- PySide6メイン画面
- PDF・画像ファイル選択
- ドラッグ＆ドロップ
- PDF先頭ページのプレビュー
- 1日〜15日の編集可能なOCR結果表
- 処理ログ
- CSV保存
- Tesseract / PaddleOCR接続用の入口

## 既存OPSSへ配置

このZIP内のファイルをOPSSプロジェクト直下へコピーします。

想定構成:

```text
OPSS/
├─ app/
│  ├─ main.py
│  ├─ main_window.py
│  ├─ services/
│  │  └─ document_loader.py
│  └─ widgets/
│     └─ image_viewer.py
├─ ocr_engines/
├─ tests/
└─ requirements-gui.txt
```

## インストール

```bash
cd ~/OPSS
source .venv/bin/activate
python -m pip install -r requirements-gui.txt
```

## 起動

```bash
python app/main.py
```

## Gitへ保存

```bash
git add app requirements-gui.txt README_GUI_BETA1.md
git commit -m "Add OPSS GUI beta1"
git push
```

## 次工程

GUIの「OCR実行」を、既存のTesseract・PaddleOCRエンジンへ接続する。
