"""Tests for crop boundaries and annotation retention (Phase 14)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor

from tests.conftest import drag_on_canvas
from ui.canvas import ToolMode
from ui.graphics_items import (
    ArrowGraphicsItem,
    RectangleGraphicsItem,
)


def _arrows(canvas) -> list[ArrowGraphicsItem]:
    return [i for i in canvas.scene().items() if isinstance(i, ArrowGraphicsItem)]


class TestCropClamping:
    def test_in_bounds_crop_copies_requested_area(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)

        assert canvas._apply_crop(QRectF(100, 100, 200, 150))
        bg = canvas._background_item.pixmap()
        assert bg.width() == 200
        assert bg.height() == 150
        assert canvas._background_item.boundingRect() == QRectF(0, 0, 200, 150)

    def test_out_of_bounds_crop_clamps_to_background(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)

        assert canvas._apply_crop(QRectF(540, 380, 200, 200))
        bg = canvas._background_item.pixmap()
        assert bg.width() == 100
        assert bg.height() == 100

    def test_partially_out_of_left_top_clamps(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)

        assert canvas._apply_crop(QRectF(-50, -50, 150, 120))
        bg = canvas._background_item.pixmap()
        assert bg.width() == 100
        assert bg.height() == 70


class TestCropNoOp:
    def test_wholly_invalid_crop_is_noop(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        before_bg = canvas._background_item.pixmap()
        before_count = len(canvas._undo_stack)

        assert not canvas._apply_crop(QRectF(700, 500, 100, 100))
        assert canvas._background_item.pixmap().cacheKey() == before_bg.cacheKey()
        assert len(canvas._undo_stack) == before_count

    def test_invalid_crop_via_handler_creates_no_history(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.CROP)
        before_bg = canvas._background_item.pixmap()
        before_count = len(canvas._undo_stack)
        emitted: list[bool] = []
        canvas.image_changed.connect(lambda: emitted.append(True))

        start = QPointF(canvas.mapFromScene(QPointF(700, 100)))
        end = QPointF(canvas.mapFromScene(QPointF(760, 160)))
        drag_on_canvas(canvas, qapp, start, end)

        assert canvas._background_item.pixmap().cacheKey() == before_bg.cacheKey()
        assert len(canvas._undo_stack) == before_count
        assert emitted == []


class TestCropAnnotationRetention:
    def test_fully_outside_annotations_removed(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)

        inside = ArrowGraphicsItem(QPointF(150, 150), QPointF(200, 200), QColor(255, 0, 0), 3)
        outside = ArrowGraphicsItem(QPointF(10, 10), QPointF(50, 50), QColor(0, 255, 0), 3)
        canvas.scene().addItem(inside)
        canvas.scene().addItem(outside)

        assert canvas._apply_crop(QRectF(100, 100, 200, 150))
        remaining = _arrows(canvas)
        assert len(remaining) == 1
        assert remaining[0] is inside

    def test_partially_intersecting_annotation_kept_relative_position(
        self, qapp, qtbot, sample_pixmap
    ):
        from ui.canvas import AnnotationCanvas

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)

        partial = ArrowGraphicsItem(QPointF(50, 150), QPointF(150, 250), QColor(255, 0, 0), 3)
        canvas.scene().addItem(partial)

        assert canvas._apply_crop(QRectF(100, 100, 200, 150))
        kept = _arrows(canvas)
        assert len(kept) == 1
        assert kept[0].start_point + kept[0].pos() == QPointF(-50, 50)
        assert kept[0].end_point + kept[0].pos() == QPointF(50, 150)

    def test_rectangle_retained_and_translated(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)

        rect_item = RectangleGraphicsItem(QRectF(120, 130, 60, 40), QColor(255, 0, 0), 3)
        rect_item.setPos(0, 0)
        canvas.scene().addItem(rect_item)

        assert canvas._apply_crop(QRectF(100, 100, 200, 150))
        rects = [
            i for i in canvas.scene().items() if isinstance(i, RectangleGraphicsItem)
        ]
        assert len(rects) == 1
        assert rects[0].pos() == QPointF(-100, -100)
        assert rects[0].rect == QRectF(120, 130, 60, 40)


class TestCropHistory:
    def test_undo_restores_prior_image_and_annotations(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)

        kept = ArrowGraphicsItem(QPointF(150, 150), QPointF(200, 200), QColor(255, 0, 0), 3)
        removed = ArrowGraphicsItem(QPointF(10, 10), QPointF(50, 50), QColor(0, 255, 0), 3)
        canvas.scene().addItem(kept)
        canvas.scene().addItem(removed)
        canvas._push_undo_state()

        assert canvas._apply_crop(QRectF(100, 100, 200, 150))
        canvas._push_undo_state()
        assert len(_arrows(canvas)) == 1
        assert canvas._background_item.pixmap().width() == 200

        canvas.undo()
        restored = _arrows(canvas)
        assert len(restored) == 2
        assert canvas._background_item.pixmap().width() == 640
        assert canvas._background_item.pixmap().height() == 480

        canvas.redo()
        assert len(_arrows(canvas)) == 1
        assert canvas._background_item.pixmap().width() == 200

    def test_valid_crop_via_handler_pushes_exactly_one_state(
        self, qapp, qtbot, sample_pixmap
    ):
        from ui.canvas import AnnotationCanvas

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.CROP)
        before_count = len(canvas._undo_stack)

        start = QPointF(canvas.mapFromScene(QPointF(100, 100)))
        end = QPointF(canvas.mapFromScene(QPointF(300, 250)))
        drag_on_canvas(canvas, qapp, start, end)

        assert len(canvas._undo_stack) == before_count + 1
        assert abs(canvas._background_item.pixmap().width() - 200) <= 1
