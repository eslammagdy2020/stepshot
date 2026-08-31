"""Freehand pen tool mouse handler."""

from __future__ import annotations

from PySide6.QtCore import QPointF

from tools.handlers.base import ToolHandler
from ui.graphics_items import PenStrokeGraphicsItem


class PenHandler(ToolHandler):
    def __init__(self) -> None:
        self._stroke: PenStrokeGraphicsItem | None = None

    def on_press(self, scene_pos: QPointF) -> bool:
        self._stroke = PenStrokeGraphicsItem(
            scene_pos,
            self.canvas._pen_color,
            self.canvas._pen_thickness,
        )
        self.canvas.scene().addItem(self._stroke)
        return False

    def on_move(self, scene_pos: QPointF) -> None:
        if self._stroke is not None:
            self._stroke.add_point(scene_pos)

    def on_release(self, scene_pos: QPointF) -> bool:
        del scene_pos
        if self._stroke is None:
            return False
        stroke = self._stroke
        self._stroke = None
        if stroke.path.elementCount() >= 2:
            self.canvas._push_undo_state()
            self.canvas.image_changed.emit()
        else:
            self.canvas.scene().removeItem(stroke)
        return True

    def cancel(self) -> None:
        if self._stroke is not None:
            self.canvas.scene().removeItem(self._stroke)
        self._stroke = None
