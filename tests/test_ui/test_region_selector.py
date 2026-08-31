"""Tests for region selection overlay."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt

from ui.region_selector import RegionSelector


class TestRegionSelector:
    def test_escape_cancels_capture(self, qapp, qtbot):
        selector = RegionSelector()
        qtbot.addWidget(selector)

        cancelled = []
        selector.capture_cancelled.connect(lambda: cancelled.append(True))

        qtbot.keyClick(selector, Qt.Key_Escape)
        assert cancelled == [True]

    def test_geometry_covers_primary_screen(self, qapp):
        selector = RegionSelector()
        screen = qapp.primaryScreen()
        assert selector.geometry().contains(screen.geometry())

    def test_valid_drag_emits_global_rect(self, qapp, qtbot):
        selector = RegionSelector()
        qtbot.addWidget(selector)
        selector.show()

        captured: list[QRect] = []
        selector.capture_completed.connect(captured.append)

        origin = QPoint(100, 100)
        end = QPoint(300, 250)

        qtbot.mousePress(selector, Qt.LeftButton, pos=origin)
        qtbot.mouseMove(selector, pos=end)
        qtbot.mouseRelease(selector, Qt.LeftButton, pos=end)

        assert len(captured) == 1
        rect = captured[0]
        assert rect.width() >= 5
        assert rect.height() >= 5

    def test_tiny_selection_cancels(self, qapp, qtbot):
        selector = RegionSelector()
        qtbot.addWidget(selector)
        selector.show()

        cancelled = []
        selector.capture_cancelled.connect(lambda: cancelled.append(True))

        origin = QPoint(200, 200)
        end = QPoint(201, 201)

        qtbot.mousePress(selector, Qt.LeftButton, pos=origin)
        qtbot.mouseMove(selector, pos=end)
        qtbot.mouseRelease(selector, Qt.LeftButton, pos=end)

        assert cancelled == [True]
