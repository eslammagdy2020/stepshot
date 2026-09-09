"""Annotation canvas and tool handling."""

from __future__ import annotations

import logging
import time
from enum import Enum, auto

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QKeyEvent,
    QPainter,
    QPainterPath,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QLabel,
)

from models.document_history import (
    AnnotationRecord,
    DocumentHistory,
    DocumentState,
    ImageValue,
    RejectedMutation,
)
from models.screenshot_inventory import ScreenshotInventory, ScreenshotRecord
from models.step_marker import StepCounter
from services import settings_service
from services.image_effects import BlurMode, apply_region_effect
from tools.arrow_tool import ArrowToolSettings
from tools.blur_tool import BlurToolSettings
from tools.handlers import ToolHandler, build_handlers
from tools.highlight_tool import HighlightToolSettings
from tools.pen_tool import PenToolSettings
from tools.rectangle_tool import RectangleToolSettings
from tools.step_tool import StepToolSettings
from tools.text_tool import TextToolSettings
from ui.annotation_adapters import (
    build_canvas_registry,
    capture_annotation,
    capturable_types,
    image_value_to_qpixmap,
    qpixmap_to_image_value,
    restore_annotation,
)
from ui.graphics_items import (
    ArrowGraphicsItem,
    BlurPatchGraphicsItem,
    HighlightGraphicsItem,
    PenStrokeGraphicsItem,
    RectangleGraphicsItem,
    StepMarkerGraphicsItem,
    TextGraphicsItem,
)
from ui.resize_handles import Handle, HandleRole, ResizeHandleLayer

logger = logging.getLogger("stepshot")

_CAPTURABLE_TYPES = capturable_types()


class ToolMode(Enum):
    SELECT = auto()
    ARROW = auto()
    RECTANGLE = auto()
    TEXT = auto()
    HIGHLIGHT = auto()
    BLUR = auto()
    STEP = auto()
    PEN = auto()
    CROP = auto()


MIN_ZOOM = 0.05
MAX_ZOOM = 16.0


