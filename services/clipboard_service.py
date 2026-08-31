"""Clipboard helpers."""

from __future__ import annotations

from PySide6.QtGui import QGuiApplication, QPixmap


class ClipboardService:
    @staticmethod
    def copy_image(pixmap: QPixmap) -> None:
        clipboard = QGuiApplication.clipboard()
        clipboard.setPixmap(pixmap)
