"""Phase 10 — undoable annotation movement.

A Select-tool mouse drag commits exactly one history state, Undo restores the
original position and Redo the final position, and a click without movement
changes nothing. Movement is driven through real mouse events, not setPos().
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QPainterPath, QPixmap

from tests.conftest import drag_item_on_canvas
from ui.canvas import AnnotationCanvas, ToolMode
from ui.graphics_items import (
    ArrowGraphicsItem,
    HighlightGraphicsItem,
    PenStrokeGraphicsItem,
    RectangleGraphicsItem,
    StepMarkerGraphicsItem,
    TextGraphicsItem,
)


def make_canvas(qtbot) -> AnnotationCanvas:
    canvas = AnnotationCanvas()
    qtbot.addWidget(canvas)
    canvas.resize(700, 560)
    pixmap = QPixmap(200, 200)
    pixmap.fill(QColor(10, 20, 30))
    canvas.load_image(pixmap)
    canvas.show()
    return canvas


def add_arrow(canvas) -> ArrowGraphicsItem:
    item = ArrowGraphicsItem(QPointF(40, 40), QPointF(90, 90), QColor(255, 0, 0), 3)
    canvas.scene().addItem(item)
    canvas._push_undo_state()
    return item


def select_only(canvas, item) -> None:
    canvas.set_tool_mode(ToolMode.SELECT)
    canvas.scene().clearSelection()
    item.setSelected(True)


def arrow_center(canvas) -> QPointF:
    item = next(
        i for i in canvas.scene().items() if isinstance(i, ArrowGraphicsItem)
    )
    return item.sceneBoundingRect().center()


class TestDragCommitsOneUndo:
    def test_drag_creates_exactly_one_undo_state(self, qapp, qtbot):
        canvas = make_canvas(qtbot)
        arrow = add_arrow(canvas)
        select_only(canvas, arrow)
        depth = len(canvas.history.undo_stack)

        drag_item_on_canvas(canvas, qapp, QPointF(60, 60), QPointF(120, 120))

        assert len(canvas.history.undo_stack) == depth + 1

    def test_undo_restores_original_position(self, qapp, qtbot):
        canvas = make_canvas(qtbot)
        arrow = add_arrow(canvas)
        select_only(canvas, arrow)
        origin = arrow_center(canvas)

        drag_item_on_canvas(canvas, qapp, QPointF(60, 60), QPointF(120, 120))
        moved = arrow_center(canvas)
        assert moved != origin

        canvas.undo()
        assert arrow_center(canvas) == origin

    def test_redo_restores_final_position(self, qapp, qtbot):
        canvas = make_canvas(qtbot)
        arrow = add_arrow(canvas)
        select_only(canvas, arrow)

        drag_item_on_canvas(canvas, qapp, QPointF(60, 60), QPointF(120, 120))
        moved = arrow_center(canvas)

        canvas.undo()
        canvas.redo()
        assert arrow_center(canvas) == moved


class TestClickWithoutMovement:
    def test_click_without_moving_does_not_change_history(self, qapp, qtbot):
        canvas = make_canvas(qtbot)
        arrow = add_arrow(canvas)
        select_only(canvas, arrow)
        depth = len(canvas.history.undo_stack)

        drag_item_on_canvas(canvas, qapp, QPointF(60, 60), QPointF(60, 60))

        assert len(canvas.history.undo_stack) == depth
        assert QPointF(arrow.pos()) == QPointF(0, 0)


class TestPropertyEditOrderAroundMove:
    def test_property_edit_then_move_keeps_undo_order(self, qapp, qtbot):
        canvas = make_canvas(qtbot)
        arrow = add_arrow(canvas)
        select_only(canvas, arrow)

        canvas.set_arrow_thickness(9)
        canvas._push_undo_state()
        drag_item_on_canvas(canvas, qapp, QPointF(60, 60), QPointF(120, 120))

        # Undo the move: thickness edit survives, position reverts.
        canvas.undo()
        arrow = next(
            i for i in canvas.scene().items() if isinstance(i, ArrowGraphicsItem)
        )
        assert arrow.thickness == 9
        assert arrow.pos() == QPointF(0, 0)


class TestAllMovableFamiliesDrag:
    def _drag_and_assert(self, canvas, qapp, item) -> None:
        select_only(canvas, item)
        depth = len(canvas.history.undo_stack)
        drag_item_on_canvas(canvas, qapp, QPointF(70, 70), QPointF(130, 130))
        assert len(canvas.history.undo_stack) == depth + 1

    def test_rectangle_drag_is_undoable(self, qapp, qtbot):
        canvas = make_canvas(qtbot)
        item = RectangleGraphicsItem(
            QRectF(50, 50, 60, 40),
            QColor(0, 200, 0),
            3,
            False,
        )
        canvas.scene().addItem(item)
        canvas._push_undo_state()
        self._drag_and_assert(canvas, qapp, item)

    def test_step_marker_drag_is_undoable(self, qapp, qtbot):
        canvas = make_canvas(qtbot)
        item = StepMarkerGraphicsItem(QPointF(60, 60), 1, QColor(255, 0, 0), 28)
        canvas.scene().addItem(item)
        canvas._push_undo_state()
        self._drag_and_assert(canvas, qapp, item)

    def test_text_drag_is_undoable(self, qapp, qtbot):
        canvas = make_canvas(qtbot)
        item = TextGraphicsItem("hi", QPointF(60, 60), QColor(255, 0, 0), 14, False)
        canvas.scene().addItem(item)
        canvas._push_undo_state()
        self._drag_and_assert(canvas, qapp, item)

    def test_highlight_drag_is_undoable(self, qapp, qtbot):
        canvas = make_canvas(qtbot)
        item = HighlightGraphicsItem(QRectF(50, 50, 70, 50), QColor(255, 255, 0), 120)
        canvas.scene().addItem(item)
        canvas._push_undo_state()
        self._drag_and_assert(canvas, qapp, item)

    def test_pen_drag_is_undoable(self, qapp, qtbot):
        canvas = make_canvas(qtbot)
        path = QPainterPath(QPointF(50, 50))
        path.lineTo(QPointF(90, 90))
        item = PenStrokeGraphicsItem(path, QColor(255, 0, 0), 3)
        canvas.scene().addItem(item)
        canvas._push_undo_state()
        self._drag_and_assert(canvas, qapp, item)
