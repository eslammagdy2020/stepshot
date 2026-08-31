"""Step tool defaults."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor


@dataclass
class StepToolSettings:
    color: QColor
    size: int = 28

    @classmethod
    def defaults(cls) -> StepToolSettings:
        return cls(color=QColor(255, 0, 0), size=28)
