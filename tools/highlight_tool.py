"""Highlight tool defaults."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor


@dataclass
class HighlightToolSettings:
    color: QColor
    opacity: int = 128

    @classmethod
    def defaults(cls) -> HighlightToolSettings:
        return cls(color=QColor(255, 255, 0), opacity=128)
