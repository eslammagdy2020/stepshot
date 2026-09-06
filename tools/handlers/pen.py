"""Freehand pen tool mouse handler."""

from __future__ import annotations

from PySide6.QtCore import QPointF

from tools.handlers.base import ToolHandler
from ui.graphics_items import PenStrokeGraphicsItem


class PenHandler(ToolHandler):
    def __init__(self) -> None:
        self._stroke: PenStrokeGraphicsItem | None = None

    def on_press(self, scene_pos: QPointF) -> bool:
        color, thickness = self.context.get_pen_settings()
        self._stroke = PenStrokeGraphicsItem(
            scene_pos,
            color,
            thickness,
        )
        self.context.add_item(self._stroke)
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
            self.context.push_undo_state()
            self.context.emit_image_changed()
        else:
            self.context.remove_item(stroke)
        return True

    def cancel(self) -> None:
        if self._stroke is not None:
            self.context.remove_item(self._stroke)
        self._stroke = None
