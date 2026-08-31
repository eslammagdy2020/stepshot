"""Tests for Scenario 2 tutorial annotation tools."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt

from tests.conftest import left_move, left_press, left_release, place_step_marker
from ui.canvas import AnnotationCanvas, ToolMode
from ui.graphics_items import (
    BlurPatchGraphicsItem,
    HighlightGraphicsItem,
    RectangleGraphicsItem,
    TextGraphicsItem,
)


def draw_rect_on_canvas(canvas, qtbot, start: QPointF, end: QPointF, mode: ToolMode) -> None:
    canvas.set_tool_mode(mode)
    left_press(canvas.viewport(), qtbot, canvas.mapFromScene(start))
    left_move(canvas.viewport(), qtbot, canvas.mapFromScene(end))
    left_release(canvas.viewport(), qtbot, canvas.mapFromScene(end))


class TestRectangleTool:
    def test_draw_outline_rectangle(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        canvas.set_rectangle_filled(False)

        draw_rect_on_canvas(
            canvas, qtbot, QPointF(30, 30), QPointF(180, 120), ToolMode.RECTANGLE
        )

        rects = [i for i in canvas.scene().items() if isinstance(i, RectangleGraphicsItem)]
        assert len(rects) == 1
        assert rects[0].filled is False

    def test_filled_rectangle(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        canvas.set_rectangle_filled(True)

        draw_rect_on_canvas(
            canvas, qtbot, QPointF(40, 40), QPointF(120, 90), ToolMode.RECTANGLE
        )

        rect = next(i for i in canvas.scene().items() if isinstance(i, RectangleGraphicsItem))
        assert rect.filled is True


class TestHighlightTool:
    def test_draw_highlight(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        draw_rect_on_canvas(
            canvas, qtbot, QPointF(50, 50), QPointF(200, 140), ToolMode.HIGHLIGHT
        )

        highlights = [
            i for i in canvas.scene().items() if isinstance(i, HighlightGraphicsItem)
        ]
        assert len(highlights) == 1
        assert highlights[0].opacity > 0


class TestBlurTool:
    def test_blur_creates_patch(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        draw_rect_on_canvas(
            canvas, qtbot, QPointF(60, 60), QPointF(200, 160), ToolMode.BLUR
        )

        patches = [i for i in canvas.scene().items() if isinstance(i, BlurPatchGraphicsItem)]
        assert len(patches) == 1

    def test_blur_patch_stores_source_rect(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        draw_rect_on_canvas(
            canvas, qtbot, QPointF(60, 60), QPointF(200, 160), ToolMode.BLUR
        )

        patch = next(
            i for i in canvas.scene().items() if isinstance(i, BlurPatchGraphicsItem)
        )
        assert patch.source_rect is not None
        assert patch.source_rect.width() >= 5
        assert patch.source_rect.height() >= 5

    def test_blur_patch_source_rect_survives_undo_redo(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)

        draw_rect_on_canvas(
            canvas, qtbot, QPointF(60, 60), QPointF(200, 160), ToolMode.BLUR
        )
        patch = next(
            i for i in canvas.scene().items() if isinstance(i, BlurPatchGraphicsItem)
        )
        source_rect = patch.source_rect

        canvas.undo()
        assert [
            i for i in canvas.scene().items() if isinstance(i, BlurPatchGraphicsItem)
        ] == []

        canvas.redo()
        patch = next(
            i for i in canvas.scene().items() if isinstance(i, BlurPatchGraphicsItem)
        )
        assert patch.source_rect == source_rect


class TestTutorialTextWorkflow:
    def test_inline_text_placement(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.TEXT)

        left_press(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(25, 25)))

        texts = [i for i in canvas.scene().items() if isinstance(i, TextGraphicsItem)]
        assert len(texts) == 1
        assert texts[0].textInteractionFlags() & Qt.TextInteractionFlag.TextEditorInteraction

    def test_click_away_finishes_text_without_adding_another(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.TEXT)

        left_press(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(25, 25)))
        texts = [i for i in canvas.scene().items() if isinstance(i, TextGraphicsItem)]
        # Phase 11: a direct setPlainText bypasses the placeholder-clearing keystroke,
        # so is_placeholder stays True and finalize_editing would blank it. Clear the
        # flag the way real typing would before setting text.
        texts[0].is_placeholder = False
        texts[0].setPlainText("Step 1: Open menu")

        left_press(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(200, 200)))

        texts = [i for i in canvas.scene().items() if isinstance(i, TextGraphicsItem)]
        assert len(texts) == 1
        assert canvas._editing_text_item is None


class TestResetToOriginal:
    def test_reset_clears_annotations(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.STEP)
        place_step_marker(canvas, qtbot, QPointF(80, 80))

        assert canvas.reset_to_original() is True
        assert canvas._step_markers() == []
        assert canvas.step_counter.next_number == 1
