"""Step tool mouse handler."""

from __future__ import annotations

from PySide6.QtCore import QPointF

from tools.handlers.base import ToolHandler
from ui.graphics_items import StepMarkerGraphicsItem


class StepHandler(ToolHandler):
    def on_press(self, scene_pos: QPointF) -> bool:
        color, size, counter = self.context.get_step_settings()
        marker = StepMarkerGraphicsItem(
            scene_pos,
            counter.next_number,
            color,
            size,
        )
        self.context.add_item(marker)
        self.context.push_undo_state()
        self.context.emit_image_changed()
        return True
