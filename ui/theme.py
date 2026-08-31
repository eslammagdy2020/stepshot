"""Application visual theme and global stylesheet."""

from __future__ import annotations

# Modern dark palette (inspired by pro creative tools)
COLORS = {
    "bg": "#14171c",
    "surface": "#1e222a",
    "surface_raised": "#262b36",
    "surface_hover": "#2f3542",
    "border": "#363d4d",
    "border_focus": "#4f8cff",
    "text": "#eef1f6",
    "text_muted": "#9aa3b2",
    "text_dim": "#6b7380",
    "accent": "#4f8cff",
    "accent_hover": "#6ba1ff",
    "accent_pressed": "#3a73e0",
    "danger": "#f07178",
    "danger_hover": "#ff8a90",
    "success": "#7fd99a",
    "canvas_bg": "#0d0f12",
    "canvas_checker": "#181b22",
    "selection": "#4f8cff",
}


def application_stylesheet() -> str:
    c = COLORS
    return f"""
    * {{
        font-family: "Segoe UI", "Inter", sans-serif;
        font-size: 13px;
    }}

    QMainWindow, QWidget {{
        background-color: {c["bg"]};
        color: {c["text"]};
    }}

    QLabel#PanelTitle {{
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 1.2px;
        color: {c["text_muted"]};
        padding: 4px 0;
    }}

    QLabel#BrandTitle {{
        font-size: 15px;
        font-weight: 700;
        color: {c["text"]};
    }}

    QLabel#BrandSubtitle {{
        font-size: 11px;
        color: {c["text_dim"]};
    }}

    QLabel#HintLabel {{
        color: {c["text_muted"]};
        font-size: 12px;
        line-height: 1.4;
    }}

    QLabel#EmptyStateTitle {{
        font-size: 18px;
        font-weight: 600;
        color: {c["text"]};
    }}

    QLabel#EmptyStateBody {{
        font-size: 13px;
        color: {c["text_muted"]};
    }}

    QWidget#LeftSidebar {{
        background-color: {c["surface"]};
        border-right: 1px solid {c["border"]};
    }}

    QWidget#PropertiesPanel {{
        background-color: {c["surface"]};
        border-left: 1px solid {c["border"]};
    }}

    QWidget#CanvasFrame {{
        background-color: {c["canvas_bg"]};
        border: none;
    }}

    QFrame#CanvasInner {{
        background-color: {c["canvas_checker"]};
        border: 1px solid {c["border"]};
        border-radius: 10px;
    }}

    QToolBar#TopBar {{
        background-color: {c["surface"]};
        border: none;
        border-bottom: 1px solid {c["border"]};
        padding: 6px 12px;
        spacing: 6px;
    }}

    QToolBar#TopBar QToolButton {{
        background-color: transparent;
        color: {c["text"]};
        border: 1px solid transparent;
        border-radius: 8px;
        padding: 7px 14px;
        margin: 0 2px;
        font-weight: 500;
    }}

    QToolBar#TopBar QToolButton:hover {{
        background-color: {c["surface_hover"]};
        border-color: {c["border"]};
    }}

    QToolBar#TopBar QToolButton:pressed {{
        background-color: {c["surface_raised"]};
    }}

    QToolBar#TopBar QToolButton#PrimaryAction {{
        background-color: {c["accent"]};
        color: #ffffff;
        font-weight: 600;
        border: none;
    }}

    QToolBar#TopBar QToolButton#PrimaryAction:hover {{
        background-color: {c["accent_hover"]};
    }}

    QToolBar#TopBar QToolButton#PrimaryAction:pressed {{
        background-color: {c["accent_pressed"]};
    }}

    QToolBar#TopBar::separator {{
        background: {c["border"]};
        width: 1px;
        margin: 4px 8px;
    }}

    QPushButton#ToolButton {{
        background-color: transparent;
        color: {c["text"]};
        border: 1px solid transparent;
        border-radius: 10px;
        padding: 10px 12px;
        text-align: left;
        font-weight: 500;
    }}

    QPushButton#ToolButton:hover {{
        background-color: {c["surface_hover"]};
        border-color: {c["border"]};
    }}

    QPushButton#ToolButton:checked {{
        background-color: {c["accent_pressed"]};
        color: #ffffff;
        border-color: {c["accent"]};
    }}

    QPushButton#DangerButton {{
        background-color: transparent;
        color: {c["danger"]};
        border: 1px solid {c["border"]};
        border-radius: 10px;
        padding: 9px 12px;
        font-weight: 500;
    }}

    QPushButton#DangerButton:hover {{
        background-color: rgba(240, 113, 120, 0.12);
        border-color: {c["danger"]};
    }}

    QWidget#PropertiesPanel,
    QWidget#PropertyPage,
    QStackedWidget#PropertiesStack {{
        background-color: {c["surface"]};
        color: {c["text"]};
    }}

    QWidget#PropertiesPanel QLabel {{
        color: {c["text"]};
        background: transparent;
    }}

    QWidget#PropertiesPanel QLabel#HintLabel {{
        color: {c["text_muted"]};
    }}

    QWidget#PropertiesPanel QGroupBox {{
        background-color: {c["surface_raised"]};
        border: 1px solid {c["border"]};
        border-radius: 12px;
        margin-top: 18px;
        padding: 20px 14px 14px 14px;
        font-weight: 600;
        color: {c["text"]};
    }}

    QWidget#PropertiesPanel QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        top: 2px;
        padding: 2px 8px;
        color: {c["text"]};
        background-color: {c["surface_raised"]};
    }}

    QGroupBox {{
        background-color: {c["surface_raised"]};
        border: 1px solid {c["border"]};
        border-radius: 12px;
        margin-top: 14px;
        padding: 16px 12px 12px 12px;
        font-weight: 600;
        color: {c["text"]};
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 0 6px;
        color: {c["text"]};
    }}

    QSpinBox, QComboBox {{
        background-color: {c["bg"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 6px 10px;
        min-height: 28px;
    }}

    QSpinBox::up-button, QSpinBox::down-button {{
        background-color: {c["surface_hover"]};
        border: none;
        width: 18px;
    }}

    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
        background-color: {c["border"]};
    }}

    QSpinBox::up-arrow, QSpinBox::down-arrow {{
        width: 8px;
        height: 8px;
    }}

    QSpinBox:focus, QComboBox:focus {{
        border-color: {c["border_focus"]};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {c["surface_raised"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        selection-background-color: {c["accent"]};
    }}

    QSlider::groove:horizontal {{
        background: {c["border"]};
        height: 6px;
        border-radius: 3px;
    }}

    QSlider::handle:horizontal {{
        background: {c["accent"]};
        width: 16px;
        height: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }}

    QSlider::sub-page:horizontal {{
        background: {c["accent"]};
        border-radius: 3px;
    }}

    QCheckBox {{
        color: {c["text"]};
        spacing: 8px;
    }}

    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 1px solid {c["border"]};
        background: {c["bg"]};
    }}

    QCheckBox::indicator:checked {{
        background: {c["accent"]};
        border-color: {c["accent"]};
    }}

    QPushButton#ColorSwatch {{
        border: 2px solid {c["border"]};
        border-radius: 8px;
        min-height: 32px;
        min-width: 80px;
        color: {c["text"]};
    }}

    QPushButton#ColorSwatch:hover {{
        border-color: {c["accent"]};
    }}

    QToolBar#TopBar QToolButton[objectName="GlyphButton"] {{
        font-size: 16px;
        font-weight: 700;
        padding: 4px 8px;
        min-width: 32px;
    }}

    QStatusBar {{
        background-color: {c["surface"]};
        color: {c["text_muted"]};
        border-top: 1px solid {c["border"]};
        padding: 4px 12px;
        font-size: 12px;
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 0;
    }}

    QScrollBar::handle:vertical {{
        background: {c["border"]};
        border-radius: 5px;
        min-height: 24px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {c["text_dim"]};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    QGraphicsView {{
        border: none;
        background: transparent;
    }}
    """


def apply_theme(app) -> None:
    from PySide6.QtWidgets import QStyleFactory

    available = QStyleFactory.keys()
    if "Fusion" in available:
        app.setStyle(QStyleFactory.create("Fusion"))
    app.setStyleSheet(application_stylesheet())
