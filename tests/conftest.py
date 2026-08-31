"""Shared pytest fixtures for StepShot automated tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def qapp():
    """Ensure a single QApplication exists for the entire test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    """Redirect QSettings persistence to an in-memory store for every test."""
    store: dict[str, object] = {}

    def fake_load(key: str, default):
        return store.get(key, default)

    def fake_save(key: str, value) -> None:
        store[key] = value

    monkeypatch.setattr("services.settings_service.load", fake_load)
    monkeypatch.setattr("services.settings_service.save", fake_save)
    return store


@pytest.fixture
def sample_pixmap() -> QPixmap:
    """Create a deterministic test screenshot."""
    pixmap = QPixmap(640, 480)
    pixmap.fill(QColor(70, 130, 180))
    painter = QPainter(pixmap)
    painter.setPen(QColor(255, 255, 255))
    painter.drawRect(10, 10, 200, 80)
    painter.drawText(20, 50, "StepShot Test Image")
    painter.end()
    return pixmap


@pytest.fixture
def temp_image_path(tmp_path: Path) -> Path:
    return tmp_path / "stepshot_export"


@pytest.fixture
def mock_clipboard(monkeypatch):
    """Use an in-memory clipboard when the OS clipboard is unavailable."""
    stored: dict[str, QPixmap] = {"pixmap": QPixmap()}

    class _Clipboard:
        def setPixmap(self, pixmap: QPixmap) -> None:
            stored["pixmap"] = pixmap

        def pixmap(self) -> QPixmap:
            return stored["pixmap"]

    clipboard = _Clipboard()
    monkeypatch.setattr(QGuiApplication, "clipboard", lambda: clipboard)
    return clipboard


def left_press(widget, qtbot, pos: QPoint | QPointF) -> None:
    if isinstance(pos, QPointF):
        pos = QPoint(int(pos.x()), int(pos.y()))
    qtbot.mousePress(widget, Qt.LeftButton, pos=pos)


def left_move(widget, qtbot, pos: QPoint | QPointF) -> None:
    if isinstance(pos, QPointF):
        pos = QPoint(int(pos.x()), int(pos.y()))
    qtbot.mouseMove(widget, pos=pos)


def left_release(widget, qtbot, pos: QPoint | QPointF) -> None:
    if isinstance(pos, QPointF):
        pos = QPoint(int(pos.x()), int(pos.y()))
    qtbot.mouseRelease(widget, Qt.LeftButton, pos=pos)


def draw_arrow_on_canvas(canvas, qtbot, start: QPointF, end: QPointF) -> None:
    """Simulate arrow drawing on the annotation canvas."""
    from ui.canvas import ToolMode

    canvas.set_tool_mode(ToolMode.ARROW)
    left_press(canvas.viewport(), qtbot, canvas.mapFromScene(start))
    left_move(canvas.viewport(), qtbot, canvas.mapFromScene(end))
    left_release(canvas.viewport(), qtbot, canvas.mapFromScene(end))


def place_step_marker(canvas, qtbot, position: QPointF) -> None:
    from ui.canvas import ToolMode

    canvas.set_tool_mode(ToolMode.STEP)
    left_press(canvas.viewport(), qtbot, canvas.mapFromScene(position))


def add_text_annotation(canvas, position: QPointF, text: str) -> None:
    """Add text directly to the scene, bypassing the input dialog."""
    from ui.graphics_items import TextGraphicsItem

    item = TextGraphicsItem(
        text,
        position,
        canvas._text_color,
        canvas._text_font_size,
        canvas._text_bold,
    )
    canvas.scene().addItem(item)
    canvas._push_undo_state()


def drag_item_on_canvas(
    canvas, app, scene_start: QPointF, scene_end: QPointF
) -> None:
    """Simulate a Select-tool mouse drag from scene_start to scene_end."""
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QMouseEvent

    viewport = canvas.viewport()
    start = canvas.mapFromScene(scene_start)
    mid = canvas.mapFromScene(QPointF((scene_start + scene_end) / 2))
    end = canvas.mapFromScene(scene_end)

    def send(kind, pos, button, buttons) -> None:
        event = QMouseEvent(
            kind,
            QPointF(pos),
            viewport.mapToGlobal(pos),
            button,
            buttons,
            Qt.NoModifier,
        )
        app.sendEvent(viewport, event)

    send(QEvent.MouseButtonPress, start, Qt.LeftButton, Qt.LeftButton)
    send(QEvent.MouseMove, mid, Qt.LeftButton, Qt.LeftButton)
    send(QEvent.MouseMove, end, Qt.LeftButton, Qt.LeftButton)
    send(QEvent.MouseButtonRelease, end, Qt.LeftButton, Qt.NoButton)


def double_click_on_canvas(canvas, app, scene_pos: QPointF) -> None:
    """Synthesize a left double-click over a scene position on the canvas viewport."""
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QMouseEvent

    viewport = canvas.viewport()
    pos = canvas.mapFromScene(scene_pos)

    def send(kind, button, buttons) -> None:
        event = QMouseEvent(
            kind,
            QPointF(pos),
            viewport.mapToGlobal(pos),
            button,
            buttons,
            Qt.NoModifier,
        )
        app.sendEvent(viewport, event)

    send(QEvent.MouseButtonPress, Qt.LeftButton, Qt.LeftButton)
    send(QEvent.MouseButtonRelease, Qt.LeftButton, Qt.NoButton)
    send(QEvent.MouseButtonDblClick, Qt.LeftButton, Qt.LeftButton)
    send(QEvent.MouseButtonRelease, Qt.LeftButton, Qt.NoButton)


def drag_on_canvas(canvas, app, view_start: QPointF, view_end: QPointF) -> None:
    """Press, move, move, release at the given viewport positions on the canvas."""
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QMouseEvent

    viewport = canvas.viewport()
    start = QPoint(int(view_start.x()), int(view_start.y()))
    end = QPoint(int(view_end.x()), int(view_end.y()))
    mid = QPoint((start.x() + end.x()) // 2, (start.y() + end.y()) // 2)

    def send(kind, pos, button, buttons):
        event = QMouseEvent(
            kind,
            QPointF(pos),
            viewport.mapToGlobal(pos),
            button,
            buttons,
            Qt.NoModifier,
        )
        app.sendEvent(viewport, event)

    send(QEvent.MouseButtonPress, start, Qt.LeftButton, Qt.LeftButton)
    send(QEvent.MouseMove, mid, Qt.LeftButton, Qt.LeftButton)
    send(QEvent.MouseMove, end, Qt.LeftButton, Qt.LeftButton)
    send(QEvent.MouseButtonRelease, end, Qt.LeftButton, Qt.NoButton)
