"""StepShot entry point."""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path

from PySide6.QtCore import (
    QObject,
    QStandardPaths,
    QTimer,
    Signal,
    QRect,
    Qt,
)
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QMessageBox

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.screenshot_service import ScreenshotService
from ui.main_window import MainWindow
from ui.region_selector import RegionSelector
from ui.theme import apply_theme

logger = logging.getLogger("stepshot")


def _setup_logging() -> None:
    if logger.handlers:
        return
    log_dir = Path(
        QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppLocalDataLocation
        )
    )
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        log_dir = Path.cwd()
    handler = logging.handlers.RotatingFileHandler(
        log_dir / "stepshot.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class CaptureSignals(QObject):
    region_requested = Signal()
    full_screen_requested = Signal()


class StepShotApp:
    def __init__(self) -> None:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("StepShot")
        self.app.setOrganizationName("StepShot")
        apply_theme(self.app)
        _setup_logging()

        self.capture_signals = CaptureSignals()
        self.main_window = MainWindow()
        self.region_selector: RegionSelector | None = None
        self._pending_region: QRect | None = None

        # Keyboard callbacks fire on a worker thread; marshal onto the Qt thread
        # with an explicit queued connection so widget access stays main-thread-only.
        self.capture_signals.region_requested.connect(
            self.start_region_capture, Qt.ConnectionType.QueuedConnection
        )
        self.capture_signals.full_screen_requested.connect(
            self.start_full_screen_capture, Qt.ConnectionType.QueuedConnection
        )
        self.main_window.region_capture_requested.connect(self.start_region_capture)
        self.main_window.full_screen_capture_requested.connect(
            self.start_full_screen_capture
        )

        self._register_hotkeys()

    def _register_hotkeys(self) -> None:
        try:
            import keyboard
        except ImportError:
            logger.warning("keyboard package unavailable; global hotkeys disabled")
            self.main_window.show()
            QMessageBox.information(
                self.main_window,
                "Hotkeys Unavailable",
                "Global hotkeys require the 'keyboard' package.\n"
                "Use toolbar buttons or install keyboard:\n"
                "pip install keyboard",
            )
            return

        try:
            keyboard.add_hotkey(
                "print screen",
                lambda: self.capture_signals.region_requested.emit(),
                suppress=True,
            )
            keyboard.add_hotkey(
                "ctrl+print screen",
                lambda: self.capture_signals.full_screen_requested.emit(),
                suppress=True,
            )
        except Exception:
            logger.exception("failed to register global hotkeys")
            self.main_window.show()
            QMessageBox.warning(
                self.main_window,
                "Hotkeys Unavailable",
                "Failed to register global hotkeys.\n"
                "Use the toolbar Capture buttons instead.",
            )

    def start_region_capture(self) -> None:
        self.main_window.hide()
        QTimer.singleShot(250, self._show_region_selector)

    def _show_region_selector(self) -> None:
        self.region_selector = RegionSelector()
        self.region_selector.capture_completed.connect(self._on_region_selected)
        self.region_selector.capture_cancelled.connect(self._on_capture_cancelled)
        self.region_selector.show()

    def start_full_screen_capture(self) -> None:
        self.main_window.hide()
        QTimer.singleShot(150, self._capture_full_screen)

    def _capture_full_screen(self) -> None:
        try:
            pixmap = ScreenshotService.capture_full_screen()
        except RuntimeError as exc:
            logger.error("full-screen capture failed: %s", exc)
            self._show_capture_error(str(exc))
            return
        self.main_window.add_screenshot(pixmap, "fullscreen")

    def _on_region_selected(self, rect: QRect) -> None:
        self._pending_region = rect
        self._dismiss_region_selector()
        QApplication.processEvents()
        QTimer.singleShot(200, self._capture_pending_region)

    def _dismiss_region_selector(self) -> None:
        if self.region_selector is None:
            return
        self.region_selector.hide()
        self.region_selector.close()
        self.region_selector.deleteLater()
        self.region_selector = None
        QApplication.processEvents()

    def _capture_pending_region(self) -> None:
        if self._pending_region is None:
            return

        rect = self._pending_region
        self._pending_region = None
        try:
            pixmap = ScreenshotService.capture_region(rect)
        except (RuntimeError, ValueError) as exc:
            logger.error("region capture failed: %s", exc)
            self._show_capture_error(str(exc))
            return
        self.main_window.add_screenshot(pixmap, "region")

    def _on_capture_cancelled(self) -> None:
        self.main_window.show()
        self.main_window.raise_()

    def _show_capture_error(self, message: str) -> None:
        self.main_window.show()
        QMessageBox.critical(self.main_window, "Capture Failed", message)

    def run(self) -> int:
        self.main_window.show()
        return self.app.exec()


def main() -> int:
    if "--smoke-test" in sys.argv:
        _smoke_test()
        return 0
    return StepShotApp().run()


def _smoke_test() -> int:
    """Initialize Qt offscreen and exit without registering hotkeys or showing UI.

    Used by CI to confirm a fresh build boots and shuts down without user
    input. Sets QT_QPA_PLATFORM=offscreen, instantiates a QApplication, runs
    one event-loop tick, logs the screen count, and forces termination via
    os._exit so the PyInstaller runw bootloader releases the host process.
    """
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication(sys.argv)
    app.setApplicationName("StepShot")
    app.setOrganizationName("StepShot")
    apply_theme(app)
    _setup_logging()
    logger.info("smoke-test: Qt initialized, %d screens", len(app.screens()))
    app.processEvents()
    os._exit(0)


if __name__ == "__main__":
    raise SystemExit(main())
