"""View-overlay handles for resizing arrow / rectangle / highlight annotations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPaintEvent, QPainter, QPen
from PySide6.QtWidgets import QGraphicsView, QWidget

from ui.graphics_items import (
    ArrowGraphicsItem,
    HighlightGraphicsItem,
    RectangleGraphicsItem,
)


class HandleRole(str, Enum):
    ARROW_START = "arrow_start"
    ARROW_END = "arrow_end"
    RECT_TL = "rect_tl"
    RECT_TR = "rect_tr"
    RECT_BL = "rect_bl"
    RECT_BR = "rect_br"
    RECT_T = "rect_t"
    RECT_B = "rect_b"
    RECT_L = "rect_l"
    RECT_R = "rect_r"


@dataclass(frozen=True)
class Handle:
    role: HandleRole
    rect: QRect


HANDLE_SCREEN_SIZE = 10
HANDLE_HIT_PAD = 4


class ResizeHandleLayer(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._item: ArrowGraphicsItem | RectangleGraphicsItem | HighlightGraphicsItem | None = None
        self._handles: list[Handle] = []

    def target(self) -> ArrowGraphicsItem | RectangleGraphicsItem | HighlightGraphicsItem | None:
        return self._item

    def hide_handles(self) -> None:
        if self._item is None and not self._handles:
            return
        self._item = None
        self._handles = []
        self.hide()
        self.update()

    def update_for_item(
        self,
        item: ArrowGraphicsItem | RectangleGraphicsItem | HighlightGraphicsItem | None,
        view: QGraphicsView,
    ) -> None:
        if item is None or not isinstance(
            item, (ArrowGraphicsItem, RectangleGraphicsItem, HighlightGraphicsItem)
        ):
            self.hide_handles()
            return
        self._item = item
        self._handles = self._compute_handles(item, view)
        self.setGeometry(view.viewport().geometry())
        self.raise_()
        self.show()
        self.update()

    def resize_to_viewport(self, view: QGraphicsView) -> None:
        if self._item is None:
            return
        self.setGeometry(view.viewport().geometry())
        self._handles = self._compute_handles(self._item, view)
        self.update()

    def handle_at(self, pos: QPoint) -> Handle | None:
        for handle in self._handles:
            if handle.rect.adjusted(-HANDLE_HIT_PAD, -HANDLE_HIT_PAD, HANDLE_HIT_PAD, HANDLE_HIT_PAD).contains(pos):
                return handle
        return None

    def paintEvent(self, event: QPaintEvent | None) -> None:
        del event
        if not self._handles:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        pen = QPen(QColor(0, 120, 215), 1)
        brush = QBrush(QColor(255, 255, 255))
        for handle in self._handles:
            painter.setPen(pen)
            painter.setBrush(brush)
            painter.drawRect(handle.rect)

    def _compute_handles(
        self,
        item: ArrowGraphicsItem | RectangleGraphicsItem | HighlightGraphicsItem,
        view: QGraphicsView,
    ) -> list[Handle]:
        # Handle squares are drawn in viewport coordinates via view.mapFromScene,
        # so the size argument is already in screen pixels — no division by zoom.
        size = HANDLE_SCREEN_SIZE
        if isinstance(item, ArrowGraphicsItem):
            return self._arrow_handles(item, view, size)
        return self._rect_handles(item, view, size)

    def _arrow_handles(
        self, item: ArrowGraphicsItem, view: QGraphicsView, size: int
    ) -> list[Handle]:
        start_scene = item.start_point + item.pos()
        end_scene = item.end_point + item.pos()
        return [
            Handle(HandleRole.ARROW_START, self._square(view.mapFromScene(start_scene), size)),
            Handle(HandleRole.ARROW_END, self._square(view.mapFromScene(end_scene), size)),
        ]

    def _rect_handles(
        self,
        item: RectangleGraphicsItem | HighlightGraphicsItem,
        view: QGraphicsView,
        size: int,
    ) -> list[Handle]:
        scene_rect = QRectF(item.rect).translated(item.pos())
        mid_x = (scene_rect.left() + scene_rect.right()) / 2
        mid_y = (scene_rect.top() + scene_rect.bottom()) / 2
        corners = {
            HandleRole.RECT_TL: scene_rect.topLeft(),
            HandleRole.RECT_TR: scene_rect.topRight(),
            HandleRole.RECT_BL: scene_rect.bottomLeft(),
            HandleRole.RECT_BR: scene_rect.bottomRight(),
            HandleRole.RECT_T: QPointF(mid_x, scene_rect.top()),
            HandleRole.RECT_B: QPointF(mid_x, scene_rect.bottom()),
            HandleRole.RECT_L: QPointF(scene_rect.left(), mid_y),
            HandleRole.RECT_R: QPointF(scene_rect.right(), mid_y),
        }
        return [
            Handle(role, self._square(view.mapFromScene(point), size))
            for role, point in corners.items()
        ]

    @staticmethod
    def _square(center: QPoint, size: int) -> QRect:
        half = size // 2
        return QRect(center.x() - half, center.y() - half, size, size)
