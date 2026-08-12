"""Feeds live camera frames to QML via the image://preview/... URL scheme."""

from __future__ import annotations

from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider


class PreviewImageProvider(QQuickImageProvider):
    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._image = QImage(1, 1, QImage.Format.Format_RGB888)

    def set_image(self, image: QImage) -> None:
        self._image = image

    def requestImage(self, id: str, size, requestedSize) -> QImage:
        image = self._image
        if size is not None:
            size.setWidth(image.width())
            size.setHeight(image.height())
        return image