class AnnotationCanvas(QGraphicsView):
    selection_changed = Signal(object)
    image_changed = Signal()
    inventory_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setObjectName("AnnotationCanvas")
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setBackgroundBrush(Qt.BrushStyle.NoBrush)

        self._placeholder = QLabel(self)
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setObjectName("EmptyState")
        self._placeholder.setText(
            "<p style='font-size:18px; font-weight:600; color:#eef1f6;'>"
            "No screenshot yet</p>"
            "<p style='color:#9aa3b2; margin-top:8px;'>"
            "Press <b>PrtSc</b> or click <b>Capture Region</b> to begin</p>"
        )
        self._placeholder.setTextFormat(Qt.TextFormat.RichText)
        self._placeholder.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._show_placeholder()

        self._background_item: QGraphicsPixmapItem | None = None
        self._tool_mode = ToolMode.SELECT
        self._step_counter = StepCounter()

        self._handlers = build_handlers(self)
        self._active_handler: ToolHandler | None = None

        rectangle_defaults = RectangleToolSettings.defaults()
        highlight_defaults = HighlightToolSettings.defaults()
        blur_defaults = BlurToolSettings.defaults()
        arrow_defaults = ArrowToolSettings.defaults()
        step_defaults = StepToolSettings.defaults()
        text_defaults = TextToolSettings.defaults()
        pen_defaults = PenToolSettings.defaults()

        self._arrow_color = QColor(
            settings_service.load("arrow/color", arrow_defaults.color)
        )
        self._arrow_thickness = int(
            settings_service.load("arrow/thickness", arrow_defaults.thickness)
        )
        self._rectangle_color = QColor(
            settings_service.load("rectangle/color", rectangle_defaults.color)
        )
        self._rectangle_thickness = int(
            settings_service.load(
                "rectangle/thickness", rectangle_defaults.thickness
            )
        )
        self._rectangle_filled = bool(
            settings_service.load("rectangle/filled", rectangle_defaults.filled)
        )
        self._highlight_color = QColor(
            settings_service.load("highlight/color", highlight_defaults.color)
        )
        self._highlight_opacity = int(
            settings_service.load("highlight/opacity", highlight_defaults.opacity)
        )
        self._blur_mode = BlurMode(
            settings_service.load("blur/mode", blur_defaults.mode.value)
        )
        self._blur_strength = int(
            settings_service.load("blur/strength", blur_defaults.strength)
        )
        self._step_color = QColor(
            settings_service.load("step/color", step_defaults.color)
        )
        self._step_size = int(settings_service.load("step/size", step_defaults.size))
        self._text_color = QColor(
            settings_service.load("text/color", text_defaults.color)
        )
        self._text_font_size = int(
            settings_service.load("text/font_size", text_defaults.font_size)
        )
        self._text_bold = bool(
            settings_service.load("text/bold", text_defaults.bold)
        )
        self._pen_color = QColor(settings_service.load("pen/color", pen_defaults.color))
        self._pen_thickness = int(
            settings_service.load("pen/thickness", pen_defaults.thickness)
        )

        self._registry = build_canvas_registry()
        self._history = DocumentHistory(self._registry)
        self._inventory = ScreenshotInventory()
        self._bg_image_value = None
        self._bg_image_cache_key: int | None = None
        self._original_pixmap: QPixmap | None = None
        self._editing_text_item: TextGraphicsItem | None = None
        self._editing_text_before: str | None = None
        self._editing_text_is_new: bool = False
        self._drag_positions: dict | None = None

        self._resize_layer = ResizeHandleLayer(self.viewport())
        self._resize_layer.hide()
        self._resize_handle: Handle | None = None
        self._resize_geometry_before: tuple[QPointF, QPointF] | QRectF | None = None
        self._resize_pos_before: QPointF | None = None
        self._resize_item: ArrowGraphicsItem | RectangleGraphicsItem | HighlightGraphicsItem | None = None
        self._scene.selectionChanged.connect(self._refresh_resize_layer)

        self._property_timer = QTimer(self)
        self._property_timer.setSingleShot(True)
        self._property_timer.setInterval(400)
        self._property_timer.timeout.connect(self._push_undo_state)

        self._checker_brush = self._build_checker_brush()

    @property
    def tool_mode(self) -> ToolMode:
        return self._tool_mode

    def get_tool_settings(self) -> dict[str, object]:
        return {
            "arrow_color": QColor(self._arrow_color),
            "arrow_thickness": self._arrow_thickness,
            "rectangle_color": QColor(self._rectangle_color),
            "rectangle_thickness": self._rectangle_thickness,
            "rectangle_filled": self._rectangle_filled,
            "highlight_color": QColor(self._highlight_color),
            "highlight_opacity": self._highlight_opacity,
            "blur_mode": self._blur_mode,
            "blur_strength": self._blur_strength,
            "step_color": QColor(self._step_color),
            "step_size": self._step_size,
            "text_color": QColor(self._text_color),
            "text_font_size": self._text_font_size,
            "text_bold": self._text_bold,
            "pen_color": QColor(self._pen_color),
            "pen_thickness": self._pen_thickness,
        }

    def _save_tool_defaults(self) -> None:
        settings_service.save("arrow/color", self._arrow_color)
        settings_service.save("arrow/thickness", self._arrow_thickness)
        settings_service.save("rectangle/color", self._rectangle_color)
        settings_service.save("rectangle/thickness", self._rectangle_thickness)
        settings_service.save("rectangle/filled", self._rectangle_filled)
        settings_service.save("highlight/color", self._highlight_color)
        settings_service.save("highlight/opacity", self._highlight_opacity)
        settings_service.save("blur/mode", self._blur_mode.value)
        settings_service.save("blur/strength", self._blur_strength)
        settings_service.save("step/color", self._step_color)
        settings_service.save("step/size", self._step_size)
        settings_service.save("text/color", self._text_color)
        settings_service.save("text/font_size", self._text_font_size)
        settings_service.save("text/bold", self._text_bold)
        settings_service.save("pen/color", self._pen_color)
        settings_service.save("pen/thickness", self._pen_thickness)

    @property
    def step_counter(self) -> StepCounter:
        return self._step_counter

    def set_tool_mode(self, mode: ToolMode) -> None:
        self._finalize_text_edit()
        self._tool_mode = mode
        self._cancel_previews()
        self._cancel_resize_tracking()
        if mode == ToolMode.SELECT:
            self.setDragMode(QGraphicsView.RubberBandDrag)
        else:
            self.setDragMode(QGraphicsView.NoDrag)
            self._scene.clearSelection()

    def load_image(self, pixmap: QPixmap) -> None:
        self.add_screenshot(pixmap, "region")

    def set_inventory(self, inventory: ScreenshotInventory) -> None:
        self._finalize_text_edit()
        self._flush_pending_property_undo()
        self._cancel_resize_tracking()
        self._inventory = inventory
        record = inventory.get_current()
        if record is None:
            self._clear_canvas_to_empty()
        else:
            self._load_record(record)
        self.inventory_changed.emit()
        self.image_changed.emit()

    def add_screenshot(self, pixmap: QPixmap, source: str) -> bool:
        if pixmap.isNull():
            return False
        self._finalize_text_edit()
        self._flush_pending_property_undo()
        self._cancel_resize_tracking()
        self._drag_positions = None
        if self._background_item is not None and len(self._inventory) > 0:
            self._inventory.update_current(self._capture_document_state())
        image_value = qpixmap_to_image_value(pixmap)
        state = DocumentState(
            version=DocumentHistory.DOCUMENT_VERSION,
            image=image_value,
            annotations=(),
            step_counter=1,
        )
        history = DocumentHistory(self._registry, initial_state=state)
        record = ScreenshotRecord(
            original=image_value,
            current=state,
            timestamp=time.time(),
            source=source,
            history=history,
        )
        self._inventory.add(record)
        self._load_record(record)
        self.inventory_changed.emit()
        self.image_changed.emit()
        return True

    def switch_to(self, index: int) -> bool:
        if len(self._inventory) == 0:
            return False
        if index == self._inventory.current_index:
            return False
        if not 0 <= index < len(self._inventory):
            return False
        self._finalize_text_edit()
        self._flush_pending_property_undo()
        self._cancel_resize_tracking()
        self._drag_positions = None
        self._cancel_previews()
        self._active_handler = None
        if self._background_item is not None:
            self._inventory.update_current(self._capture_document_state())
        record = self._inventory.switch_to(index)
        if record is None:
            return False
        self._load_record(record)
        self.inventory_changed.emit()
        self.image_changed.emit()
        return True

    def next_screenshot(self) -> bool:
        return self.switch_to(self._inventory.current_index + 1)

    def prev_screenshot(self) -> bool:
        return self.switch_to(self._inventory.current_index - 1)

    def remove_current(self) -> bool:
        if len(self._inventory) == 0:
            return False
        self._finalize_text_edit()
        self._flush_pending_property_undo()
        self._cancel_resize_tracking()
        self._drag_positions = None
        self._cancel_previews()
        self._active_handler = None
        self._inventory.remove_at(self._inventory.current_index)
        record = self._inventory.get_current()
        if record is None:
            self._clear_canvas_to_empty()
        else:
            self._load_record(record)
        self.inventory_changed.emit()
        self.image_changed.emit()
        return True

    def clear_inventory(self) -> None:
        self._finalize_text_edit()
        self._flush_pending_property_undo()
        self._cancel_resize_tracking()
        self._drag_positions = None
        self._cancel_previews()
        self._active_handler = None
        self._inventory.clear()
        self._clear_canvas_to_empty()
        self.inventory_changed.emit()
        self.image_changed.emit()

    def _clear_canvas_to_empty(self) -> None:
        self._scene.clear()
        self._background_item = None
        self._original_pixmap = None
        self._bg_image_value = None
        self._bg_image_cache_key = None
        self._step_counter.reset()
        self._history = DocumentHistory(self._registry)
        self._scene.clearSelection()
        self.selection_changed.emit(None)
        self._show_placeholder()

    def _load_record(self, record: ScreenshotRecord) -> None:
        self._original_pixmap = image_value_to_qpixmap(record.original)
        self._scene.clear()
        self._background_item = self._scene.addPixmap(
            image_value_to_qpixmap(record.current.image)
            if record.current.image is not None
            else image_value_to_qpixmap(record.original)
        )
        self._background_item.setZValue(-1)
        self._scene.setSceneRect(self._background_item.boundingRect())
        self.zoom_to_fit()
        self._step_counter.reset_to(record.current.step_counter)
        self._active_handler = None
        self._bg_image_value = None
        self._bg_image_cache_key = None
        self._restore_scene_only(record.current)
        if record.history is None:
            self._history = DocumentHistory(self._registry, initial_state=record.current)
            self._inventory.set_history(self._history)
        else:
            self._history = record.history
            if self._history.current != record.current:
                self._inventory.update_current(self._history.current)
                record = self._inventory.get_current() or record
                self._restore_scene_only(record.current)
        self._scene.clearSelection()
        self.selection_changed.emit(None)
        self._placeholder.hide()

    def _restore_scene_only(self, state: DocumentState) -> None:
        restored_items = []
        for record_item in reversed(state.annotations):
            restored_items.append(restore_annotation(self._registry, record_item))
        for item in list(self._scene.items()):
            if item is self._background_item:
                continue
            self._scene.removeItem(item)
        if self._background_item is not None and state.image is not None:
            self._background_item.setPixmap(image_value_to_qpixmap(state.image))
            self._bg_image_value = state.image
            self._bg_image_cache_key = self._background_item.pixmap().cacheKey()
        self._step_counter.reset_to(state.step_counter)
        for item in restored_items:
            self._scene.addItem(item)
        if self._background_item is not None:
            self._scene.setSceneRect(self._background_item.boundingRect())

    @property
    def inventory(self) -> ScreenshotInventory:
        return self._inventory

    @property
    def inventory_count(self) -> int:
        return len(self._inventory)

    @property
    def current_index_1based(self) -> int:
        if len(self._inventory) == 0:
            return 0
        return self._inventory.current_index + 1

    def can_go_next(self) -> bool:
        return self._inventory.can_go_next()

    def can_go_prev(self) -> bool:
        return self._inventory.can_go_prev()

    def _reset_history(self) -> None:
        self._history = DocumentHistory(
            self._registry, initial_state=self._capture_document_state()
        )

    def zoom_to_fit(self) -> None:
        if self._background_item is None:
            return
        self.fitInView(self._background_item, Qt.AspectRatioMode.KeepAspectRatio)
        self.clamp_zoom()
        self._resize_layer.resize_to_viewport(self)

    def clamp_zoom(self) -> None:
        scale = self.transform().m11()
        if scale <= 0:
            return
        target = min(max(scale, MIN_ZOOM), MAX_ZOOM)
        if target != scale:
            factor = target / scale
            self.scale(factor, factor)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._placeholder.setGeometry(self.rect())
        self._resize_layer.resize_to_viewport(self)

    def scrollContentsBy(self, dx: int, dy: int) -> None:
        super().scrollContentsBy(dx, dy)
        self._resize_layer.resize_to_viewport(self)

    def scale(self, sx: float, sy: float) -> None:
        super().scale(sx, sy)
        self._resize_layer.resize_to_viewport(self)

    def resetTransform(self) -> None:
        super().resetTransform()
        self._resize_layer.resize_to_viewport(self)

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        del rect
        painter.fillRect(self.viewport().rect(), self._checker_brush)

    def _build_checker_brush(self):
        from PySide6.QtGui import QBrush

        checker = 16
        tile = QPixmap(checker * 2, checker * 2)
        tile.fill(QColor("#14171c"))
        painter = QPainter(tile)
        painter.fillRect(0, 0, checker, checker, QColor("#1a1e26"))
        painter.fillRect(checker, checker, checker, checker, QColor("#1a1e26"))
        painter.end()
        return QBrush(tile)

    def _show_placeholder(self) -> None:
        self._placeholder.show()
        self._placeholder.raise_()

    def render_to_pixmap(self) -> QPixmap:
        if self._background_item is None:
            raise RuntimeError("No screenshot loaded.")

        source = self._background_item.boundingRect()
        background = self._background_item.pixmap()
        output = QPixmap(background.width(), background.height())
        output.fill(Qt.transparent)

        painter = QPainter(output)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self._scene.render(
            painter,
            QRectF(0, 0, output.width(), output.height()),
            source,
        )
        painter.end()
        return output

    def set_arrow_color(self, color: QColor) -> None:
        self._arrow_color = color
        item = self._selected_arrow()
        if item:
            item.set_color(color)
            self._schedule_property_undo()
        self._save_tool_defaults()

    def set_arrow_thickness(self, thickness: int) -> None:
        self._arrow_thickness = thickness
        item = self._selected_arrow()
        if item:
            item.set_thickness(thickness)
            self._schedule_property_undo()
        self._save_tool_defaults()

    def set_step_color(self, color: QColor) -> None:
        self._step_color = color
        item = self._selected_step()
        if item:
            item.set_color(color)
            self._schedule_property_undo()
        self._save_tool_defaults()

    def set_step_size(self, size: int) -> None:
        self._step_size = size
        item = self._selected_step()
        if item:
            item.set_size(size)
            self._schedule_property_undo()
        self._save_tool_defaults()

    def set_text_color(self, color: QColor) -> None:
        self._text_color = color
        item = self._selected_text()
        if item:
            item.set_color(color)
            self._schedule_property_undo()
        self._save_tool_defaults()

    def set_text_font_size(self, font_size: int) -> None:
        self._text_font_size = font_size
        item = self._selected_text()
        if item:
            item.set_font_size(font_size)
            self._schedule_property_undo()
        self._save_tool_defaults()

    def set_text_bold(self, bold: bool) -> None:
        self._text_bold = bold
        item = self._selected_text()
        if item:
            item.set_bold(bold)
            self._schedule_property_undo()
        self._save_tool_defaults()

    def set_rectangle_color(self, color: QColor) -> None:
        self._rectangle_color = color
        item = self._selected_rectangle()
        if item:
            item.set_color(color)
            self._schedule_property_undo()
        self._save_tool_defaults()

    def set_rectangle_thickness(self, thickness: int) -> None:
        self._rectangle_thickness = thickness
        item = self._selected_rectangle()
        if item:
            item.set_thickness(thickness)
            self._schedule_property_undo()
        self._save_tool_defaults()

    def set_rectangle_filled(self, filled: bool) -> None:
        self._rectangle_filled = filled
        item = self._selected_rectangle()
        if item:
            item.set_filled(filled)
            self._schedule_property_undo()
        self._save_tool_defaults()

    def set_highlight_color(self, color: QColor) -> None:
        self._highlight_color = color
        item = self._selected_highlight()
        if item:
            item.set_color(color)
            self._schedule_property_undo()
        self._save_tool_defaults()

    def set_highlight_opacity(self, opacity: int) -> None:
        self._highlight_opacity = opacity
        item = self._selected_highlight()
        if item:
            item.set_opacity(opacity)
            self._schedule_property_undo()
        self._save_tool_defaults()

    def set_blur_mode(self, mode: BlurMode) -> None:
        self._blur_mode = mode
        self._save_tool_defaults()

    def set_blur_strength(self, strength: int) -> None:
        self._blur_strength = strength
        self._save_tool_defaults()

    def set_pen_color(self, color: QColor) -> None:
        self._pen_color = color
        item = self._selected_pen()
        if item:
            item.set_color(color)
            self._schedule_property_undo()
        self._save_tool_defaults()

    def set_pen_thickness(self, thickness: int) -> None:
        self._pen_thickness = thickness
        item = self._selected_pen()
        if item:
            item.set_thickness(thickness)
            self._schedule_property_undo()
        self._save_tool_defaults()

    def duplicate_selected(self) -> None:
        selected = [
            item
            for item in self._scene.selectedItems()
            if item is not self._background_item
        ]
        if not selected:
            return
        offset = QPointF(20, 20)
        duplicated = False
        for item in selected:
            clone = self._clone_item(item, offset)
            if clone is not None:
                self._scene.addItem(clone)
                duplicated = True
        if not duplicated:
            return
        self._push_undo_state()
        self.image_changed.emit()

    def _clone_item(self, item, offset: QPointF):
        if isinstance(item, ArrowGraphicsItem):
            return ArrowGraphicsItem(
                item.start_point + item.pos() + offset,
                item.end_point + item.pos() + offset,
                QColor(item.color),
                item.thickness,
            )
        if isinstance(item, StepMarkerGraphicsItem):
            return StepMarkerGraphicsItem(
                item.pos() + offset,
                self._step_counter.next_number,
                QColor(item.marker_color),
                item.marker_size,
            )
        if isinstance(item, TextGraphicsItem):
            return TextGraphicsItem(
                item.toPlainText(),
                item.pos() + offset,
                QColor(item.text_color),
                item.font_size,
                item.bold,
            )
        if isinstance(item, RectangleGraphicsItem):
            clone = RectangleGraphicsItem(
                QRectF(item.rect).translated(offset),
                QColor(item.color),
                item.thickness,
                item.filled,
            )
            clone.setPos(item.pos())
            return clone
        if isinstance(item, HighlightGraphicsItem):
            clone = HighlightGraphicsItem(
                QRectF(item.rect).translated(offset),
                QColor(item.color),
                item.opacity,
            )
            clone.setPos(item.pos())
            return clone
        if isinstance(item, PenStrokeGraphicsItem):
            clone = PenStrokeGraphicsItem(
                QPainterPath(item.path),
                QColor(item.color),
                item.thickness,
            )
            clone.setPos(item.pos() + offset)
            return clone
        return None

    def reset_step_numbering(self) -> int:
        self._finalize_text_edit()
        markers = self._step_markers()
        for marker in markers:
            self._scene.removeItem(marker)
        self._step_counter.reset(start=1)
        self._push_undo_state()
        self.image_changed.emit()
        return len(markers)

    def has_screenshot(self) -> bool:
        return len(self._inventory) > 0 and self._background_item is not None

    def annotation_count(self) -> int:
        if self._background_item is None:
            return 0
        return sum(
            1
            for item in self._scene.items()
            if item is not self._background_item
        )

    def current_zoom(self) -> float:
        return self.transform().m11()

    def has_background(self) -> bool:
        return self._background_item is not None

    def reset_to_original(self) -> bool:
        record = self._inventory.get_current()
        if record is None or self._background_item is None:
            if self._original_pixmap is None or self._background_item is None:
                return False
            record = None
        self._flush_pending_property_undo()
        self._finalize_text_edit()
        self._cancel_resize_tracking()
        for item in list(self._scene.items()):
            if item is not self._background_item:
                self._scene.removeItem(item)
        self._scene.removeItem(self._background_item)
        if record is not None:
            restored = image_value_to_qpixmap(record.original)
            self._original_pixmap = restored.copy()
        else:
            restored = self._original_pixmap.copy()
        self._background_item = self._scene.addPixmap(restored)
        self._background_item.setZValue(-1)
        self._scene.setSceneRect(self._background_item.boundingRect())
        self.zoom_to_fit()
        self._step_counter.reset(start=1)
        self._reset_history()
        if record is not None:
            self._inventory.set_history(self._history)
            self._inventory.update_current(self._capture_document_state())
        self._scene.clearSelection()
        self.selection_changed.emit(None)
        self.image_changed.emit()
        return True

    def _text_item_at(self, scene_pos: QPointF) -> TextGraphicsItem | None:
        for item in self._scene.items(scene_pos):
            if isinstance(item, TextGraphicsItem):
                return item
        return None

    def _start_text_edit(self, item: TextGraphicsItem, *, is_new: bool = False) -> None:
        self._editing_text_item = item
        self._editing_text_is_new = is_new
        self._editing_text_before = None if is_new else item.toPlainText()
        item.on_focus_out = self._finalize_text_edit
        item.setSelected(True)
        item.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        item.setFocus(Qt.FocusReason.MouseFocusReason)

    def _finalize_text_edit(self) -> None:
        if self._editing_text_item is None:
            return
        item = self._editing_text_item
        is_new = self._editing_text_is_new
        before = self._editing_text_before
        self._editing_text_item = None
        self._editing_text_is_new = False
        self._editing_text_before = None
        item.on_focus_out = None

        item.finalize_editing()
        self.setFocus(Qt.FocusReason.OtherFocusReason)

        text = item.toPlainText().strip()

        if not text:
            if item.scene() is not None:
                self._scene.removeItem(item)
            if is_new:
                return
            self._push_undo_state()
            self.image_changed.emit()
            return

        if is_new or text != (before or "").strip():
            self._push_undo_state()
            self.image_changed.emit()

    def _step_markers(self) -> list[StepMarkerGraphicsItem]:
        return [
            item
            for item in self._scene.items()
            if isinstance(item, StepMarkerGraphicsItem)
        ]

    def undo(self) -> None:
        self._property_timer.stop()
        self._cancel_resize_tracking()
        if self._editing_text_item is not None:
            return
        state = self._history.undo()
        if state is not None:
            self._restore_document_state(state)
            if len(self._inventory) > 0:
                self._inventory.update_current(state)

    def redo(self) -> None:
        self._property_timer.stop()
        self._cancel_resize_tracking()
        if self._editing_text_item is not None:
            return
        state = self._history.redo()
        if state is not None:
            self._restore_document_state(state)
            if len(self._inventory) > 0:
                self._inventory.update_current(state)

    def delete_selected(self) -> None:
        selected = self._scene.selectedItems()
        if not selected:
            return
        self._cancel_resize_tracking()
        for item in selected:
            if item is self._background_item:
                continue
            self._scene.removeItem(item)
        self._push_undo_state()
        self.selection_changed.emit(None)
        self.image_changed.emit()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape and self._editing_text_item is not None:
            self._finalize_text_edit()
            return
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self._editing_text_item is None:
                self.delete_selected()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        if self._background_item is None:
            super().mousePressEvent(event)
            return

        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._tool_mode == ToolMode.SELECT
            and self._resize_layer.target() is not None
        ):
            handle = self._resize_layer.handle_at(event.position().toPoint())
            if handle is not None:
                self._begin_resize_tracking(handle)
                event.accept()
                return

        handler = self._handlers.get(self._tool_mode)
        if handler is None or event.button() != Qt.LeftButton:
            if self._editing_text_item is not None:
                self._finalize_text_edit()
            if self._tool_mode == ToolMode.SELECT and event.button() == Qt.LeftButton:
                self._begin_drag_tracking()
            super().mousePressEvent(event)
            self._emit_selection()
            return

        scene_pos = self.mapToScene(event.position().toPoint())
        self._flush_pending_property_undo()
        self._active_handler = handler
        if handler.on_press(scene_pos):
            self._active_handler = None

    def mouseDoubleClickEvent(self, event) -> None:
        if self._background_item is None or event.button() != Qt.LeftButton:
            super().mouseDoubleClickEvent(event)
            return
        scene_pos = self.mapToScene(event.position().toPoint())
        item = self._text_item_at(scene_pos)
        if item is None:
            super().mouseDoubleClickEvent(event)
            return
        if self._editing_text_item is item:
            return
        if self._editing_text_item is not None:
            self._finalize_text_edit()
        self._start_text_edit(item, is_new=False)

    def mouseMoveEvent(self, event) -> None:
        if self._resize_item is not None and self._resize_handle is not None:
            self._apply_resize_to(event.position().toPoint())
            event.accept()
            return
        scene_pos = self.mapToScene(event.position().toPoint())
        if self._active_handler is not None:
            self._active_handler.on_move(scene_pos)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._resize_item is not None and self._resize_handle is not None:
            if event.button() == Qt.MouseButton.LeftButton:
                self._commit_resize_tracking()
                event.accept()
            else:
                self._cancel_resize_tracking()
            return
        if self._active_handler is not None:
            handler = self._active_handler
            self._active_handler = None
            scene_pos = self.mapToScene(event.position().toPoint())
            handler.on_release(scene_pos)
            return
        super().mouseReleaseEvent(event)
        if self._drag_positions is not None:
            self._commit_drag_tracking()
        self._emit_selection()

    def _begin_drag_tracking(self) -> None:
        self._flush_pending_property_undo()
        self._drag_positions = {
            item: QPointF(item.pos())
            for item in self._scene.items()
            if item is not self._background_item
        }

    def _commit_drag_tracking(self) -> None:
        previous = self._drag_positions
        self._drag_positions = None
        if not previous:
            return
        moved = any(
            item in previous and item.pos() != previous[item]
            for item in self._scene.items()
            if item is not self._background_item
        )
        if moved:
            self._push_undo_state()
            self.image_changed.emit()
            self._resize_layer.resize_to_viewport(self)

    def _refresh_resize_layer(self) -> None:
        if self._tool_mode != ToolMode.SELECT:
            self._resize_layer.hide_handles()
            return
        selected = [item for item in self._scene.selectedItems() if item is not self._background_item]
        if len(selected) != 1:
            self._resize_layer.hide_handles()
            return
        self._resize_layer.update_for_item(selected[0], self)

    def _begin_resize_tracking(self, handle: Handle) -> None:
        item = self._resize_layer.target()
        if item is None:
            return
        self._resize_item = item
        self._resize_handle = handle
        self._resize_geometry_before = self._capture_geometry(item)
        self._resize_pos_before = QPointF(item.pos())
        self._flush_pending_property_undo()

    def _apply_resize_to(self, view_pos: QPoint) -> None:
        item = self._resize_item
        if item is None:
            return
        scene_pos = self.mapToScene(view_pos)
        before = self._resize_geometry_before
        if before is None or self._resize_handle is None:
            return
        if isinstance(item, ArrowGraphicsItem):
            new_start, new_end = self._project_arrow(
                before, self._resize_handle, scene_pos, item.pos()
            )
            item.set_geometry(new_start, new_end)
        else:
            new_rect = self._project_rect(
                before, self._resize_handle, scene_pos, item.pos()
            )
            item.set_geometry(new_rect)
        self._resize_layer.resize_to_viewport(self)
        self.viewport().update()

    def _commit_resize_tracking(self) -> None:
        item = self._resize_item
        before = self._resize_geometry_before
        pos_before = self._resize_pos_before
        self._cancel_resize_tracking()
        if item is None or before is None or pos_before is None:
            return
        after = self._capture_geometry(item)
        if after != before or item.pos() != pos_before:
            self._push_undo_state()
            self.image_changed.emit()

    def _cancel_resize_tracking(self) -> None:
        self._resize_item = None
        self._resize_handle = None
        self._resize_geometry_before = None
        self._resize_pos_before = None

    def _capture_geometry(
        self,
        item: ArrowGraphicsItem | RectangleGraphicsItem | HighlightGraphicsItem,
    ) -> tuple[QPointF, QPointF] | QRectF | None:
        if isinstance(item, ArrowGraphicsItem):
            return (QPointF(item.start_point), QPointF(item.end_point))
        if isinstance(item, (RectangleGraphicsItem, HighlightGraphicsItem)):
            return QRectF(item.rect)
        return None

    @staticmethod
    def _project_arrow(
        before: tuple[QPointF, QPointF],
        handle: Handle,
        scene_pos: QPointF,
        item_pos: QPointF,
    ) -> tuple[QPointF, QPointF]:
        start, end = before
        local_pos = QPointF(scene_pos.x() - item_pos.x(), scene_pos.y() - item_pos.y())
        if handle.role is HandleRole.ARROW_START:
            return local_pos, end
        return start, local_pos

    @staticmethod
    def _project_rect(
        before: QRectF,
        handle: Handle,
        scene_pos: QPointF,
        item_pos: QPointF,
    ) -> QRectF:
        rect = QRectF(before)
        x, y = scene_pos.x() - item_pos.x(), scene_pos.y() - item_pos.y()
        if handle.role is HandleRole.RECT_TL:
            return QRectF(x, y, rect.right() - x, rect.bottom() - y)
        if handle.role is HandleRole.RECT_TR:
            return QRectF(rect.left(), y, x - rect.left(), rect.bottom() - y)
        if handle.role is HandleRole.RECT_BL:
            return QRectF(x, rect.top(), rect.right() - x, y - rect.top())
        if handle.role is HandleRole.RECT_BR:
            return QRectF(rect.left(), rect.top(), x - rect.left(), y - rect.top())
        if handle.role is HandleRole.RECT_T:
            return QRectF(rect.left(), y, rect.width(), rect.bottom() - y)
        if handle.role is HandleRole.RECT_B:
            return QRectF(rect.left(), rect.top(), rect.width(), y - rect.top())
        if handle.role is HandleRole.RECT_L:
            return QRectF(x, rect.top(), rect.right() - x, rect.height())
        if handle.role is HandleRole.RECT_R:
            return QRectF(rect.left(), rect.top(), x - rect.left(), rect.height())
        return rect

    def _cancel_previews(self) -> None:
        for handler in self._handlers.values():
            handler.cancel()
        self._active_handler = None

    def _apply_crop(self, rect: QRectF) -> bool:
        if self._background_item is None:
            return False
        self._cancel_resize_tracking()
        from PySide6.QtCore import QRect

        background = self._background_item.pixmap()
        bounds = self._background_item.boundingRect()
        effective = rect.intersected(bounds)
        if effective.width() < 1 or effective.height() < 1:
            return False
        physical = self._logical_to_physical_rect(effective)
        physical = physical.intersected(
            QRect(0, 0, background.width(), background.height())
        )
        if physical.width() < 1 or physical.height() < 1:
            return False
        cropped = background.copy(physical)
        if cropped.isNull():
            return False
        origin_x = effective.left()
        origin_y = effective.top()
        for item in list(self._scene.items()):
            if item is self._background_item:
                continue
            if item.sceneBoundingRect().intersected(effective).isEmpty():
                self._scene.removeItem(item)
                continue
            item.moveBy(-origin_x, -origin_y)
            if isinstance(item, BlurPatchGraphicsItem) and item.source_rect is not None:
                item.source_rect.translate(-origin_x, -origin_y)
        self._background_item.setPixmap(cropped)
        self._bg_image_cache_key = None
        self._scene.setSceneRect(self._background_item.boundingRect())
        self.zoom_to_fit()
        return True

    def _apply_blur_region(self, rect: QRectF) -> None:
        if self._background_item is None:
            return
        physical_rect = self._logical_to_physical_rect(rect)
        background = self._background_item.pixmap()
        try:
            patch = apply_region_effect(
                background,
                physical_rect,
                self._blur_mode,
                pixelate_size=self._blur_strength,
                blur_radius=self._blur_strength,
                device_pixel_ratio=background.devicePixelRatio(),
            )
        except ValueError:
            return
        item = BlurPatchGraphicsItem(
            patch,
            rect.topLeft(),
            self._blur_mode.value,
            self._blur_strength,
            source_rect=rect,
        )
        self._scene.addItem(item)

    def _logical_to_physical_rect(self, rect: QRectF) -> QRect:
        from PySide6.QtCore import QRect

        background = self._background_item.pixmap()
        logical = self._background_item.boundingRect()
        scale_x = background.width() / logical.width()
        scale_y = background.height() / logical.height()
        return QRect(
            int(rect.x() * scale_x),
            int(rect.y() * scale_y),
            max(1, int(rect.width() * scale_x)),
            max(1, int(rect.height() * scale_y)),
        )

    def _selected_arrow(self) -> ArrowGraphicsItem | None:
        for item in self._scene.selectedItems():
            if isinstance(item, ArrowGraphicsItem):
                return item
        return None

    def _selected_step(self) -> StepMarkerGraphicsItem | None:
        for item in self._scene.selectedItems():
            if isinstance(item, StepMarkerGraphicsItem):
                return item
        return None

    def _selected_text(self) -> TextGraphicsItem | None:
        for item in self._scene.selectedItems():
            if isinstance(item, TextGraphicsItem):
                return item
        return None

    def _selected_rectangle(self) -> RectangleGraphicsItem | None:
        for item in self._scene.selectedItems():
            if isinstance(item, RectangleGraphicsItem):
                return item
        return None

    def _selected_highlight(self) -> HighlightGraphicsItem | None:
        for item in self._scene.selectedItems():
            if isinstance(item, HighlightGraphicsItem):
                return item
        return None

    def _selected_pen(self) -> PenStrokeGraphicsItem | None:
        for item in self._scene.selectedItems():
            if isinstance(item, PenStrokeGraphicsItem):
                return item
        return None

    def _emit_selection(self) -> None:
        for item in self._scene.selectedItems():
            if isinstance(item, ArrowGraphicsItem):
                self.selection_changed.emit(item)
                return
            if isinstance(item, RectangleGraphicsItem):
                self.selection_changed.emit(item)
                return
            if isinstance(item, HighlightGraphicsItem):
                self.selection_changed.emit(item)
                return
            if isinstance(item, StepMarkerGraphicsItem):
                self.selection_changed.emit(item)
                return
            if isinstance(item, TextGraphicsItem):
                self.selection_changed.emit(item)
                return
            if isinstance(item, PenStrokeGraphicsItem):
                self.selection_changed.emit(item)
                return
        self.selection_changed.emit(None)

    def add_item(self, item: QGraphicsItem) -> None:
        self._scene.addItem(item)

    def remove_item(self, item: QGraphicsItem) -> None:
        self._scene.removeItem(item)

    def push_undo_state(self) -> None:
        self._push_undo_state()

    def emit_image_changed(self) -> None:
        self.image_changed.emit()

    def apply_blur_region(self, rect: QRectF) -> None:
        self._apply_blur_region(rect)

    def apply_crop(self, rect: QRectF) -> bool:
        return self._apply_crop(rect)

    def get_arrow_settings(self) -> tuple[QColor, int]:
        return self._arrow_color, self._arrow_thickness

    def get_rectangle_settings(self) -> tuple[QColor, int, bool]:
        return self._rectangle_color, self._rectangle_thickness, self._rectangle_filled

    def get_highlight_settings(self) -> tuple[QColor, int]:
        return self._highlight_color, self._highlight_opacity

    def get_step_settings(self) -> tuple[QColor, int, StepCounter]:
        return self._step_color, self._step_size, self._step_counter

    def get_text_settings(self) -> tuple[QColor, int, bool]:
        return self._text_color, self._text_font_size, self._text_bold

    def get_pen_settings(self) -> tuple[QColor, int]:
        return self._pen_color, self._pen_thickness

    def get_text_item_at(self, scene_pos: QPointF) -> TextGraphicsItem | None:
        return self._text_item_at(scene_pos)

    def start_text_edit(self, item: TextGraphicsItem, *, is_new: bool) -> None:
        self._start_text_edit(item, is_new=is_new)

    def finalize_text_edit(self) -> None:
        self._finalize_text_edit()

    def is_editing_text(self) -> bool:
        return self._editing_text_item is not None

    @property
    def history(self) -> DocumentHistory:
        return self._history

    def _capture_document_state(self) -> DocumentState:
        return DocumentState(
            version=DocumentHistory.DOCUMENT_VERSION,
            image=self._current_image_value(),
            annotations=self._capture_annotations(),
            step_counter=self._step_counter.current,
        )

    def _current_image_value(self) -> ImageValue | None:
        if self._background_item is None:
            return None
        pixmap = self._background_item.pixmap()
        if self._bg_image_cache_key != pixmap.cacheKey():
            self._bg_image_value = qpixmap_to_image_value(pixmap)
            self._bg_image_cache_key = pixmap.cacheKey()
        return self._bg_image_value

    def _capture_annotations(self) -> tuple[AnnotationRecord, ...]:
        records = []
        for item in self._scene.items():
            if item is self._background_item:
                continue
            if not isinstance(item, _CAPTURABLE_TYPES):
                continue
            records.append(capture_annotation(item))
        return tuple(records)

    def _schedule_property_undo(self) -> None:
        self._property_timer.start()

    def _flush_pending_property_undo(self) -> None:
        if self._property_timer.isActive():
            self._push_undo_state()

    def _push_undo_state(self) -> None:
        self._property_timer.stop()
        state = self._capture_document_state()
        result = self._history.apply(state)
        if isinstance(result, RejectedMutation):
            logger.warning("History rejected document state: %s", result.reason)
        if len(self._inventory) > 0 and self._background_item is not None:
            self._inventory.update_current(self._history.current)

    def _restore_document_state(self, state: DocumentState) -> None:
        for record in state.annotations:
            if self._registry.adapter(record.kind) is None:
                logger.warning(
                    "Restoration rejected: unregistered annotation kind %s",
                    record.kind,
                )
                return

        restored_items = []
        for record in reversed(state.annotations):
            restored_items.append(restore_annotation(self._registry, record))

        for item in list(self._scene.items()):
            if item is self._background_item:
                continue
            self._scene.removeItem(item)

        if self._background_item is not None and state.image is not None:
            self._background_item.setPixmap(image_value_to_qpixmap(state.image))
            self._bg_image_value = state.image
            self._bg_image_cache_key = self._background_item.pixmap().cacheKey()

        self._step_counter.reset_to(state.step_counter)

        for item in restored_items:
            self._scene.addItem(item)

        if self._background_item is not None:
            self._scene.setSceneRect(self._background_item.boundingRect())

        self.selection_changed.emit(None)
        self.image_changed.emit()
