"""Rectangle tool defaults."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor


@dataclass
class RectangleToolSettings:
    color: QColor
    thickness: int = 3
    filled: bool = False

    @classmethod
    def defaults(cls) -> RectangleToolSettings:
        return cls(color=QColor(255, 0, 0), thickness=3, filled=False)
