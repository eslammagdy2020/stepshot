"""Tests for screenshot capture service."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QImage, QPixmap

from services.screenshot_service import ScreenshotService


class _MockScreen:
    """Stand-in for QScreen that reports a fixed geometry/DPR and synthesizes a grab."""

    def __init__(self, geometry: QRect, dpr: float, color: QColor) -> None:
        self._geometry = geometry
        self._dpr = dpr
        self._color = color
        self.calls: list[tuple[int, int, int, int]] = []

    def geometry(self) -> QRect:
        return self._geometry

    def devicePixelRatio(self) -> float:
        return self._dpr

    def grabWindow(self, win_id: int, x: int = 0, y: int = 0, w: int = 0, h: int = 0) -> QPixmap:
        self.calls.append((x, y, w, h))
        if w <= 0 or h <= 0:
            return QPixmap()
        pixmap = QPixmap(w, h)
        pixmap.fill(self._color)
        return pixmap


class TestScreenshotService:
    def test_capture_full_screen_returns_valid_pixmap(self, qapp):
        pixmap = ScreenshotService.capture_full_screen()
        assert isinstance(pixmap, QPixmap)
        assert not pixmap.isNull()
        assert pixmap.width() > 0
        assert pixmap.height() > 0

    def test_capture_region_returns_valid_pixmap(self, qapp):
        screen = qapp.primaryScreen()
        geometry = screen.geometry()
        rect = QRect(
            geometry.x() + 10,
            geometry.y() + 10,
            min(200, geometry.width() - 20),
            min(150, geometry.height() - 20),
        )
        pixmap = ScreenshotService.capture_region(rect)
        assert isinstance(pixmap, QPixmap)
        assert not pixmap.isNull()
        assert pixmap.width() == rect.width()
        assert pixmap.height() == rect.height()
        assert pixmap.devicePixelRatio() == pytest.approx(screen.devicePixelRatio())

    @pytest.mark.parametrize(
        "rect",
        [
            QRect(0, 0, 0, 100),
            QRect(0, 0, 100, 0),
            QRect(0, 0, -50, 100),
        ],
    )
    def test_capture_region_rejects_invalid_rect(self, qapp, rect):
        with pytest.raises(ValueError, match="positive width and height"):
            ScreenshotService.capture_region(rect)


class TestCrossMonitorCapture:
    """Capture behavior when the selection crosses one or more screens."""

    def test_single_screen_path_preserved(self, qapp):
        screen = _MockScreen(QRect(0, 0, 800, 600), 1.0, QColor(255, 0, 0))
        with patch("services.screenshot_service.QGuiApplication.screens", return_value=[screen]):
            pixmap = ScreenshotService.capture_region(QRect(10, 10, 120, 80))
        assert pixmap.width() == 120
        assert pixmap.height() == 80
        assert screen.calls == [(10, 10, 120, 80)]

    def test_two_screens_compose_pixels_from_each(self, qapp):
        left = _MockScreen(QRect(0, 0, 800, 600), 1.0, QColor(255, 0, 0))
        right = _MockScreen(QRect(800, 0, 800, 600), 1.0, QColor(0, 0, 255))
        rect = QRect(700, 100, 200, 100)
        with patch("services.screenshot_service.QGuiApplication.screens", return_value=[left, right]):
            pixmap = ScreenshotService.capture_region(rect)
        assert pixmap.width() == 200
        assert pixmap.height() == 100
        assert left.calls == [(700, 100, 100, 100)]
        assert right.calls == [(0, 100, 100, 100)]
        image = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
        sample_left = QColor(image.pixel(20, 50))
        sample_right = QColor(image.pixel(180, 50))
        assert sample_left.red() > 200 and sample_left.blue() < 50
        assert sample_right.blue() > 200 and sample_right.red() < 50

    def test_negative_global_coordinates_do_not_shift_output(self, qapp):
        primary = _MockScreen(QRect(-1280, 0, 1280, 800), 1.0, QColor(0, 255, 0))
        rect = QRect(-1280 + 100, 50, 200, 100)
        with patch("services.screenshot_service.QGuiApplication.screens", return_value=[primary]):
            pixmap = ScreenshotService.capture_region(rect)
        assert pixmap.width() == 200
        assert pixmap.height() == 100
        image = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
        sample = QColor(image.pixel(50, 50))
        assert sample.green() > 200

    def test_mixed_dpi_passes_logical_pixels_to_grab(self, qapp):
        low = _MockScreen(QRect(0, 0, 800, 600), 1.0, QColor(255, 255, 0))
        high = _MockScreen(QRect(800, 0, 800, 600), 1.5, QColor(255, 0, 255))
        rect = QRect(700, 100, 200, 100)
        with patch("services.screenshot_service.QGuiApplication.screens", return_value=[low, high]):
            pixmap = ScreenshotService.capture_region(rect)
        assert pixmap.width() == 200
        assert pixmap.height() == 100
        assert low.calls == [(700, 100, 100, 100)]
        assert high.calls == [(0, 100, 100, 100)]
        assert pixmap.devicePixelRatio() == pytest.approx(1.0)

    def test_region_outside_all_screens_raises(self, qapp):
        primary = _MockScreen(QRect(0, 0, 800, 600), 1.0, QColor(0, 0, 0))
        with patch("services.screenshot_service.QGuiApplication.screens", return_value=[primary]):
            with pytest.raises(RuntimeError, match="No screen covers"):
                ScreenshotService.capture_region(QRect(2000, 2000, 100, 100))

    def test_grab_failure_inside_multi_screen_raises(self, qapp):
        def grab_zero(*args, **kwargs):
            return QPixmap()

        left = _MockScreen(QRect(0, 0, 800, 600), 1.0, QColor(0, 0, 0))
        right = SimpleNamespace(
            geometry=lambda: QRect(800, 0, 800, 600),
            devicePixelRatio=lambda: 1.0,
            grabWindow=grab_zero,
        )
        with patch("services.screenshot_service.QGuiApplication.screens", return_value=[left, right]):
            with pytest.raises(RuntimeError, match="Failed to capture"):
                ScreenshotService.capture_region(QRect(700, 100, 200, 100))