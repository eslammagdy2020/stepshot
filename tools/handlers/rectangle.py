"""Rectangle tool mouse handler."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF

from tools.handlers.base import RectDragHandler
from ui.graphics_items import RectangleGraphicsItem


class RectangleHandler(RectDragHandler):
    def _create_preview(self, scene_pos: QPointF):
        return RectangleGraphicsItem(
            QRectF(scene_pos, scene_pos),
            self.canvas._rectangle_color,
            self.canvas._rectangle_thickness,
            self.canvas._rectangle_filled,
        )

    def _commit(self, rect: QRectF, preview) -> bool:
        preview.rect = rect
        preview.prepareGeometryChange()
        preview.update()
        self.canvas.scene().addItem(preview)
        return True
