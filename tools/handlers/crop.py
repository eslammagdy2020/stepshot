"""Crop tool mouse handler."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor

from tools.handlers.base import RectDragHandler
from ui.graphics_items import RectangleGraphicsItem


class CropHandler(RectDragHandler):
    def _create_preview(self, scene_pos: QPointF):
        return RectangleGraphicsItem(
            QRectF(scene_pos, scene_pos),
            QColor(46, 204, 113),
            2,
            False,
        )

    def _commit(self, rect: QRectF, preview) -> bool:
        del preview
        return self.canvas._apply_crop(rect)
