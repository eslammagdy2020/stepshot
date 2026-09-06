"""Tests for the annotation canvas."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QPixmap

from tests.conftest import add_text_annotation, draw_arrow_on_canvas, place_step_marker
from ui.canvas import AnnotationCanvas, ToolMode
from ui.graphics_items import (
    ArrowGraphicsItem,
    HighlightGraphicsItem,
    StepMarkerGraphicsItem,
    TextGraphicsItem,
)


class TestAnnotationCanvasLoad:
    def test_load_image_sets_background(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)

        canvas.load_image(sample_pixmap)

        assert canvas._background_item is not None
        assert not canvas._background_item.pixmap().isNull()

    def test_load_image_resets_step_counter(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        canvas.set_tool_mode(ToolMode.STEP)
        place_step_marker(canvas, qtbot, QPointF(50, 50))
        assert canvas.step_counter.next_number == 2

        canvas.load_image(sample_pixmap)
        assert canvas.step_counter.next_number == 1


class TestAnnotationCanvasTools:
    def test_draw_arrow_creates_item(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        draw_arrow_on_canvas(canvas, qtbot, QPointF(50, 50), QPointF(200, 150))

        arrows = [i for i in canvas.scene().items() if isinstance(i, ArrowGraphicsItem)]
        assert len(arrows) == 1

    def test_short_arrow_is_discarded(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        draw_arrow_on_canvas(canvas, qtbot, QPointF(100, 100), QPointF(102, 101))

        arrows = [i for i in canvas.scene().items() if isinstance(i, ArrowGraphicsItem)]
        assert len(arrows) == 0

    def test_step_tool_auto_increments(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.STEP)

        place_step_marker(canvas, qtbot, QPointF(80, 80))
        place_step_marker(canvas, qtbot, QPointF(160, 120))
        place_step_marker(canvas, qtbot, QPointF(240, 200))

        markers = [
            i for i in canvas.scene().items() if isinstance(i, StepMarkerGraphicsItem)
        ]
        numbers = sorted(m.number for m in markers)
        assert numbers == [1, 2, 3]

    def test_reset_step_numbering(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.STEP)

        place_step_marker(canvas, qtbot, QPointF(50, 50))
        place_step_marker(canvas, qtbot, QPointF(150, 150))
        canvas.reset_step_numbering()
        place_step_marker(canvas, qtbot, QPointF(250, 250))

        markers = [
            i for i in canvas.scene().items() if isinstance(i, StepMarkerGraphicsItem)
        ]
        numbers = sorted(m.number for m in markers)
        assert numbers == [1]

    def test_text_annotation_can_be_added(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        add_text_annotation(canvas, QPointF(30, 40), "Click here")

        texts = [i for i in canvas.scene().items() if isinstance(i, TextGraphicsItem)]
        assert len(texts) == 1
        assert texts[0].toPlainText() == "Click here"


class TestAnnotationCanvasProperties:
    def test_arrow_color_on_selection(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        draw_arrow_on_canvas(canvas, qtbot, QPointF(20, 20), QPointF(120, 80))

        arrow = next(i for i in canvas.scene().items() if isinstance(i, ArrowGraphicsItem))
        canvas.scene().clearSelection()
        arrow.setSelected(True)

        canvas.set_arrow_color(QColor(0, 255, 0))
        assert arrow.color.green() == 255

    def test_step_size_on_selection(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.STEP)
        place_step_marker(canvas, qtbot, QPointF(100, 100))

        marker = next(
            i for i in canvas.scene().items() if isinstance(i, StepMarkerGraphicsItem)
        )
        marker.setSelected(True)
        canvas.set_step_size(36)
        assert marker.marker_size == 36


class TestUndoCoalescing:
    def test_rapid_property_changes_coalesce_into_one_undo_state(self, qapp, qtbot, sample_pixmap):
        from ui.graphics_items import HighlightGraphicsItem

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        highlight = HighlightGraphicsItem(
            QRectF(30, 30, 100, 60),
            QColor(255, 255, 0),
            128,
        )
        canvas.scene().addItem(highlight)
        highlight.setSelected(True)
        canvas._push_undo_state()
        baseline = len(canvas.history.undo_stack)

        for opacity in range(20, 256, 5):
            canvas.set_highlight_opacity(opacity)

        qtbot.wait(500)
        assert len(canvas.history.undo_stack) == baseline + 1

    def test_undo_stack_is_capped(self, qapp, qtbot, sample_pixmap):
        from ui.graphics_items import StepMarkerGraphicsItem
        from PySide6.QtCore import QPointF

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        for i in range(200):
            marker = StepMarkerGraphicsItem(QPointF(i * 10, i * 10), i + 1, QColor(255, 0, 0), 28)
            canvas.scene().addItem(marker)
            canvas._push_undo_state()

        assert len(canvas.history.undo_stack) <= 50

    def test_pending_property_undo_flushes_before_gesture(
        self, qapp, qtbot, sample_pixmap
    ):
        from tests.conftest import left_move, left_press, left_release
        from ui.graphics_items import RectangleGraphicsItem

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)

        rect = RectangleGraphicsItem(QRectF(20, 20, 60, 40), QColor(255, 0, 0), 3, False)
        canvas.scene().addItem(rect)
        rect.setSelected(True)
        canvas._push_undo_state()

        canvas.set_rectangle_thickness(5)
        assert canvas._property_timer.isActive()

        canvas.set_tool_mode(ToolMode.RECTANGLE)
        left_press(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(300, 300)))
        left_move(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(400, 380)))

        assert not canvas._property_timer.isActive()

        qtbot.wait(500)

        rectangles = [
            r for r in canvas.history.current.annotations if r.kind == "rectangle"
        ]
        assert len(rectangles) == 1
        assert rectangles[0].thickness == 5

        left_release(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(400, 380)))

        rectangles = [
            r for r in canvas.history.current.annotations if r.kind == "rectangle"
        ]
        assert len(rectangles) == 2


class TestBackgroundInSnapshots:
    def test_snapshot_stores_background_image(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        state = canvas._capture_document_state()
        assert state.image is not None
        assert state.image.width > 0
        assert state.image.height > 0

    def test_undo_restores_swapped_background(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        original = canvas._background_item.pixmap()

        swapped = QPixmap(original.width(), original.height())
        swapped.fill(QColor(0, 0, 0))
        canvas._background_item.setPixmap(swapped)
        canvas._push_undo_state()
        assert canvas._background_item.pixmap().toImage() == swapped.toImage()

        canvas.undo()
        assert canvas._background_item.pixmap().toImage() == original.toImage()

    def test_redo_restores_swapped_background(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        original = canvas._background_item.pixmap()

        swapped = QPixmap(original.width(), original.height())
        swapped.fill(QColor(0, 0, 0))
        canvas._background_item.setPixmap(swapped)
        canvas._push_undo_state()

        canvas.undo()
        canvas.redo()
        assert canvas._background_item.pixmap().toImage() == swapped.toImage()


class TestAnnotationCanvasUndoRedo:
    def test_undo_removes_last_annotation(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        draw_arrow_on_canvas(canvas, qtbot, QPointF(10, 10), QPointF(100, 100))
        assert len([i for i in canvas.scene().items() if isinstance(i, ArrowGraphicsItem)]) == 1

        canvas.undo()
        assert len([i for i in canvas.scene().items() if isinstance(i, ArrowGraphicsItem)]) == 0

    def test_redo_restores_undone_state(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        draw_arrow_on_canvas(canvas, qtbot, QPointF(10, 10), QPointF(100, 100))
        canvas.undo()
        canvas.redo()

        assert len([i for i in canvas.scene().items() if isinstance(i, ArrowGraphicsItem)]) == 1

    def test_new_action_clears_redo_stack(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        draw_arrow_on_canvas(canvas, qtbot, QPointF(10, 10), QPointF(100, 100))
        canvas.undo()
        place_step_marker(canvas, qtbot, QPointF(50, 50))

        canvas.redo()
        assert len([i for i in canvas.scene().items() if isinstance(i, ArrowGraphicsItem)]) == 0

    def test_rejected_apply_does_not_clear_redo_stack(self, qapp, qtbot, sample_pixmap):
        from models.document_history import DocumentState, RejectedMutation

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        draw_arrow_on_canvas(canvas, qtbot, QPointF(10, 10), QPointF(100, 100))
        canvas.undo()
        assert canvas.history.can_redo

        current = canvas.history.current
        bad_state = DocumentState(
            version=1,
            image=current.image,
            annotations=current.annotations + (
                type("BadRecord", (), {"kind": "unknown", "version": 999})(),
            ),
            step_counter=current.step_counter,
        )
        result = canvas.history.apply(bad_state)
        assert isinstance(result, RejectedMutation)
        assert canvas.history.can_redo

    def test_step_counter_restores_after_undo(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.STEP)

        place_step_marker(canvas, qtbot, QPointF(80, 80))
        place_step_marker(canvas, qtbot, QPointF(160, 120))
        place_step_marker(canvas, qtbot, QPointF(240, 200))

        canvas.undo()
        canvas.undo()

        markers = [
            i for i in canvas.scene().items() if isinstance(i, StepMarkerGraphicsItem)
        ]
        assert [m.number for m in markers] == [1]

        canvas.redo()
        canvas.redo()
        markers = [
            i for i in canvas.scene().items() if isinstance(i, StepMarkerGraphicsItem)
        ]
        assert sorted(m.number for m in markers) == [1, 2, 3]

        canvas.undo()
        canvas.undo()
        place_step_marker(canvas, qtbot, QPointF(320, 240))
        markers = [
            i for i in canvas.scene().items() if isinstance(i, StepMarkerGraphicsItem)
        ]
        assert sorted(m.number for m in markers) == [1, 2]


class TestAnnotationCanvasDelete:
    def test_delete_selected_removes_items(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        add_text_annotation(canvas, QPointF(20, 20), "Remove me")

        text = next(i for i in canvas.scene().items() if isinstance(i, TextGraphicsItem))
        text.setSelected(True)
        canvas.delete_selected()

        texts = [i for i in canvas.scene().items() if isinstance(i, TextGraphicsItem)]
        assert len(texts) == 0

    def test_delete_selected_emits_image_changed(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        add_text_annotation(canvas, QPointF(20, 20), "Remove me")

        emitted = []

        def on_changed() -> None:
            emitted.append(True)

        canvas.image_changed.connect(on_changed)
        text = next(i for i in canvas.scene().items() if isinstance(i, TextGraphicsItem))
        text.setSelected(True)
        canvas.delete_selected()

        assert len(emitted) == 1


class TestAnnotationCanvasExport:
    def test_render_to_pixmap_matches_background_size(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        draw_arrow_on_canvas(canvas, qtbot, QPointF(10, 10), QPointF(200, 100))

        rendered = canvas.render_to_pixmap()
        background = canvas._background_item.pixmap()
        assert rendered.width() == background.width()
        assert rendered.height() == background.height()
        assert not rendered.isNull()


class TestCheckerboardBackground:
    def test_checkerboard_brush_is_cached(self, qapp):
        from PySide6.QtGui import QBrush

        canvas = AnnotationCanvas()
        assert isinstance(canvas._checker_brush, QBrush)
        assert not canvas._checker_brush.texture().isNull()

    def test_render_without_image_raises(self, qapp, qtbot):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)

        try:
            canvas.render_to_pixmap()
            raised = False
        except RuntimeError:
            raised = True
        assert raised
