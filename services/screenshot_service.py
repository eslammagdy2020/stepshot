"""Screenshot capture using Qt screen APIs."""

from __future__ import annotations

from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPixmap, QScreen


class ScreenshotService:
    @staticmethod
    def screens_intersecting(rect: QRect) -> list[QScreen]:
        screens = QGuiApplication.screens()
        return [screen for screen in screens if screen.geometry().intersects(rect)]

    @staticmethod
    def capture_full_screen() -> QPixmap:
        screens = QGuiApplication.screens()
        if not screens:
            raise RuntimeError("No screens available.")

        if len(screens) == 1:
            pixmap = screens[0].grabWindow(0)
            if pixmap.isNull():
                raise RuntimeError("Failed to capture screen.")
            return pixmap

        geometry = screens[0].geometry()
        for screen in screens[1:]:
            geometry = geometry.united(screen.geometry())

        output = QPixmap(geometry.width(), geometry.height())
        output.fill(QColor(0, 0, 0))
        painter = QPainter(output)
        try:
            for screen in screens:
                grab = screen.grabWindow(0)
                if grab.isNull():
                    raise RuntimeError("Failed to capture screen.")
                screen_geom = screen.geometry()
                target = QRect(
                    screen_geom.x() - geometry.x(),
                    screen_geom.y() - geometry.y(),
                    screen_geom.width(),
                    screen_geom.height(),
                )
                painter.drawPixmap(target, grab)
        finally:
            painter.end()
        return output

    @staticmethod
    def capture_region(rect: QRect) -> QPixmap:
        if rect.width() <= 0 or rect.height() <= 0:
            raise ValueError("Capture region must have positive width and height.")

        intersecting = ScreenshotService.screens_intersecting(rect)
        if not intersecting:
            raise RuntimeError("No screen covers the selected region.")

        output = QPixmap(rect.width(), rect.height())
        output.fill(QColor(0, 0, 0))
        output.setDevicePixelRatio(intersecting[0].devicePixelRatio())
        painter = QPainter(output)
        try:
            for screen in intersecting:
                screen_geom = screen.geometry()
                intersection = screen_geom.intersected(rect)
                local_origin_x = intersection.x() - screen_geom.x()
                local_origin_y = intersection.y() - screen_geom.y()
                grab = screen.grabWindow(
                    0,
                    local_origin_x,
                    local_origin_y,
                    intersection.width(),
                    intersection.height(),
                )
                if grab.isNull():
                    raise RuntimeError("Failed to capture screen.")
                target = QRect(
                    intersection.x() - rect.x(),
                    intersection.y() - rect.y(),
                    intersection.width(),
                    intersection.height(),
                )
                painter.drawPixmap(target, grab)
        finally:
            painter.end()
        return output
