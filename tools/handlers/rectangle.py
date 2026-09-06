"""Rectangle tool mouse handler."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF

from tools.handlers.base import RectDragHandler
from ui.graphics_items import RectangleGraphicsItem


class RectangleHandler(RectDragHandler):
    def _create_preview(self, scene_pos: QPointF):
        color, thickness, filled = self.context.get_rectangle_settings()
        return RectangleGraphicsItem(
            QRectF(scene_pos, scene_pos),
            color,
            thickness,
            filled,
        )

    def _commit(self, rect: QRectF, preview) -> bool:
        preview.rect = rect
        preview.prepareGeometryChange()
        preview.update()
        self.context.add_item(preview)
        return True
