"""Persistent user preferences via QSettings."""

from __future__ import annotations

from PySide6.QtCore import QSettings

ORG = "StepShot"
APP = "StepShot"


def load(key: str, default):
    return QSettings(ORG, APP).value(key, default)


def save(key: str, value) -> None:
    QSettings(ORG, APP).setValue(key, value)
