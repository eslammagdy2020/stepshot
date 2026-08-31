"""Step tool mouse handler."""

from __future__ import annotations

from PySide6.QtCore import QPointF

from tools.handlers.base import ToolHandler
from ui.graphics_items import StepMarkerGraphicsItem


class StepHandler(ToolHandler):
    def on_press(self, scene_pos: QPointF) -> bool:
        marker = StepMarkerGraphicsItem(
            scene_pos,
            self.canvas._step_counter.next_number,
            self.canvas._step_color,
            self.canvas._step_size,
        )
        self.canvas.scene().addItem(marker)
        self.canvas._push_undo_state()
        self.canvas.image_changed.emit()
        return True
