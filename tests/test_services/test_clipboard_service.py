"""Tests for clipboard service."""

from __future__ import annotations

from PySide6.QtGui import QPixmap

from services.clipboard_service import ClipboardService


class TestClipboardService:
    def test_copy_image_places_pixmap_on_clipboard(
        self, qapp, sample_pixmap, mock_clipboard
    ):
        ClipboardService.copy_image(sample_pixmap)

        clipboard_pixmap = mock_clipboard.pixmap()

        assert not clipboard_pixmap.isNull()
        assert clipboard_pixmap.size() == sample_pixmap.size()

    def test_copy_overwrites_previous_clipboard_content(
        self, qapp, sample_pixmap, mock_clipboard
    ):
        first = sample_pixmap.copy(0, 0, 100, 100)
        second = sample_pixmap.copy(100, 100, 200, 200)

        ClipboardService.copy_image(first)
        ClipboardService.copy_image(second)

        assert mock_clipboard.pixmap().size() == second.size()
