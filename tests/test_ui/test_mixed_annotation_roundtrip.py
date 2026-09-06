"""Mixed-annotation round-trip tests for undo/redo pixel-perfect restoration."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QImage, QPixmap

from tests.conftest import add_text_annotation, draw_arrow_on_canvas, place_step_marker
from ui.canvas import AnnotationCanvas, ToolMode
from ui.graphics_items import (
    ArrowGraphicsItem,
    HighlightGraphicsItem,
    PenStrokeGraphicsItem,
    RectangleGraphicsItem,
    StepMarkerGraphicsItem,
    TextGraphicsItem,
)


def _pixmaps_equal(a: QPixmap, b: QPixmap) -> bool:
    """Compare two pixmaps by converting both to the same image format."""
    return a.toImage().convertToFormat(QImage.Format.Format_ARGB32_Premultiplied) == \
           b.toImage().convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)


class TestMixedAnnotationRoundTrip:
    def _create_mixed_annotations(self, canvas: AnnotationCanvas, qtbot) -> QPixmap:
        """Create a canvas with multiple annotation types and return the rendered pixmap."""
        draw_arrow_on_canvas(canvas, qtbot, QPointF(50, 50), QPointF(200, 150))
        place_step_marker(canvas, qtbot, QPointF(300, 100))
        add_text_annotation(canvas, QPointF(100, 300), "Test Text")
        canvas.set_tool_mode(ToolMode.RECTANGLE)
        from tests.conftest import left_press, left_move, left_release
        left_press(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(400, 200)))
        left_move(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(550, 350)))
        left_release(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(550, 350)))
        canvas.set_tool_mode(ToolMode.HIGHLIGHT)
        left_press(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(50, 400)))
        left_move(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(300, 480)))
        left_release(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(300, 480)))
        canvas.set_tool_mode(ToolMode.PEN)
        left_press(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(450, 50)))
        left_move(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(500, 100)))
        left_move(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(550, 80)))
        left_release(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(550, 80)))
        canvas.set_tool_mode(ToolMode.BLUR)
        left_press(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(200, 200)))
        left_move(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(350, 300)))
        left_release(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(350, 300)))

        return canvas.render_to_pixmap()

    def _count_annotations(self, canvas: AnnotationCanvas) -> dict[str, int]:
        counts = {
            "arrow": 0,
            "step": 0,
            "text": 0,
            "rectangle": 0,
            "highlight": 0,
            "pen": 0,
            "blur": 0,
        }
        for item in canvas.scene().items():
            if isinstance(item, ArrowGraphicsItem):
                counts["arrow"] += 1
            elif isinstance(item, StepMarkerGraphicsItem):
                counts["step"] += 1
            elif isinstance(item, TextGraphicsItem):
                counts["text"] += 1
            elif isinstance(item, RectangleGraphicsItem):
                counts["rectangle"] += 1
            elif isinstance(item, HighlightGraphicsItem):
                counts["highlight"] += 1
            elif isinstance(item, PenStrokeGraphicsItem):
                counts["pen"] += 1
            elif hasattr(item, "__class__") and item.__class__.__name__ == "BlurPatchGraphicsItem":
                counts["blur"] += 1
        return counts

    def test_undo_redo_preserves_mixed_annotations_pixel_perfect(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        initial_render = self._create_mixed_annotations(canvas, qtbot)
        initial_counts = self._count_annotations(canvas)
        assert sum(initial_counts.values()) == 7

        canvas.undo()
        canvas.redo()

        restored_render = canvas.render_to_pixmap()
        restored_counts = self._count_annotations(canvas)

        assert restored_counts == initial_counts
        assert _pixmaps_equal(restored_render, initial_render)

    def test_multi_level_undo_redo_preserves_mixed_annotations(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        draw_arrow_on_canvas(canvas, qtbot, QPointF(50, 50), QPointF(200, 150))
        render_after_arrow = canvas.render_to_pixmap()

        place_step_marker(canvas, qtbot, QPointF(300, 100))
        render_after_step = canvas.render_to_pixmap()

        add_text_annotation(canvas, QPointF(100, 300), "Test Text")
        render_after_text = canvas.render_to_pixmap()

        canvas.undo()
        restored_after_undo_1 = canvas.render_to_pixmap()
        assert _pixmaps_equal(restored_after_undo_1, render_after_step)

        canvas.undo()
        restored_after_undo_2 = canvas.render_to_pixmap()
        assert _pixmaps_equal(restored_after_undo_2, render_after_arrow)

        canvas.undo()
        restored_after_undo_3 = canvas.render_to_pixmap()
        assert _pixmaps_equal(restored_after_undo_3, sample_pixmap)

        canvas.redo()
        restored_after_redo_1 = canvas.render_to_pixmap()
        assert _pixmaps_equal(restored_after_redo_1, render_after_arrow)

        canvas.redo()
        restored_after_redo_2 = canvas.render_to_pixmap()
        assert _pixmaps_equal(restored_after_redo_2, render_after_step)

        canvas.redo()
        restored_after_redo_3 = canvas.render_to_pixmap()
        assert _pixmaps_equal(restored_after_redo_3, render_after_text)

    def test_new_action_after_undo_clears_redo_but_preserves_undo(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        draw_arrow_on_canvas(canvas, qtbot, QPointF(50, 50), QPointF(200, 150))
        place_step_marker(canvas, qtbot, QPointF(300, 100))

        canvas.undo()
        canvas.undo()

        # At seed state: can't undo further, but can redo
        assert not canvas.history.can_undo
        assert canvas.history.can_redo

        add_text_annotation(canvas, QPointF(100, 300), "New Text After Undo")

        # New action clears redo, but creates new undo entry
        assert not canvas.history.can_redo
        assert canvas.history.can_undo

        # Undo the new text annotation
        canvas.undo()
        counts = self._count_annotations(canvas)
        assert counts["arrow"] == 0
        assert counts["step"] == 0
        assert counts["text"] == 0

        # Redo the text annotation
        canvas.redo()
        counts = self._count_annotations(canvas)
        assert counts["text"] == 1

    def test_load_image_after_annotations_resets_history(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        draw_arrow_on_canvas(canvas, qtbot, QPointF(50, 50), QPointF(200, 150))
        place_step_marker(canvas, qtbot, QPointF(300, 100))

        assert canvas.history.can_undo

        canvas.load_image(sample_pixmap)

        assert not canvas.history.can_undo
        assert not canvas.history.can_redo

        counts = self._count_annotations(canvas)
        assert counts["arrow"] == 0
        assert counts["step"] == 0

    def test_reset_to_original_clears_annotations_and_resets_history(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        draw_arrow_on_canvas(canvas, qtbot, QPointF(50, 50), QPointF(200, 150))
        place_step_marker(canvas, qtbot, QPointF(300, 100))

        assert canvas.history.can_undo

        result = canvas.reset_to_original()

        assert result is True
        assert not canvas.history.can_undo
        assert not canvas.history.can_redo

        counts = self._count_annotations(canvas)
        assert counts["arrow"] == 0
        assert counts["step"] == 0

        restored_render = canvas.render_to_pixmap()
        assert _pixmaps_equal(restored_render, sample_pixmap)

    def test_delete_selected_updates_history_correctly(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        draw_arrow_on_canvas(canvas, qtbot, QPointF(50, 50), QPointF(200, 150))
        place_step_marker(canvas, qtbot, QPointF(300, 100))
        add_text_annotation(canvas, QPointF(100, 300), "To Delete")

        text_item = next(i for i in canvas.scene().items() if isinstance(i, TextGraphicsItem))
        text_item.setSelected(True)
        canvas.delete_selected()

        assert canvas.history.can_undo

        canvas.undo()

        counts = self._count_annotations(canvas)
        assert counts["text"] == 1
        assert counts["arrow"] == 1
        assert counts["step"] == 1

        canvas.redo()

        counts = self._count_annotations(canvas)
        assert counts["text"] == 0
        assert counts["arrow"] == 1
        assert counts["step"] == 1