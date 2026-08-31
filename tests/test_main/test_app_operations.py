"""Tests for app-level operations: logging setup and capture-failure reporting."""

from __future__ import annotations

import logging
import logging.handlers

import pytest
from PySide6.QtCore import QRect

import main
from main import StepShotApp
from services.screenshot_service import ScreenshotService


@pytest.fixture
def logging_to_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(main.logger, "handlers", [])
    monkeypatch.setattr(
        main.QStandardPaths, "writableLocation", staticmethod(lambda _: str(tmp_path))
    )
    yield tmp_path
    for handler in main.logger.handlers:
        handler.close()


@pytest.fixture
def app_stub(monkeypatch):
    """A StepShotApp without a second QApplication, with dialogs stubbed out."""
    instance = StepShotApp.__new__(StepShotApp)
    instance.main_window = None
    instance._pending_region = None
    monkeypatch.setattr(
        StepShotApp, "_show_capture_error", lambda self, message: None
    )
    return instance


class TestLoggingSetup:
    def test_creates_rotating_file_handler(self, logging_to_tmp):
        main._setup_logging()

        handlers = main.logger.handlers
        assert len(handlers) == 1
        assert isinstance(handlers[0], logging.handlers.RotatingFileHandler)

        main.logger.info("hello")
        handlers[0].flush()
        assert "hello" in (logging_to_tmp / "stepshot.log").read_text(encoding="utf-8")

    def test_is_idempotent(self, logging_to_tmp):
        main._setup_logging()
        main._setup_logging()

        assert len(main.logger.handlers) == 1


class TestCaptureFailureLogging:
    def test_full_screen_failure_is_logged(self, app_stub, monkeypatch, caplog):
        def fail() -> None:
            raise RuntimeError("no screens")

        monkeypatch.setattr(ScreenshotService, "capture_full_screen", fail)

        with caplog.at_level(logging.ERROR, logger="stepshot"):
            app_stub._capture_full_screen()

        assert "no screens" in caplog.text

    def test_region_failure_is_logged(self, app_stub, monkeypatch, caplog):
        def fail(_rect: QRect) -> None:
            raise RuntimeError("grab failed")

        monkeypatch.setattr(ScreenshotService, "capture_region", fail)
        app_stub._pending_region = QRect(0, 0, 10, 10)

        with caplog.at_level(logging.ERROR, logger="stepshot"):
            app_stub._capture_pending_region()

        assert "grab failed" in caplog.text
