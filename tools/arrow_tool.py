"""Arrow tool defaults."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor


@dataclass
class ArrowToolSettings:
    color: QColor
    thickness: int = 3

    @classmethod
    def defaults(cls) -> ArrowToolSettings:
        return cls(color=QColor(255, 0, 0), thickness=3)
