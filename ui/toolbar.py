"""Application toolbars."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QLabel,
    QPushButton,
    QStyle,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ui.canvas import ToolMode
from ui.icon_factory import glyph_icon

TOOL_LABELS: dict[ToolMode, tuple[str, str]] = {
    ToolMode.SELECT: ("Select", "◎"),
    ToolMode.ARROW: ("Arrow", "➤"),
    ToolMode.RECTANGLE: ("Rectangle", "▭"),
    ToolMode.TEXT: ("Text", "T"),
    ToolMode.HIGHLIGHT: ("Highlight", "▬"),
    ToolMode.BLUR: ("Blur", "◌"),
    ToolMode.STEP: ("Step #", "#"),
    ToolMode.PEN: ("Pen", "✏"),
    ToolMode.CROP: ("Crop", "✂"),
}

TOOL_KEYS: dict[ToolMode, str] = {
    ToolMode.SELECT: "V",
    ToolMode.ARROW: "A",
    ToolMode.RECTANGLE: "R",
    ToolMode.TEXT: "T",
    ToolMode.HIGHLIGHT: "H",
    ToolMode.BLUR: "B",
    ToolMode.STEP: "S",
    ToolMode.PEN: "P",
    ToolMode.CROP: "C",
}


class TopToolBar(QToolBar):
    new_capture = Signal()
    full_screen_capture = Signal()
    save_image = Signal()
    copy_image = Signal()
    undo = Signal()
    redo = Signal()
    duplicate = Signal()
    zoom_in = Signal()
    zoom_out = Signal()
    zoom_fit = Signal()
    zoom_reset = Signal()

    def __init__(self) -> None:
        super().__init__("Main")
        self.setObjectName("TopBar")
        self.setMovable(False)
        self.setIconSize(QSize(20, 20))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        style = self.style()
        self.addAction(
            self._action(
                "Capture Region",
                self.new_capture.emit,
                "Ctrl+N",
                primary=True,
                icon=style.standardIcon(QStyle.StandardPixmap.SP_DesktopIcon),
            )
        )
        self.addAction(
            self._action(
                "Full Screen",
                self.full_screen_capture.emit,
                "Ctrl+Shift+N",
                icon=style.standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton),
            )
        )
        self.addSeparator()
        self.addAction(
            self._action(
                "Save",
                self.save_image.emit,
                "Ctrl+S",
                icon=style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton),
            )
        )
        self.addAction(
            self._action(
                "Copy",
                self.copy_image.emit,
                "Ctrl+C",
                icon=style.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton),
            )
        )
        self.addSeparator()
        self.addAction(
            self._glyph_action("Undo", "↶", self.undo.emit, "Ctrl+Z"),
        )
        self.addAction(
            self._glyph_action("Redo", "↷", self.redo.emit, "Ctrl+Y"),
        )
        self.addAction(
            self._glyph_action("Duplicate", "⧉", self.duplicate.emit, "Ctrl+D"),
        )
        self.addSeparator()
        self.addAction(
            self._compact_glyph_action("Zoom In", "+", self.zoom_in.emit, "Ctrl++"),
        )
        self.addAction(
            self._compact_glyph_action("Zoom Out", "−", self.zoom_out.emit, "Ctrl+-"),
        )
        self.addAction(
            self._glyph_action("Zoom Fit", "⤢", self.zoom_fit.emit, "Ctrl+0"),
        )
        self.addAction(
            self._glyph_action("Zoom 100%", "1:1", self.zoom_reset.emit, "Ctrl+1"),
        )

    def _action(
        self,
        text: str,
        slot,
        shortcut: str | None = None,
        primary: bool = False,
        icon=None,
    ) -> QAction:
        action = QAction(text, self)
        if icon is not None and not icon.isNull():
            action.setIcon(icon)
        action.triggered.connect(slot)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        self.addAction(action)
        button = self.widgetForAction(action)
        if button is not None:
            if primary:
                button.setObjectName("PrimaryAction")
            button.setToolTip(f"{text} ({shortcut})" if shortcut else text)
        return action

    def _glyph_action(
        self,
        text: str,
        glyph: str,
        slot,
        shortcut: str | None = None,
    ) -> QAction:
        action = QAction(glyph_icon(glyph), text, self)
        action.triggered.connect(slot)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        self.addAction(action)
        button = self.widgetForAction(action)
        if button is not None:
            button.setToolTip(f"{text} ({shortcut})" if shortcut else text)
        return action

    def _compact_glyph_action(
        self,
        text: str,
        glyph: str,
        slot,
        shortcut: str | None = None,
    ) -> QAction:
        action = QAction(glyph_icon(glyph, size=22), text, self)
        action.triggered.connect(slot)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        self.addAction(action)
        button = self.widgetForAction(action)
        if isinstance(button, QToolButton):
            button.setObjectName("GlyphButton")
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            button.setFixedSize(36, 32)
            button.setToolTip(f"{text} ({shortcut})" if shortcut else text)
        return action


class LeftToolBar(QWidget):
    tool_selected = Signal(ToolMode)
    reset_steps = Signal()
    reset_all = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("LeftSidebar")
        self.setFixedWidth(148)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(4)

        brand = QLabel("StepShot")
        brand.setObjectName("BrandTitle")
        layout.addWidget(brand)

        subtitle = QLabel("Annotate & capture")
        subtitle.setObjectName("BrandSubtitle")
        layout.addWidget(subtitle)

        layout.addSpacing(12)

        tools_label = QLabel("TOOLS")
        tools_label.setObjectName("PanelTitle")
        layout.addWidget(tools_label)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        self._buttons: dict[ToolMode, QPushButton] = {}
        self._shortcuts: dict[ToolMode, QShortcut] = {}
        for mode, (label, glyph) in TOOL_LABELS.items():
            button = QPushButton(f"  {glyph}   {label}")
            button.setObjectName("ToolButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self._group.addButton(button)
            button.clicked.connect(lambda checked, m=mode: self.tool_selected.emit(m))
            layout.addWidget(button)
            self._buttons[mode] = button

            key = TOOL_KEYS[mode]
            button.setToolTip(f"{label} ({key})")
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(
                lambda m=mode: self.tool_selected.emit(m)
            )
            self._shortcuts[mode] = shortcut

        self._buttons[ToolMode.SELECT].setChecked(True)

        layout.addSpacing(8)

        reset_button = QPushButton("  ✕   Reset Steps")
        reset_button.setObjectName("DangerButton")
        reset_button.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_button.clicked.connect(lambda *_args: self.reset_steps.emit())
        layout.addWidget(reset_button)

        reset_all_button = QPushButton("  ↺   Reset All")
        reset_all_button.setObjectName("DangerButton")
        reset_all_button.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_all_button.clicked.connect(lambda *_args: self.reset_all.emit())
        layout.addWidget(reset_all_button)

        layout.addStretch()

        hotkey_hint = QLabel("PrtSc · region\nCtrl+PrtSc · full screen")
        hotkey_hint.setObjectName("HintLabel")
        hotkey_hint.setWordWrap(True)
        layout.addWidget(hotkey_hint)

    def set_tool(self, mode: ToolMode) -> None:
        button = self._buttons.get(mode)
        if button:
            button.setChecked(True)
