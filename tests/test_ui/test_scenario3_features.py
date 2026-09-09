"""Tests for Phase 3-5 features (performance, UX polish, features)."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMainWindow

from tests.conftest import (
    draw_arrow_on_canvas,
    left_move,
    left_press,
    left_release,
    place_step_marker,
)
from ui.canvas import MAX_ZOOM, MIN_ZOOM, AnnotationCanvas, ToolMode
from ui.graphics_items import (
    ArrowGraphicsItem,
    PenStrokeGraphicsItem,
    StepMarkerGraphicsItem,
)
from ui.main_window import MainWindow
from ui.toolbar import LeftToolBar, TOOL_KEYS


def draw_pen_stroke(canvas, qtbot) -> None:
    canvas.set_tool_mode(ToolMode.PEN)
    left_press(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(10, 10)))
    left_move(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(60, 40)))
    left_move(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(120, 90)))
    left_release(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(120, 90)))


def _pens(canvas):
    return [
        i for i in canvas.scene().items() if isinstance(i, PenStrokeGraphicsItem)
    ]


class TestToolShortcuts:
    def test_key_mapping_defined_for_all_tools(self, qapp):
        for mode in ToolMode:
            assert TOOL_KEYS[mode]

    def test_letter_activates_tool(self, qapp, qtbot):
        toolbar = LeftToolBar()
        window = QMainWindow()
        window.setCentralWidget(toolbar)
        qtbot.addWidget(window)
        window.show()
        QApplication.setActiveWindow(window)

        selected: list[ToolMode] = []
        toolbar.tool_selected.connect(selected.append)

        QTest.keyClick(window, Qt.Key.Key_A)
        qtbot.wait(50)
        assert ToolMode.ARROW in selected


class TestDuplicateSelected:
    def test_duplicate_offsets_arrow(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        draw_arrow_on_canvas(canvas, qtbot, QPointF(50, 50), QPointF(150, 100))

        arrow = next(
            i for i in canvas.scene().items() if isinstance(i, ArrowGraphicsItem)
        )
        arrow.setSelected(True)
        canvas.duplicate_selected()

        arrows = [
            i for i in canvas.scene().items() if isinstance(i, ArrowGraphicsItem)
        ]
        assert len(arrows) == 2
        original = next(a for a in arrows if a is not arrow)
        assert original.start_point == arrow.start_point + QPointF(20, 20)
        assert original.end_point == arrow.end_point + QPointF(20, 20)

        canvas.undo()
        arrows = [
            i for i in canvas.scene().items() if isinstance(i, ArrowGraphicsItem)
        ]
        assert len(arrows) == 1

    def test_duplicate_step_gets_next_number(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.STEP)
        place_step_marker(canvas, qtbot, QPointF(80, 80))

        marker = next(
            i for i in canvas.scene().items() if isinstance(i, StepMarkerGraphicsItem)
        )
        marker.setSelected(True)
        canvas.duplicate_selected()

        markers = [
            i for i in canvas.scene().items() if isinstance(i, StepMarkerGraphicsItem)
        ]
        assert sorted(m.number for m in markers) == [1, 2]


class TestPenTool:
    def test_pen_draws_stroke_and_undo_removes(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        draw_pen_stroke(canvas, qtbot)
        assert len(_pens(canvas)) == 1
        assert _pens(canvas)[0].path.elementCount() >= 3

        canvas.undo()
        assert len(_pens(canvas)) == 0

    def test_pen_redo_restores_stroke(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        draw_pen_stroke(canvas, qtbot)
        canvas.undo()
        canvas.redo()
        assert len(_pens(canvas)) == 1

    def test_pen_stroke_is_deletable(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        draw_pen_stroke(canvas, qtbot)
        _pens(canvas)[0].setSelected(True)
        canvas.delete_selected()
        assert len(_pens(canvas)) == 0

    def test_pen_properties_apply_to_stroke(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        draw_pen_stroke(canvas, qtbot)
        stroke = _pens(canvas)[0]
        stroke.setSelected(True)
        canvas.set_pen_color(QColor(0, 0, 255))
        canvas.set_pen_thickness(8)
        assert stroke.color.blue() == 255
        assert stroke.thickness == 8


class TestCropTool:
    def _crop(self, canvas, qtbot):
        canvas.set_tool_mode(ToolMode.CROP)
        left_press(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(100, 50)))
        left_move(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(500, 400)))
        left_release(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(500, 400)))

    def test_crop_resizes_background(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        self._crop(canvas, qtbot)
        background = canvas._background_item.pixmap()
        assert 0 < background.width() < sample_pixmap.width()
        assert 0 < background.height() < sample_pixmap.height()

    def test_crop_applies_exact_region(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        canvas._apply_crop(QRectF(100, 50, 400, 350))
        background = canvas._background_item.pixmap()
        assert background.width() == 400
        assert background.height() == 350

    def test_crop_keeps_annotations(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        draw_arrow_on_canvas(canvas, qtbot, QPointF(150, 100), QPointF(250, 150))

        self._crop(canvas, qtbot)
        arrows = [
            i for i in canvas.scene().items() if isinstance(i, ArrowGraphicsItem)
        ]
        assert len(arrows) == 1

    def test_crop_undo_restores_background(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        self._crop(canvas, qtbot)
        assert canvas._background_item.pixmap().width() < 640
        canvas.undo()
        assert canvas._background_item.pixmap().width() == 640
        assert canvas._background_item.pixmap().height() == 480

    def test_crop_reflected_in_export(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        self._crop(canvas, qtbot)
        background = canvas._background_item.pixmap()
        rendered = canvas.render_to_pixmap()
        assert rendered.width() == background.width()
        assert rendered.height() == background.height()


class TestPanelSync:
    def test_panel_shows_selected_arrow_thickness(self, qapp, qtbot, sample_pixmap):
        window = MainWindow()
        qtbot.addWidget(window)
        window.load_screenshot(sample_pixmap)
        draw_arrow_on_canvas(window._canvas, qtbot, QPointF(50, 50), QPointF(200, 150))

        arrow = next(
            i
            for i in window._canvas.scene().items()
            if isinstance(i, ArrowGraphicsItem)
        )
        arrow.thickness = 7
        arrow.setSelected(True)
        window._update_properties_panel(arrow)

        assert window._arrow_thickness.value() == 7


class TestSettingsPersistence:
    def test_tool_defaults_persist_across_instances(self, qapp):
        first = AnnotationCanvas()
        first.set_arrow_color(QColor(0, 255, 0))
        first.set_pen_thickness(9)

        second = AnnotationCanvas()
        assert second._arrow_color.green() == 255
        assert second._pen_thickness == 9


class TestZoomIndicator:
    def test_zoom_reset_reports_100_percent(self, qapp, qtbot, sample_pixmap):
        window = MainWindow()
        qtbot.addWidget(window)
        window.load_screenshot(sample_pixmap)

        window._zoom_in()
        window._zoom_reset()
        assert round(window._canvas.transform().m11(), 3) == 1.0
        assert "100%" in window._zoom_label.text()

    def test_zoom_fit_sets_indicator(self, qapp, qtbot, sample_pixmap):
        window = MainWindow()
        qtbot.addWidget(window)
        window.load_screenshot(sample_pixmap)

        window._zoom_fit()
        assert window._zoom_label.text().startswith("Zoom:")

    def test_zoom_fit_respects_max_bound(self, qapp, qtbot):
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        tiny = QPixmap(4, 4)
        tiny.fill(QColor("steelblue"))
        window.load_screenshot(tiny)

        window._zoom_fit()
        assert window._canvas.transform().m11() <= MAX_ZOOM

    def test_clamp_zoom_raises_to_min_bound(self, qapp, qtbot, sample_pixmap):
        window = MainWindow()
        qtbot.addWidget(window)
        window.load_screenshot(sample_pixmap)

        window._canvas.resetTransform()
        window._canvas.scale(0.001, 0.001)
        window._canvas.clamp_zoom()
        assert window._canvas.transform().m11() == pytest.approx(MIN_ZOOM)

    def test_indicator_refreshes_after_reset_all(self, qapp, qtbot, sample_pixmap):
        window = MainWindow()
        qtbot.addWidget(window)
        window.load_screenshot(sample_pixmap)

        window._canvas.resetTransform()
        window._canvas.reset_to_original()
        expected = int(round(window._canvas.transform().m11() * 100))
        assert window._zoom_label.text() == f"Zoom: {expected}%"

    def test_indicator_refreshes_after_crop(self, qapp, qtbot, sample_pixmap):
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        window.load_screenshot(sample_pixmap)

        canvas = window._canvas
        canvas.set_tool_mode(ToolMode.CROP)
        canvas.resetTransform()
        window._update_zoom_indicator()
        stale = window._zoom_label.text()

        start = canvas.mapFromScene(QPointF(60, 40))
        end = canvas.mapFromScene(QPointF(300, 260))
        left_press(canvas.viewport(), qtbot, start)
        left_move(canvas.viewport(), qtbot, end)
        left_release(canvas.viewport(), qtbot, end)

        expected = int(round(canvas.transform().m11() * 100))
        assert window._zoom_label.text() == f"Zoom: {expected}%"
        assert window._zoom_label.text() != stale


class TestAnnotationCount:
    def test_count_updates_on_draw_and_delete(self, qapp, qtbot, sample_pixmap):
        window = MainWindow()
        qtbot.addWidget(window)
        window.load_screenshot(sample_pixmap)

        draw_arrow_on_canvas(window._canvas, qtbot, QPointF(50, 50), QPointF(200, 150))
        assert "1 annotations" in window._annotation_label.text()

        arrow = next(
            i
            for i in window._canvas.scene().items()
            if isinstance(i, ArrowGraphicsItem)
        )
        arrow.setSelected(True)
        window._canvas.delete_selected()
        assert "0 annotations" in window._annotation_label.text()

    def test_count_resets_on_new_capture(self, qapp, qtbot, sample_pixmap):
        window = MainWindow()
        qtbot.addWidget(window)
        window.load_screenshot(sample_pixmap)

        draw_arrow_on_canvas(window._canvas, qtbot, QPointF(50, 50), QPointF(200, 150))
        assert "1 annotations" in window._annotation_label.text()

        window.load_screenshot(sample_pixmap)
        assert "0 annotations" in window._annotation_label.text()
