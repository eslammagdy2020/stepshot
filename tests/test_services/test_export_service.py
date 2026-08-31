"""Tests for image export service."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtGui import QPixmap

from services.export_service import ExportService


class TestExportService:
    def test_save_png_creates_valid_file(self, sample_pixmap, temp_image_path):
        path = temp_image_path.with_suffix(".png")
        ExportService.save_png(sample_pixmap, path)

        assert path.exists()
        assert path.stat().st_size > 0

        with Image.open(path) as image:
            assert image.format == "PNG"
            assert image.size == (640, 480)

    def test_save_jpg_creates_valid_file(self, sample_pixmap, temp_image_path):
        path = temp_image_path.with_suffix(".jpg")
        ExportService.save_jpg(sample_pixmap, path)

        assert path.exists()
        assert path.stat().st_size > 0

        with Image.open(path) as image:
            assert image.format in ("JPEG", "JPG")
            assert image.size == (640, 480)

    def test_save_png_default_format_per_prd(self, sample_pixmap, temp_image_path):
        """PRD specifies PNG as the default export format."""
        path = temp_image_path.with_suffix(".png")
        ExportService.save_png(sample_pixmap, path)
        assert path.suffix.lower() == ".png"

    def test_save_png_failure_raises(self, monkeypatch, temp_image_path):
        pixmap = QPixmap(10, 10)

        def fail_save(*_args, **_kwargs):
            return False

        monkeypatch.setattr(pixmap, "save", fail_save)

        with pytest.raises(RuntimeError, match="Failed to save PNG"):
            ExportService.save_png(pixmap, temp_image_path.with_suffix(".png"))

    def test_save_jpg_failure_raises(self, monkeypatch, temp_image_path):
        pixmap = QPixmap(10, 10)

        def fail_save(*_args, **_kwargs):
            return False

        monkeypatch.setattr(pixmap, "save", fail_save)

        with pytest.raises(RuntimeError, match="Failed to save JPG"):
            ExportService.save_jpg(pixmap, temp_image_path.with_suffix(".jpg"))

    def test_accepts_path_object(self, sample_pixmap, temp_image_path):
        path: Path = temp_image_path.with_suffix(".png")
        ExportService.save_png(sample_pixmap, path)
        assert path.is_file()
