"""Text tool mouse handler."""

from __future__ import annotations

from PySide6.QtCore import QPointF

from tools.handlers.base import ToolHandler
from ui.graphics_items import TextGraphicsItem


class TextHandler(ToolHandler):
    def on_press(self, scene_pos: QPointF) -> bool:
        canvas = self.canvas
        clicked = canvas._text_item_at(scene_pos)

        if canvas._editing_text_item is not None:
            canvas._finalize_text_edit()
            if clicked is not None:
                canvas._start_text_edit(clicked, is_new=False)
            return True

        if clicked is not None:
            canvas._start_text_edit(clicked, is_new=False)
            return True

        item = TextGraphicsItem(
            "Enter instruction...",
            scene_pos,
            canvas._text_color,
            canvas._text_font_size,
            canvas._text_bold,
        )
        item.is_placeholder = True
        canvas.scene().addItem(item)
        canvas._start_text_edit(item, is_new=True)
        return True
