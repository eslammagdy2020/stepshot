"""Text tool mouse handler."""

from __future__ import annotations

from PySide6.QtCore import QPointF

from tools.handlers.base import ToolHandler
from ui.graphics_items import TextGraphicsItem


class TextHandler(ToolHandler):
    def on_press(self, scene_pos: QPointF) -> bool:
        clicked = self.context.get_text_item_at(scene_pos)

        if self.context.is_editing_text():
            self.context.finalize_text_edit()
            if clicked is not None:
                self.context.start_text_edit(clicked, is_new=False)
            return True

        if clicked is not None:
            self.context.start_text_edit(clicked, is_new=False)
            return True

        color, font_size, bold = self.context.get_text_settings()
        item = TextGraphicsItem(
            "Enter instruction...",
            scene_pos,
            color,
            font_size,
            bold,
        )
        item.is_placeholder = True
        self.context.add_item(item)
        self.context.start_text_edit(item, is_new=True)
        return True
