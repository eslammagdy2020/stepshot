"""Base classes for per-tool mouse handlers."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF

from tools.handlers.context import HandlerContext


class ToolHandler:
    def attach(self, context: HandlerContext) -> None:
        self.context = context

    def on_press(self, scene_pos: QPointF) -> bool:
        del scene_pos
        return False

    def on_move(self, scene_pos: QPointF) -> None:
        del scene_pos

    def on_release(self, scene_pos: QPointF) -> bool:
        del scene_pos
        return False

    def cancel(self) -> None:
        pass


class RectDragHandler(ToolHandler):
    MIN_SIZE = 5

    def __init__(self) -> None:
        self._start: QPointF | None = None
        self._preview = None

    def on_press(self, scene_pos: QPointF) -> bool:
        self._start = scene_pos
        self._preview = self._create_preview(scene_pos)
        self.context.add_item(self._preview)
        return False

    def on_move(self, scene_pos: QPointF) -> None:
        if self._preview is None or self._start is None:
            return
        self._update_preview(
            self._preview, QRectF(self._start, scene_pos).normalized()
        )
        self._preview.prepareGeometryChange()
        self._preview.update()

    def on_release(self, scene_pos: QPointF) -> bool:
        if self._preview is None or self._start is None:
            return False
        rect = QRectF(self._start, scene_pos).normalized()
        preview = self._preview
        self._preview = None
        self._start = None
        self.context.remove_item(preview)
        if rect.width() >= self.MIN_SIZE and rect.height() >= self.MIN_SIZE:
            if self._commit(rect, preview):
                self.context.push_undo_state()
                self.context.emit_image_changed()
        return True

    def cancel(self) -> None:
        if self._preview is not None:
            self.context.remove_item(self._preview)
        self._preview = None
        self._start = None

    def _create_preview(self, scene_pos: QPointF):
        raise NotImplementedError

    def _update_preview(self, preview, rect: QRectF) -> None:
        preview.rect = rect

    def _commit(self, rect: QRectF, preview) -> bool:
        del rect, preview
        raise NotImplementedError
