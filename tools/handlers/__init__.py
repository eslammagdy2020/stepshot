"""Per-tool mouse handlers for the annotation canvas."""

from __future__ import annotations

from tools.handlers.arrow import ArrowHandler
from tools.handlers.base import RectDragHandler, ToolHandler
from tools.handlers.blur import BlurHandler
from tools.handlers.crop import CropHandler
from tools.handlers.highlight import HighlightHandler
from tools.handlers.pen import PenHandler
from tools.handlers.rectangle import RectangleHandler
from tools.handlers.step import StepHandler
from tools.handlers.text import TextHandler


def build_handlers(canvas) -> dict:
    from ui.canvas import ToolMode

    handlers = {
        ToolMode.ARROW: ArrowHandler(),
        ToolMode.RECTANGLE: RectangleHandler(),
        ToolMode.HIGHLIGHT: HighlightHandler(),
        ToolMode.BLUR: BlurHandler(),
        ToolMode.CROP: CropHandler(),
        ToolMode.PEN: PenHandler(),
        ToolMode.STEP: StepHandler(),
        ToolMode.TEXT: TextHandler(),
    }
    for handler in handlers.values():
        handler.attach(canvas)
    return handlers


__all__ = [
    "ArrowHandler",
    "BlurHandler",
    "CropHandler",
    "HighlightHandler",
    "PenHandler",
    "RectangleHandler",
    "RectDragHandler",
    "StepHandler",
    "TextHandler",
    "ToolHandler",
    "build_handlers",
]
