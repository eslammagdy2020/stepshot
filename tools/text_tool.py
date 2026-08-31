"""Text tool defaults."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor


@dataclass
class TextToolSettings:
    color: QColor
    font_size: int = 14
    bold: bool = False

    @classmethod
    def defaults(cls) -> TextToolSettings:
        return cls(color=QColor(255, 0, 0), font_size=14, bold=False)
