"""Blur tool defaults."""

from __future__ import annotations

from dataclasses import dataclass

from services.image_effects import BlurMode


@dataclass
class BlurToolSettings:
    mode: BlurMode = BlurMode.BLUR
    strength: int = 12

    @classmethod
    def defaults(cls) -> BlurToolSettings:
        return cls()
