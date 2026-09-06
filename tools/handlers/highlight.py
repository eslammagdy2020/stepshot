"""Highlight tool mouse handler."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF

from tools.handlers.base import RectDragHandler
from ui.graphics_items import HighlightGraphicsItem


class HighlightHandler(RectDragHandler):
    def _create_preview(self, scene_pos: QPointF):
        color, opacity = self.context.get_highlight_settings()
        return HighlightGraphicsItem(
            QRectF(scene_pos, scene_pos),
            color,
            opacity,
        )

    def _commit(self, rect: QRectF, preview) -> bool:
        preview.rect = rect
        preview.prepareGeometryChange()
        preview.update()
        self.context.add_item(preview)
        return True
