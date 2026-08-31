"""Tests for application toolbars."""

from __future__ import annotations

from PySide6.QtGui import QKeySequence

from ui.canvas import ToolMode
from ui.toolbar import LeftToolBar, TopToolBar


class TestTopToolBar:
    def test_has_prd_actions(self, qapp, qtbot):
        toolbar = TopToolBar()
        qtbot.addWidget(toolbar)

        labels = {action.text() for action in toolbar.actions() if action.text()}
        expected = {
            "Capture Region",
            "Full Screen",
            "Save",
            "Copy",
            "Undo",
            "Redo",
            "Zoom In",
            "Zoom Out",
        }
        assert expected.issubset(labels)

    def test_undo_redo_shortcuts(self, qapp, qtbot):
        toolbar = TopToolBar()
        qtbot.addWidget(toolbar)

        shortcuts = {
            action.text(): action.shortcut().toString()
            for action in toolbar.actions()
            if action.text()
        }
        assert shortcuts["Undo"] == QKeySequence("Ctrl+Z").toString()
        assert shortcuts["Redo"] == QKeySequence("Ctrl+Y").toString()

    def test_signals_emit_on_action(self, qapp, qtbot):
        toolbar = TopToolBar()
        qtbot.addWidget(toolbar)

        triggered: list[str] = []

        toolbar.save_image.connect(lambda: triggered.append("save"))
        toolbar.copy_image.connect(lambda: triggered.append("copy"))
        toolbar.undo.connect(lambda: triggered.append("undo"))

        for action in toolbar.actions():
            if action.text() == "Save":
                action.trigger()
            if action.text() == "Copy":
                action.trigger()
            if action.text() == "Undo":
                action.trigger()

        assert triggered == ["save", "copy", "undo"]


class TestLeftToolBar:
    def test_has_core_tools(self, qapp, qtbot):
        toolbar = LeftToolBar()
        qtbot.addWidget(toolbar)

        buttons = toolbar.findChildren(type(toolbar._buttons[ToolMode.SELECT]))
        labels = {button.text() for button in buttons}
        for name in (
            "Select",
            "Arrow",
            "Rectangle",
            "Text",
            "Highlight",
            "Blur",
            "Step #",
        ):
            assert any(name in label for label in labels), f"{name} not in toolbar"

    def test_tool_selected_signal(self, qapp, qtbot):
        toolbar = LeftToolBar()
        qtbot.addWidget(toolbar)

        selected: list[ToolMode] = []
        toolbar.tool_selected.connect(selected.append)

        toolbar._buttons[ToolMode.ARROW].click()
        assert selected == [ToolMode.ARROW]

    def test_reset_steps_signal(self, qapp, qtbot):
        toolbar = LeftToolBar()
        qtbot.addWidget(toolbar)

        from PySide6.QtWidgets import QPushButton

        reset_buttons = [
            b
            for b in toolbar.findChildren(QPushButton)
            if "Reset Steps" in b.text()
        ]
        assert len(reset_buttons) == 1

        reset_called = []
        toolbar.reset_steps.connect(lambda: reset_called.append(True))
        reset_buttons[0].click()
        assert reset_called == [True]

    def test_set_tool_checks_button(self, qapp, qtbot):
        toolbar = LeftToolBar()
        qtbot.addWidget(toolbar)

        toolbar.set_tool(ToolMode.TEXT)
        assert toolbar._buttons[ToolMode.TEXT].isChecked()
