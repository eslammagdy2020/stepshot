"""Custom graphics items for annotations."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QKeyEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsItemGroup,
    QGraphicsPixmapItem,
    QGraphicsTextItem,
    QStyleOptionGraphicsItem,
    QWidget,
)


def _clamp_min_size(rect: QRectF) -> QRectF:
    clamped = QRectF(rect).normalized()
    if clamped.width() < 4:
        clamped.setWidth(4)
    if clamped.height() < 4:
        clamped.setHeight(4)
    return clamped


class ArrowGraphicsItem(QGraphicsItem):
    def __init__(
        self,
        start: QPointF,
        end: QPointF,
        color: QColor | None = None,
        thickness: int = 3,
    ) -> None:
        super().__init__()
        self.start_point = QPointF(start)
        self.end_point = QPointF(end)
        self.color = color or QColor(255, 0, 0)
        self.thickness = thickness
        self.setFlags(
            QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

    def boundingRect(self) -> QRectF:
        padding = max(12, self.thickness * 4)
        return QRectF(self.start_point, self.end_point).normalized().adjusted(
            -padding, -padding, padding, padding
        )

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        del option, widget
        pen = QPen(self.color, self.thickness, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(self.color)
        painter.drawLine(self.start_point, self.end_point)

        angle = math.atan2(
            self.end_point.y() - self.start_point.y(),
            self.end_point.x() - self.start_point.x(),
        )
        head_length = max(12, self.thickness * 4)
        head_angle = math.pi / 7

        p1 = QPointF(
            self.end_point.x() - head_length * math.cos(angle - head_angle),
            self.end_point.y() - head_length * math.sin(angle - head_angle),
        )
        p2 = QPointF(
            self.end_point.x() - head_length * math.cos(angle + head_angle),
            self.end_point.y() - head_length * math.sin(angle + head_angle),
        )

        path = QPainterPath()
        path.moveTo(self.end_point)
        path.lineTo(p1)
        path.lineTo(p2)
        path.closeSubpath()
        painter.fillPath(path, self.color)

        if self.isSelected():
            painter.setPen(QPen(QColor(0, 120, 215), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.boundingRect())

    def set_color(self, color: QColor) -> None:
        self.color = color
        self.update()

    def set_thickness(self, thickness: int) -> None:
        self.thickness = thickness
        self.prepareGeometryChange()
        self.update()

    def set_geometry(self, start: QPointF, end: QPointF) -> None:
        new_start = QPointF(start)
        new_end = QPointF(end)
        if (new_end - new_start).manhattanLength() < 4:
            return
        self.prepareGeometryChange()
        self.start_point = new_start
        self.end_point = new_end
        self.update()


class StepMarkerGraphicsItem(QGraphicsItemGroup):
    def __init__(
        self,
        position: QPointF,
        number: int,
        color: QColor | None = None,
        size: int = 28,
    ) -> None:
        super().__init__()
        self.marker_color = color or QColor(255, 0, 0)
        self.marker_size = size
        self.number = number

        radius = size / 2
        self.circle = QGraphicsEllipseItem(-radius, -radius, size, size, self)
        self.circle.setPen(QPen(Qt.white, 2))
        self.circle.setBrush(QBrush(self.marker_color))

        self.label = QGraphicsTextItem(str(number), self)
        font = QFont("Segoe UI", max(10, size // 2), QFont.Bold)
        self.label.setFont(font)
        self.label.setDefaultTextColor(Qt.white)
        self._center_label()

        self.setPos(position)
        self.setFlags(
            QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemSendsGeometryChanges
        )

    def set_color(self, color: QColor) -> None:
        self.marker_color = color
        self.circle.setBrush(QBrush(color))
        self.update()

    def set_size(self, size: int) -> None:
        self.marker_size = size
        radius = size / 2
        self.circle.setRect(-radius, -radius, size, size)
        font = QFont("Segoe UI", max(10, size // 2), QFont.Bold)
        self.label.setFont(font)
        self._center_label()
        self.update()

    def set_number(self, number: int) -> None:
        self.number = number
        self.label.setPlainText(str(number))
        self._center_label()
        self.update()

    def _center_label(self) -> None:
        text_rect = self.label.boundingRect()
        self.label.setPos(-text_rect.width() / 2, -text_rect.height() / 2)


class TextGraphicsItem(QGraphicsTextItem):
    BACKDROP_MARGIN = 6

    def __init__(
        self,
        text: str,
        position: QPointF,
        color: QColor | None = None,
        font_size: int = 14,
        bold: bool = False,
    ) -> None:
        super().__init__(text)
        self.text_color = color or QColor(255, 0, 0)
        self.font_size = font_size
        self.bold = bold
        self._apply_font()
        self.setDefaultTextColor(self.text_color)
        self.setPos(position)
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.is_placeholder = False
        self.on_focus_out = None
        self.setFlags(
            QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemSendsGeometryChanges
        )

    def boundingRect(self) -> QRectF:
        return super().boundingRect().adjusted(
            -self.BACKDROP_MARGIN,
            -self.BACKDROP_MARGIN,
            self.BACKDROP_MARGIN,
            self.BACKDROP_MARGIN,
        )

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._backdrop_color())
        painter.drawRoundedRect(self.boundingRect(), 6, 6)
        painter.restore()
        super().paint(painter, option, widget)
        if self.isSelected():
            painter.setPen(QPen(QColor(0, 120, 215), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.boundingRect())

    def _backdrop_color(self) -> QColor:
        luminance = (
            0.299 * self.text_color.red()
            + 0.587 * self.text_color.green()
            + 0.114 * self.text_color.blue()
        )
        if luminance < 140:
            return QColor(255, 255, 255, 110)
        return QColor(0, 0, 0, 110)

    def _apply_font(self) -> None:
        weight = QFont.Bold if self.bold else QFont.Normal
        self.setFont(QFont("Segoe UI", self.font_size, weight))

    def set_color(self, color: QColor) -> None:
        self.text_color = color
        self.setDefaultTextColor(color)

    def set_font_size(self, font_size: int) -> None:
        self.font_size = font_size
        self._apply_font()

    def set_bold(self, bold: bool) -> None:
        self.bold = bold
        self._apply_font()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self.is_placeholder:
            self.is_placeholder = False
            self.setPlainText("")
        super().keyPressEvent(event)

    def finalize_editing(self) -> None:
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.clearFocus()
        if self.is_placeholder:
            self.setPlainText("")

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        if self.on_focus_out is not None:
            callback, self.on_focus_out = self.on_focus_out, None
            callback()
        else:
            self.finalize_editing()


class RectangleGraphicsItem(QGraphicsItem):
    def __init__(
        self,
        rect: QRectF,
        color: QColor | None = None,
        thickness: int = 3,
        filled: bool = False,
    ) -> None:
        super().__init__()
        self.rect = QRectF(rect).normalized()
        self.color = color or QColor(255, 0, 0)
        self.thickness = thickness
        self.filled = filled
        self.setFlags(
            QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemSendsGeometryChanges
        )

    def boundingRect(self) -> QRectF:
        padding = self.thickness + 2
        return self.rect.adjusted(-padding, -padding, padding, padding)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        del option, widget
        pen = QPen(self.color, self.thickness)
        painter.setPen(pen)
        if self.filled:
            painter.setBrush(QBrush(self.color))
        else:
            painter.setBrush(Qt.NoBrush)
        painter.drawRect(self.rect)

        if self.isSelected():
            painter.setPen(QPen(QColor(0, 120, 215), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.boundingRect())

    def set_color(self, color: QColor) -> None:
        self.color = color
        self.update()

    def set_thickness(self, thickness: int) -> None:
        self.thickness = thickness
        self.prepareGeometryChange()
        self.update()

    def set_filled(self, filled: bool) -> None:
        self.filled = filled
        self.update()

    def set_geometry(self, rect: QRectF) -> None:
        self.prepareGeometryChange()
        self.rect = _clamp_min_size(rect)
        self.update()


class HighlightGraphicsItem(QGraphicsItem):
    def __init__(
        self,
        rect: QRectF,
        color: QColor | None = None,
        opacity: int = 128,
    ) -> None:
        super().__init__()
        self.rect = QRectF(rect).normalized()
        base = color or QColor(255, 255, 0)
        self.color = QColor(base.red(), base.green(), base.blue(), opacity)
        self.opacity = opacity
        self.setFlags(
            QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemSendsGeometryChanges
        )

    def boundingRect(self) -> QRectF:
        return self.rect

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        del option, widget
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.color))
        painter.drawRect(self.rect)

        if self.isSelected():
            painter.setPen(QPen(QColor(0, 120, 215), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.boundingRect())

    def set_color(self, color: QColor) -> None:
        self.color = QColor(color.red(), color.green(), color.blue(), self.opacity)
        self.update()

    def set_opacity(self, opacity: int) -> None:
        self.opacity = max(0, min(255, opacity))
        self.color.setAlpha(self.opacity)
        self.update()

    def set_geometry(self, rect: QRectF) -> None:
        self.prepareGeometryChange()
        self.rect = _clamp_min_size(rect)
        self.update()


class PenStrokeGraphicsItem(QGraphicsItem):
    def __init__(
        self,
        path_or_start: QPainterPath | QPointF,
        color: QColor | None = None,
        thickness: int = 3,
    ) -> None:
        super().__init__()
        self.path = QPainterPath(path_or_start)
        self.color = color or QColor(255, 0, 0)
        self.thickness = thickness
        self.setFlags(
            QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

    def add_point(self, point: QPointF) -> None:
        self.path.lineTo(point)
        self.prepareGeometryChange()
        self.update()

    def boundingRect(self) -> QRectF:
        padding = max(4, self.thickness + 2)
        return self.path.boundingRect().adjusted(-padding, -padding, padding, padding)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        del option, widget
        pen = QPen(self.color, self.thickness, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(self.path)

        if self.isSelected():
            painter.setPen(QPen(QColor(0, 120, 215), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.boundingRect())

    def set_color(self, color: QColor) -> None:
        self.color = color
        self.update()

    def set_thickness(self, thickness: int) -> None:
        self.thickness = thickness
        self.prepareGeometryChange()
        self.update()


class BlurPatchGraphicsItem(QGraphicsPixmapItem):
    def __init__(
        self,
        pixmap: QPixmap,
        position: QPointF,
        mode: str,
        strength: int,
        source_rect: QRectF | None = None,
    ) -> None:
        super().__init__(pixmap)
        self.blur_mode = mode
        self.strength = strength
        self.source_rect = source_rect
        self.setPos(position)
        self.setFlags(QGraphicsItem.ItemIsSelectable)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        super().paint(painter, option, widget)
        if self.isSelected():
            painter.setPen(QPen(QColor(0, 120, 215), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.boundingRect())

