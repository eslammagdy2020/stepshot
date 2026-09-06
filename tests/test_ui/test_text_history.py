"""Tests for atomic text creation and canvas-owned text editing history (Phase 11)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from tests.conftest import (
    add_text_annotation,
    double_click_on_canvas,
    left_press,
    place_step_marker,
)
from ui.canvas import AnnotationCanvas, ToolMode
from ui.graphics_items import RectangleGraphicsItem, TextGraphicsItem


def _text_items(canvas) -> list[TextGraphicsItem]:
    return [i for i in canvas.scene().items() if isinstance(i, TextGraphicsItem)]


def _make_canvas(qtbot, sample_pixmap) -> AnnotationCanvas:
    canvas = AnnotationCanvas()
    qtbot.addWidget(canvas)
    canvas.load_image(sample_pixmap)
    canvas.set_tool_mode(ToolMode.TEXT)
    return canvas


def _create_and_type(canvas, qtbot, scene_pos: QPointF, text: str) -> TextGraphicsItem:
    left_press(canvas.viewport(), qtbot, canvas.mapFromScene(scene_pos))
    QTest.keyClicks(canvas.viewport(), text)
    return _text_items(canvas)[0]


class TestCreateTextHistory:
    def test_create_and_type_one_undo_removes(self, qapp, qtbot, sample_pixmap):
        canvas = _make_canvas(qtbot, sample_pixmap)

        _create_and_type(canvas, qtbot, QPointF(50, 50), "Hello")
        left_press(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(400, 400)))

        texts = _text_items(canvas)
        assert len(texts) == 1
        assert texts[0].toPlainText() == "Hello"

        canvas.undo()
        assert len(_text_items(canvas)) == 0

        canvas.redo()
        texts = _text_items(canvas)
        assert len(texts) == 1
        assert texts[0].toPlainText() == "Hello"

    def test_placeholder_never_surfaces_after_undo(self, qapp, qtbot, sample_pixmap):
        canvas = _make_canvas(qtbot, sample_pixmap)

        _create_and_type(canvas, qtbot, QPointF(50, 50), "Hello")
        left_press(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(400, 400)))

        canvas.undo()
        assert len(_text_items(canvas)) == 0
        assert all(
            i.toPlainText() != "Enter instruction..."
            for i in canvas.scene().items()
            if isinstance(i, TextGraphicsItem)
        )

    def test_empty_new_text_leaves_nothing_and_no_history(self, qapp, qtbot, sample_pixmap):
        canvas = _make_canvas(qtbot, sample_pixmap)

        before_len = len(canvas.history.undo_stack)
        left_press(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(50, 50)))
        # Finalize without typing anything.
        left_press(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(400, 400)))

        assert len(_text_items(canvas)) == 0
        assert len(canvas.history.undo_stack) == before_len


class TestEditTextHistory:
    def test_edit_existing_undo_restores_previous(self, qapp, qtbot, sample_pixmap):
        canvas = _make_canvas(qtbot, sample_pixmap)
        add_text_annotation(canvas, QPointF(60, 60), "Before")
        item = _text_items(canvas)[0]

        canvas._start_text_edit(item, is_new=False)
        item.setPlainText("")
        QTest.keyClicks(canvas.viewport(), "After")
        canvas._finalize_text_edit()

        assert len(_text_items(canvas)) == 1
        assert _text_items(canvas)[0].toPlainText() == "After"

        canvas.undo()
        assert len(_text_items(canvas)) == 1
        assert _text_items(canvas)[0].toPlainText() == "Before"

        canvas.redo()
        assert _text_items(canvas)[0].toPlainText() == "After"

    def test_edit_without_change_pushes_no_history(self, qapp, qtbot, sample_pixmap):
        canvas = _make_canvas(qtbot, sample_pixmap)
        add_text_annotation(canvas, QPointF(60, 60), "Same")
        item = _text_items(canvas)[0]

        before_len = len(canvas.history.undo_stack)
        canvas._start_text_edit(item, is_new=False)
        canvas._finalize_text_edit()

        assert len(canvas.history.undo_stack) == before_len
        assert _text_items(canvas)[0].toPlainText() == "Same"

    def test_double_click_routes_through_canvas(self, qapp, qtbot, sample_pixmap):
        canvas = _make_canvas(qtbot, sample_pixmap)
        add_text_annotation(canvas, QPointF(60, 60), "Target")
        item = _text_items(canvas)[0]

        double_click_on_canvas(canvas, qapp, item.pos() + QPointF(5, 5))

        assert canvas._editing_text_item is item
        assert (
            item.textInteractionFlags()
            & Qt.TextInteractionFlag.TextEditorInteraction
        )


class TestFinalizeContracts:
    def test_escape_finalizes_like_click_away(self, qapp, qtbot, sample_pixmap):
        canvas = _make_canvas(qtbot, sample_pixmap)

        _create_and_type(canvas, qtbot, QPointF(50, 50), "Hello")
        QTest.keyClick(canvas, Qt.Key.Key_Escape)

        assert canvas._editing_text_item is None
        texts = _text_items(canvas)
        assert len(texts) == 1
        assert texts[0].toPlainText() == "Hello"

        canvas.undo()
        assert len(_text_items(canvas)) == 0

    def test_multiline_survives_create_undo_redo(self, qapp, qtbot, sample_pixmap):
        canvas = _make_canvas(qtbot, sample_pixmap)

        left_press(canvas.viewport(), qtbot, canvas.mapFromScene(QPointF(50, 50)))
        QTest.keyClicks(canvas.viewport(), "Line1")
        QTest.keyClick(canvas.viewport(), Qt.Key.Key_Return)
        QTest.keyClicks(canvas.viewport(), "Line2")
        canvas._finalize_text_edit()

        assert _text_items(canvas)[0].toPlainText() == "Line1\nLine2"

        canvas.undo()
        assert len(_text_items(canvas)) == 0

        canvas.redo()
        assert _text_items(canvas)[0].toPlainText() == "Line1\nLine2"


class TestUndoWhileTextIsEditing:
    def test_undo_does_not_collapse_scene_when_text_is_in_edit_mode(
        self, qapp, qtbot, sample_pixmap
    ):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)

        rect_item = RectangleGraphicsItem(
            QRectF(20, 20, 60, 40), QColor(255, 0, 0), 3
        )
        canvas.scene().addItem(rect_item)
        canvas._push_undo_state()

        add_text_annotation(canvas, QPointF(80, 80), "first")
        text = next(
            i for i in canvas.scene().items() if isinstance(i, TextGraphicsItem)
        )
        canvas._start_text_edit(text, is_new=True)
        assert canvas._editing_text_item is text

        before_stack_depth = len(canvas.history.undo_stack)
        canvas.undo()
        after_stack_depth = len(canvas.history.undo_stack)

        assert after_stack_depth == before_stack_depth
        assert next(
            i for i in canvas.scene().items() if isinstance(i, RectangleGraphicsItem)
        ) is rect_item
        assert canvas._editing_text_item is text

    def test_redo_does_not_advance_while_text_is_in_edit_mode(
        self, qapp, qtbot, sample_pixmap
    ):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.STEP)

        place_step_marker(canvas, qtbot, QPointF(50, 50))
        place_step_marker(canvas, qtbot, QPointF(120, 50))
        canvas.undo()
        assert len(canvas.history.redo_stack) == 1
        assert len(canvas.history.undo_stack) == 1

        add_text_annotation(canvas, QPointF(80, 200), "note")
        text = next(
            i for i in canvas.scene().items() if isinstance(i, TextGraphicsItem)
        )
        canvas._start_text_edit(text, is_new=True)
        assert canvas._editing_text_item is text

        undo_before = len(canvas.history.undo_stack)
        redo_before = len(canvas.history.redo_stack)
        canvas.redo()
        assert len(canvas.history.undo_stack) == undo_before
        assert len(canvas.history.redo_stack) == redo_before
        assert canvas._editing_text_item is text
