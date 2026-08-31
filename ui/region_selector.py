"""Fullscreen region selection overlay."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QRubberBand, QWidget


class RegionSelector(QWidget):
    capture_completed = Signal(QRect)
    capture_cancelled = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)

        screens = QGuiApplication.screens()
        if screens:
            geometry = screens[0].geometry()
            for screen in screens[1:]:
                geometry = geometry.united(screen.geometry())
        else:
            geometry = QRect(0, 0, 1920, 1080)
        self.setGeometry(geometry)

        self._origin: QPoint | None = None
        self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self._rubber_band.setStyleSheet(
            "background-color: rgba(79, 140, 255, 0.15);"
            "border: 2px solid #4f8cff;"
            "border-radius: 2px;"
        )

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(10, 14, 22, 170))

        font = QFont("Segoe UI", 13)
        painter.setFont(font)
        painter.setPen(QColor(238, 241, 246))
        painter.drawText(
            24,
            36,
            "Drag to select a region  ·  Esc to cancel",
        )

        if self._origin and not self._rubber_band.isHidden():
            rect = self._rubber_band.geometry()
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor("#4f8cff"), 2, Qt.PenStyle.SolidLine))
            painter.drawRect(rect)

            size_text = f"{rect.width()} × {rect.height()}"
            painter.setPen(QColor(200, 210, 230))
            painter.drawText(rect.bottomLeft() + QPoint(4, 20), size_text)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.capture_cancelled.emit()
            self.close()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.position().toPoint()
            self._rubber_band.setGeometry(QRect(self._origin, self._origin))
            self._rubber_band.show()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._origin is not None:
            rect = QRect(self._origin, event.position().toPoint()).normalized()
            self._rubber_band.setGeometry(rect)
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._origin is not None:
            rect = QRect(self._origin, event.position().toPoint()).normalized()
            self._rubber_band.hide()
            self._origin = None
            if rect.width() >= 5 and rect.height() >= 5:
                global_rect = QRect(
                    self.mapToGlobal(rect.topLeft()),
                    rect.size(),
                )
                self.hide()
                self.close()
                self.capture_completed.emit(global_rect)
            else:
                self.capture_cancelled.emit()
                self.close()
            return
        super().mouseReleaseEvent(event)
