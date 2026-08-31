"""Tests for image effect helpers."""

from __future__ import annotations

from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QPainter, QPixmap

from services.image_effects import BlurMode, apply_region_effect


def test_blur_region_changes_pixels(sample_pixmap):
    rect = QRect(50, 50, 120, 80)
    result = apply_region_effect(sample_pixmap, rect, BlurMode.BLUR, blur_radius=8)
    assert not result.isNull()
    assert result.width() == rect.width()
    assert result.height() == rect.height()


def test_pixelate_region(sample_pixmap):
    rect = QRect(20, 20, 100, 60)
    result = apply_region_effect(
        sample_pixmap, rect, BlurMode.PIXELATE, pixelate_size=10
    )
    assert not result.isNull()


def test_effect_preserves_device_pixel_ratio():
    pixmap = QPixmap(320, 240)
    pixmap.fill(QColor(70, 130, 180))
    pixmap.setDevicePixelRatio(2.0)

    rect = QRect(40, 40, 60, 40)
    result = apply_region_effect(
        pixmap, rect, BlurMode.BLUR, device_pixel_ratio=2.0
    )
    assert result.devicePixelRatio() == 2.0
    assert result.width() == rect.width()
    assert result.height() == rect.height()


def test_qpixmap_to_pil_uses_raw_rgba():
    from services.image_effects import qpixmap_to_pil

    pixmap = QPixmap(40, 30)
    pixmap.fill(QColor(255, 0, 0))
    image = qpixmap_to_pil(pixmap)
    assert image.mode == "RGBA"
    assert image.size == (40, 30)
    assert image.getpixel((5, 5))[:3] == (255, 0, 0)


def test_qpixmap_to_pil_handles_odd_widths():
    from services.image_effects import qpixmap_to_pil

    pixmap = QPixmap(37, 5)
    pixmap.fill(QColor(255, 0, 0))
    painter = QPainter(pixmap)
    painter.fillRect(36, 0, 1, 5, QColor(0, 0, 255))
    painter.end()

    image = qpixmap_to_pil(pixmap)
    assert image.size == (37, 5)
    assert image.getpixel((0, 2))[:3] == (255, 0, 0)
    assert image.getpixel((36, 2))[:3] == (0, 0, 255)
