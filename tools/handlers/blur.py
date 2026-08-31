"""Blur tool mouse handler."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor

from tools.handlers.base import RectDragHandler
from ui.graphics_items import RectangleGraphicsItem


class BlurHandler(RectDragHandler):
    def _create_preview(self, scene_pos: QPointF):
        return RectangleGraphicsItem(
            QRectF(scene_pos, scene_pos),
            QColor(0, 120, 215),
            2,
            False,
        )

    def _commit(self, rect: QRectF, preview) -> bool:
        del preview
        self.canvas._apply_blur_region(rect)
        return True
