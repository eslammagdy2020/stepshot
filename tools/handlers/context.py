"""Handler context interface for tool handlers."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor

from models.step_marker import StepCounter
from ui.graphics_items import TextGraphicsItem


@runtime_checkable
class HandlerContext(Protocol):
    def add_item(self, item) -> None:
        ...

    def remove_item(self, item) -> None:
        ...

    def push_undo_state(self) -> None:
        ...

    def emit_image_changed(self) -> None:
        ...

    def apply_blur_region(self, rect: QRectF) -> None:
        ...

    def apply_crop(self, rect: QRectF) -> bool:
        ...

    def get_arrow_settings(self) -> tuple[QColor, int]:
        ...

    def get_rectangle_settings(self) -> tuple[QColor, int, bool]:
        ...

    def get_highlight_settings(self) -> tuple[QColor, int]:
        ...

    def get_step_settings(self) -> tuple[QColor, int, StepCounter]:
        ...

    def get_text_settings(self) -> tuple[QColor, int, bool]:
        ...

    def get_pen_settings(self) -> tuple[QColor, int]:
        ...

    def get_text_item_at(self, scene_pos: QPointF) -> TextGraphicsItem | None:
        ...

    def start_text_edit(self, item: TextGraphicsItem, *, is_new: bool) -> None:
        ...

    def finalize_text_edit(self) -> None:
        ...

    def is_editing_text(self) -> bool:
        ...


__all__ = ["HandlerContext"]