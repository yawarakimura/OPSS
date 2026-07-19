# OPSS v0.1 GUI β2

## 追加された機能

- GUIの「OCR実行」から実際にOCRを開始
- Tesseract / PaddleOCR ダブルエンジン構造
- 15日分の日別行を横罫線から自動切り出し
- 横罫線検出失敗時の均等分割フォールバック
- 時刻を `HH:MM` に正規化
- 判定ルール
  - 両者一致: 自動確定
  - 一方だけ成功: 採用候補
  - 不一致: 要確認
  - 両方失敗: 手入力
- OCRを別スレッドで実行し、GUIの停止を防止
- 進捗表示・エンジン状態・エラーログ

## 導入

```bash
cd ~/OPSS
source .venv/bin/activate
python -m pip install -r requirements-beta2.txt
```

macOSでTesseract本体が未導入の場合:

```bash
brew install tesseract
```

起動:

```bash
python app/main.py
```

## PaddleOCRについて

PaddleOCRが未導入でもTesseract単独で動作します。その場合は判定が「採用候補」になります。
PaddleOCRは環境が整ってから追加できます。
