"""Arrow tool mouse handler."""

from __future__ import annotations

from PySide6.QtCore import QPointF

from tools.handlers.base import ToolHandler
from ui.graphics_items import ArrowGraphicsItem


class ArrowHandler(ToolHandler):
    MIN_LENGTH_SQ = 25

    def __init__(self) -> None:
        self._start: QPointF | None = None
        self._preview: ArrowGraphicsItem | None = None

    def on_press(self, scene_pos: QPointF) -> bool:
        self._start = scene_pos
        self._preview = ArrowGraphicsItem(
            scene_pos,
            scene_pos,
            self.canvas._arrow_color,
            self.canvas._arrow_thickness,
        )
        self.canvas.scene().addItem(self._preview)
        return False

    def on_move(self, scene_pos: QPointF) -> None:
        if self._preview is None or self._start is None:
            return
        self._preview.end_point = scene_pos
        self._preview.prepareGeometryChange()
        self._preview.update()

    def on_release(self, scene_pos: QPointF) -> bool:
        if self._preview is None or self._start is None:
            return False
        preview = self._preview
        start = self._start
        self._preview = None
        self._start = None
        dx = scene_pos.x() - start.x()
        dy = scene_pos.y() - start.y()
        if dx * dx + dy * dy >= self.MIN_LENGTH_SQ:
            self.canvas._push_undo_state()
            self.canvas.image_changed.emit()
        else:
            self.canvas.scene().removeItem(preview)
        return True

    def cancel(self) -> None:
        if self._preview is not None:
            self.canvas.scene().removeItem(self._preview)
        self._preview = None
        self._start = None
