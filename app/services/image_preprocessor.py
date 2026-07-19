"""OCR向けの画像前処理を提供する。"""

from __future__ import annotations

import cv2
import numpy as np
from numpy.typing import NDArray


ImageArray = NDArray[np.uint8]


class ImagePreprocessor:
    """OCRエンジンから独立した画像前処理を行う。"""

    def preprocess(self, image: ImageArray) -> ImageArray:
        """一連の前処理を画像に適用する。

        Args:
            image: OpenCV形式の入力画像。

        Returns:
            前処理済みの二値画像。
        """
        processed = self.grayscale(image)
        processed = self.denoise(processed)
        processed = self.enhance(processed)
        processed = self.deskew(processed)
        processed = self.threshold(processed)
        return processed

    def grayscale(self, image: ImageArray) -> ImageArray:
        """画像をグレースケールへ変換する。

        Args:
            image: OpenCV形式の入力画像。

        Returns:
            グレースケール画像。
        """
        if image.ndim == 2:
            return image.copy()
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def threshold(self, image: ImageArray) -> ImageArray:
        """大津の二値化を画像に適用する。

        Args:
            image: グレースケール画像。

        Returns:
            二値化された画像。
        """
        _, thresholded = cv2.threshold(
            image,
            0,
            255,
            cv2.THRESH_BINARY | cv2.THRESH_OTSU,
        )
        return thresholded

    def denoise(self, image: ImageArray) -> ImageArray:
        """メディアンフィルターで小さなノイズを除去する。

        Args:
            image: 前処理対象の画像。

        Returns:
            ノイズを低減した画像。
        """
        return cv2.medianBlur(image, 3)

    def deskew(self, image: ImageArray) -> ImageArray:
        """画像の傾き補正を行うための拡張ポイントを提供する。

        Args:
            image: 前処理対象の画像。

        Returns:
            傾き補正後の画像。現時点では入力画像のコピー。
        """
        return image.copy()

    def enhance(self, image: ImageArray) -> ImageArray:
        """ヒストグラム平坦化でコントラストを高める。

        Args:
            image: グレースケール画像。

        Returns:
            コントラストを補正した画像。
        """
        return cv2.equalizeHist(image)
