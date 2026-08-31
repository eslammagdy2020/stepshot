"""Pen tool settings."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor


@dataclass
class PenToolSettings:
    color: QColor
    thickness: int = 3

    @classmethod
    def defaults(cls) -> "PenToolSettings":
        return cls(QColor(255, 0, 0), 3)
