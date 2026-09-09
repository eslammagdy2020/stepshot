"""Main application window."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QColorDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from services.clipboard_service import ClipboardService
from services.export_service import ExportService
from services.image_effects import BlurMode
from ui.canvas import MAX_ZOOM, MIN_ZOOM, AnnotationCanvas, ToolMode
from ui.graphics_items import (
    ArrowGraphicsItem,
    HighlightGraphicsItem,
    PenStrokeGraphicsItem,
    RectangleGraphicsItem,
    StepMarkerGraphicsItem,
    TextGraphicsItem,
)
from ui.theme import COLORS
from ui.toolbar import InventoryToolBar, LeftToolBar, TopToolBar


class MainWindow(QMainWindow):
    region_capture_requested = Signal()
    full_screen_capture_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("StepShot")
        self.resize(1280, 820)

        self._canvas = AnnotationCanvas()
        self._top_toolbar = TopToolBar()
        self._inventory_toolbar = InventoryToolBar()
        self._left_toolbar = LeftToolBar()
        self._properties_panel = self._build_properties_panel()

        canvas_frame = QFrame()
        canvas_frame.setObjectName("CanvasFrame")
        canvas_layout = QVBoxLayout(canvas_frame)
        canvas_layout.setContentsMargins(16, 12, 16, 12)
        canvas_inner = QFrame()
        canvas_inner.setObjectName("CanvasInner")
        inner_layout = QVBoxLayout(canvas_inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.addWidget(self._canvas)
        canvas_layout.addWidget(canvas_inner)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._left_toolbar)
        layout.addWidget(canvas_frame, stretch=1)
        layout.addWidget(self._properties_panel)
        self.setCentralWidget(central)

        self.addToolBar(self._top_toolbar)
        self.addToolBarBreak()
        self.addToolBar(self._inventory_toolbar)
        self._connect_signals()

        self._status = self.statusBar()
        self._status.showMessage(
            "Ready — PrtSc: region capture | Ctrl+PrtSc: full screen | Delete: remove selection"
        )
        self._annotation_label = QLabel("0 annotations")
        self._annotation_label.setObjectName("StatusLabel")
        self._status.addPermanentWidget(self._annotation_label)
        self._zoom_label = QLabel("")
        self._zoom_label.setObjectName("StatusLabel")
        self._status.addPermanentWidget(self._zoom_label)
        self._update_inventory_state()

    def load_screenshot(self, pixmap: QPixmap) -> None:
        self.add_screenshot(pixmap, "region")

    def add_screenshot(self, pixmap: QPixmap, source: str = "region") -> None:
        self._canvas.add_screenshot(pixmap, source)
        self.show()
        self.raise_()
        self.activateWindow()
        self._update_zoom_indicator()
        self._update_inventory_state()

    def _on_tool_selected(self, mode: ToolMode) -> None:
        self._canvas.set_tool_mode(mode)
        self._update_properties_panel(None)

    def _on_reset_steps(self) -> None:
        removed = self._canvas.reset_step_numbering()
        if removed:
            self._status.showMessage(
                f"Removed {removed} step marker{'s' if removed != 1 else ''}. Next step: 1.",
                4000,
            )
        else:
            self._status.showMessage("No step markers to remove.", 4000)

    def _on_reset_all(self) -> None:
        if not self._canvas.has_screenshot():
            self._status.showMessage("Capture a screenshot first.", 4000)
            return

        answer = QMessageBox.question(
            self,
            "Reset All",
            "Remove all annotations and restore the original screenshot?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        if self._canvas.reset_to_original():
            self._status.showMessage("Restored original screenshot.", 4000)
        else:
            self._status.showMessage("Nothing to reset.", 4000)

    def _connect_signals(self) -> None:
        self._left_toolbar.tool_selected.connect(self._on_tool_selected)
        self._left_toolbar.reset_steps.connect(self._on_reset_steps)
        self._left_toolbar.reset_all.connect(self._on_reset_all)

        self._top_toolbar.new_capture.connect(self.region_capture_requested.emit)
        self._top_toolbar.full_screen_capture.connect(
            self.full_screen_capture_requested.emit
        )
        self._top_toolbar.save_image.connect(self._save_image)
        self._top_toolbar.copy_image.connect(self._copy_image)
        self._top_toolbar.undo.connect(self._canvas.undo)
        self._top_toolbar.redo.connect(self._canvas.redo)
        self._top_toolbar.duplicate.connect(self._canvas.duplicate_selected)
        self._top_toolbar.zoom_in.connect(self._zoom_in)
        self._top_toolbar.zoom_out.connect(self._zoom_out)
        self._top_toolbar.zoom_fit.connect(self._zoom_fit)
        self._top_toolbar.zoom_reset.connect(self._zoom_reset)
        self._inventory_toolbar.prev_screenshot.connect(self._prev_screenshot)
        self._inventory_toolbar.next_screenshot.connect(self._next_screenshot)
        self._inventory_toolbar.delete_screenshot.connect(self._delete_screenshot)
        self._inventory_toolbar.clear_inventory.connect(self._clear_inventory)

        self._canvas.selection_changed.connect(self._update_properties_panel)
        self._canvas.image_changed.connect(self._update_annotation_count)
        self._canvas.image_changed.connect(self._update_zoom_indicator)
        self._canvas.inventory_changed.connect(self._update_inventory_state)

    def _build_properties_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("PropertiesPanel")
        panel.setFixedWidth(248)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        heading = QLabel("PROPERTIES")
        heading.setObjectName("PanelTitle")
        layout.addWidget(heading)

        self._stack = QStackedWidget()
        self._stack.setObjectName("PropertiesStack")
        layout.addWidget(self._stack, stretch=1)

        self._empty_page = QWidget()
        self._empty_page.setObjectName("PropertyPage")
        empty_page = self._empty_page
        empty_layout = QVBoxLayout(empty_page)
        empty_layout.setContentsMargins(0, 8, 0, 0)
        self._empty_panel = QLabel(
            "Choose a tool on the left, or select an annotation on the canvas."
        )
        self._empty_panel.setObjectName("HintLabel")
        self._empty_panel.setWordWrap(True)
        self._empty_panel.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        empty_layout.addWidget(self._empty_panel)
        empty_layout.addStretch()
        self._stack.addWidget(empty_page)

        self._arrow_panel = self._build_arrow_panel()
        self._stack.addWidget(self._arrow_panel)

        self._step_panel = self._build_step_panel()
        self._stack.addWidget(self._step_panel)

        self._text_panel = self._build_text_panel()
        self._stack.addWidget(self._text_panel)

        self._rectangle_panel = self._build_rectangle_panel()
        self._stack.addWidget(self._rectangle_panel)

        self._highlight_panel = self._build_highlight_panel()
        self._stack.addWidget(self._highlight_panel)

        self._blur_panel = self._build_blur_panel()
        self._stack.addWidget(self._blur_panel)

        self._pen_panel = self._build_pen_panel()
        self._stack.addWidget(self._pen_panel)

        self._stack.setCurrentWidget(self._empty_page)
        self._sync_panel_from_defaults()
        return panel

    def _property_page(self, title: str) -> tuple[QWidget, QFormLayout]:
        page = QWidget()
        page.setObjectName("PropertyPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        box = QGroupBox(title)
        box.setObjectName("PropertyGroup")
        form = QFormLayout(box)
        form.setContentsMargins(12, 22, 12, 14)
        form.setSpacing(12)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

        layout.addWidget(box)
        layout.addStretch()
        return page, form

    def _build_arrow_panel(self) -> QWidget:
        page, form = self._property_page("Arrow")

        self._arrow_color_btn = self._color_button(QColor(255, 0, 0))
        self._arrow_color_btn.clicked.connect(self._pick_arrow_color)
        form.addRow("Color", self._arrow_color_btn)

        self._arrow_thickness = QSpinBox()
        self._arrow_thickness.setRange(1, 12)
        self._arrow_thickness.setValue(3)
        self._arrow_thickness.valueChanged.connect(self._canvas.set_arrow_thickness)
        form.addRow("Thickness", self._arrow_thickness)
        return page

    def _build_step_panel(self) -> QWidget:
        page, form = self._property_page("Step Number")

        self._step_color_btn = self._color_button(QColor(255, 0, 0))
        self._step_color_btn.clicked.connect(self._pick_step_color)
        form.addRow("Color", self._step_color_btn)

        self._step_size = QSpinBox()
        self._step_size.setRange(18, 48)
        self._step_size.setValue(28)
        self._step_size.valueChanged.connect(self._canvas.set_step_size)
        form.addRow("Size", self._step_size)
        return page

    def _build_text_panel(self) -> QWidget:
        page, form = self._property_page("Text")

        self._text_color_btn = self._color_button(QColor(255, 0, 0))
        self._text_color_btn.clicked.connect(self._pick_text_color)
        form.addRow("Color", self._text_color_btn)

        self._text_font_size = QSpinBox()
        self._text_font_size.setRange(8, 48)
        self._text_font_size.setValue(14)
        self._text_font_size.valueChanged.connect(self._canvas.set_text_font_size)
        form.addRow("Font Size", self._text_font_size)

        self._text_bold = QCheckBox("Bold")
        self._text_bold.toggled.connect(self._canvas.set_text_bold)
        form.addRow("", self._text_bold)

        hint = QLabel("Click to place text. Click elsewhere or Esc to finish.")
        hint.setObjectName("HintLabel")
        hint.setWordWrap(True)
        form.addRow(hint)
        return page

    def _build_rectangle_panel(self) -> QWidget:
        page, form = self._property_page("Rectangle")

        self._rectangle_color_btn = self._color_button(QColor(255, 0, 0))
        self._rectangle_color_btn.clicked.connect(self._pick_rectangle_color)
        form.addRow("Color", self._rectangle_color_btn)

        self._rectangle_thickness = QSpinBox()
        self._rectangle_thickness.setRange(1, 12)
        self._rectangle_thickness.setValue(3)
        self._rectangle_thickness.valueChanged.connect(self._canvas.set_rectangle_thickness)
        form.addRow("Thickness", self._rectangle_thickness)

        self._rectangle_filled = QCheckBox("Filled")
        self._rectangle_filled.toggled.connect(self._canvas.set_rectangle_filled)
        form.addRow("", self._rectangle_filled)
        return page

    def _build_highlight_panel(self) -> QWidget:
        page, form = self._property_page("Highlight")

        self._highlight_color_btn = self._color_button(QColor(255, 255, 0))
        self._highlight_color_btn.clicked.connect(self._pick_highlight_color)
        form.addRow("Color", self._highlight_color_btn)

        self._highlight_opacity = QSlider(Qt.Orientation.Horizontal)
        self._highlight_opacity.setRange(20, 255)
        self._highlight_opacity.setValue(128)
        self._highlight_opacity.valueChanged.connect(self._canvas.set_highlight_opacity)
        form.addRow("Opacity", self._highlight_opacity)
        return page

    def _build_blur_panel(self) -> QWidget:
        page, form = self._property_page("Blur")

        self._blur_mode = QComboBox()
        self._blur_mode.addItem("Blur", BlurMode.BLUR)
        self._blur_mode.addItem("Pixelate", BlurMode.PIXELATE)
        self._blur_mode.currentIndexChanged.connect(self._on_blur_mode_changed)
        form.addRow("Mode", self._blur_mode)

        self._blur_strength = QSpinBox()
        self._blur_strength.setRange(4, 40)
        self._blur_strength.setValue(12)
        self._blur_strength.valueChanged.connect(self._canvas.set_blur_strength)
        form.addRow("Strength", self._blur_strength)

        hint = QLabel("Drag over passwords, names, or emails to hide them.")
        hint.setObjectName("HintLabel")
        hint.setWordWrap(True)
        form.addRow(hint)
        return page

    def _build_pen_panel(self) -> QWidget:
        page, form = self._property_page("Pen")

        self._pen_color_btn = self._color_button(QColor(255, 0, 0))
        self._pen_color_btn.clicked.connect(self._pick_pen_color)
        form.addRow("Color", self._pen_color_btn)

        self._pen_thickness = QSpinBox()
        self._pen_thickness.setRange(1, 20)
        self._pen_thickness.setValue(3)
        self._pen_thickness.valueChanged.connect(self._canvas.set_pen_thickness)
        form.addRow("Thickness", self._pen_thickness)
        return page

    def _color_button(self, color: QColor) -> QWidget:
        from PySide6.QtWidgets import QPushButton

        button = QPushButton()
        button.setObjectName("ColorSwatch")
        button.setFixedHeight(32)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._set_button_color(button, color)
        button.setProperty("color", color)
        return button

    def _set_button_color(self, button, color: QColor) -> None:
        border = COLORS["border"]
        button.setStyleSheet(
            f"QPushButton#ColorSwatch {{"
            f" background-color: {color.name()};"
            f" border: 2px solid {border};"
            f" border-radius: 8px;"
            f" min-height: 32px;"
            f"}}"
        )
        button.setProperty("color", color)

    def _pick_arrow_color(self) -> None:
        current = self._arrow_color_btn.property("color")
        color = QColorDialog.getColor(current, self, "Arrow Color")
        if color.isValid():
            self._set_button_color(self._arrow_color_btn, color)
            self._canvas.set_arrow_color(color)

    def _pick_step_color(self) -> None:
        current = self._step_color_btn.property("color")
        color = QColorDialog.getColor(current, self, "Step Color")
        if color.isValid():
            self._set_button_color(self._step_color_btn, color)
            self._canvas.set_step_color(color)

    def _pick_text_color(self) -> None:
        current = self._text_color_btn.property("color")
        color = QColorDialog.getColor(current, self, "Text Color")
        if color.isValid():
            self._set_button_color(self._text_color_btn, color)
            self._canvas.set_text_color(color)

    def _pick_rectangle_color(self) -> None:
        current = self._rectangle_color_btn.property("color")
        color = QColorDialog.getColor(current, self, "Rectangle Color")
        if color.isValid():
            self._set_button_color(self._rectangle_color_btn, color)
            self._canvas.set_rectangle_color(color)

    def _pick_highlight_color(self) -> None:
        current = self._highlight_color_btn.property("color")
        color = QColorDialog.getColor(current, self, "Highlight Color")
        if color.isValid():
            self._set_button_color(self._highlight_color_btn, color)
            self._canvas.set_highlight_color(color)

    def _pick_pen_color(self) -> None:
        current = self._pen_color_btn.property("color")
        color = QColorDialog.getColor(current, self, "Pen Color")
        if color.isValid():
            self._set_button_color(self._pen_color_btn, color)
            self._canvas.set_pen_color(color)

    def _on_blur_mode_changed(self) -> None:
        mode = self._blur_mode.currentData()
        if mode is not None:
            self._canvas.set_blur_mode(mode)

    def _update_properties_panel(self, item) -> None:
        if isinstance(item, ArrowGraphicsItem):
            self._stack.setCurrentWidget(self._arrow_panel)
            self._sync_panel_values(item)
            return
        if isinstance(item, RectangleGraphicsItem):
            self._stack.setCurrentWidget(self._rectangle_panel)
            self._sync_panel_values(item)
            return
        if isinstance(item, HighlightGraphicsItem):
            self._stack.setCurrentWidget(self._highlight_panel)
            self._sync_panel_values(item)
            return
        if isinstance(item, StepMarkerGraphicsItem):
            self._stack.setCurrentWidget(self._step_panel)
            self._sync_panel_values(item)
            return
        if isinstance(item, TextGraphicsItem):
            self._stack.setCurrentWidget(self._text_panel)
            self._sync_panel_values(item)
            return
        if isinstance(item, PenStrokeGraphicsItem):
            self._stack.setCurrentWidget(self._pen_panel)
            self._sync_panel_values(item)
            return

        mode = self._canvas.tool_mode
        if mode == ToolMode.ARROW:
            self._stack.setCurrentWidget(self._arrow_panel)
        elif mode == ToolMode.RECTANGLE:
            self._stack.setCurrentWidget(self._rectangle_panel)
        elif mode == ToolMode.HIGHLIGHT:
            self._stack.setCurrentWidget(self._highlight_panel)
        elif mode == ToolMode.BLUR:
            self._stack.setCurrentWidget(self._blur_panel)
        elif mode == ToolMode.STEP:
            self._stack.setCurrentWidget(self._step_panel)
        elif mode == ToolMode.TEXT:
            self._stack.setCurrentWidget(self._text_panel)
        elif mode == ToolMode.PEN:
            self._stack.setCurrentWidget(self._pen_panel)
        else:
            self._stack.setCurrentWidget(self._empty_page)

    def _set_widget_value(self, widget, value) -> None:
        widget.blockSignals(True)
        if isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        else:
            widget.setValue(int(value))
        widget.blockSignals(False)

    def _sync_panel_values(self, item) -> None:
        if isinstance(item, ArrowGraphicsItem):
            self._set_widget_value(self._arrow_thickness, item.thickness)
            self._set_button_color(self._arrow_color_btn, QColor(item.color))
        elif isinstance(item, RectangleGraphicsItem):
            self._set_widget_value(self._rectangle_thickness, item.thickness)
            self._set_widget_value(self._rectangle_filled, item.filled)
            self._set_button_color(self._rectangle_color_btn, QColor(item.color))
        elif isinstance(item, HighlightGraphicsItem):
            self._set_widget_value(self._highlight_opacity, item.opacity)
            self._set_button_color(self._highlight_color_btn, QColor(item.color))
        elif isinstance(item, StepMarkerGraphicsItem):
            self._set_widget_value(self._step_size, item.marker_size)
            self._set_button_color(self._step_color_btn, QColor(item.marker_color))
        elif isinstance(item, TextGraphicsItem):
            self._set_widget_value(self._text_font_size, item.font_size)
            self._set_widget_value(self._text_bold, item.bold)
            self._set_button_color(self._text_color_btn, QColor(item.text_color))
        elif isinstance(item, PenStrokeGraphicsItem):
            self._set_widget_value(self._pen_thickness, item.thickness)
            self._set_button_color(self._pen_color_btn, QColor(item.color))

    def _sync_panel_from_defaults(self) -> None:
        settings = self._canvas.get_tool_settings()
        self._set_widget_value(self._arrow_thickness, settings["arrow_thickness"])
        self._set_button_color(self._arrow_color_btn, settings["arrow_color"])
        self._set_widget_value(self._step_size, settings["step_size"])
        self._set_button_color(self._step_color_btn, settings["step_color"])
        self._set_widget_value(self._text_font_size, settings["text_font_size"])
        self._set_widget_value(self._text_bold, settings["text_bold"])
        self._set_button_color(self._text_color_btn, settings["text_color"])
        self._set_widget_value(
            self._rectangle_thickness, settings["rectangle_thickness"]
        )
        self._set_button_color(self._rectangle_color_btn, settings["rectangle_color"])
        self._set_widget_value(self._rectangle_filled, settings["rectangle_filled"])
        self._set_widget_value(
            self._highlight_opacity, settings["highlight_opacity"]
        )
        self._set_button_color(self._highlight_color_btn, settings["highlight_color"])
        index = self._blur_mode.findData(settings["blur_mode"])
        if index >= 0:
            self._blur_mode.blockSignals(True)
            self._blur_mode.setCurrentIndex(index)
            self._blur_mode.blockSignals(False)
        self._set_widget_value(self._blur_strength, settings["blur_strength"])
        self._set_widget_value(self._pen_thickness, settings["pen_thickness"])
        self._set_button_color(self._pen_color_btn, settings["pen_color"])

    def _save_image(self) -> None:
        try:
            pixmap = self._canvas.render_to_pixmap()
        except RuntimeError as exc:
            QMessageBox.warning(self, "Save", str(exc))
            return

        save_dir = ExportService.default_save_directory()
        default_name = ExportService.generate_filename(save_dir, "png")
        default_path = str(save_dir / default_name)

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Screenshot",
            default_path,
            "PNG Images (*.png);;JPEG Images (*.jpg *.jpeg)",
        )
        if not path:
            return

        try:
            if path.lower().endswith((".jpg", ".jpeg")):
                ExportService.save_jpg(pixmap, path)
            else:
                if not path.lower().endswith(".png"):
                    path += ".png"
                ExportService.save_png(pixmap, path)
        except RuntimeError as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))
            return

        self._status.showMessage(f"Saved {path}", 4000)

    def _copy_image(self) -> None:
        try:
            pixmap = self._canvas.render_to_pixmap()
        except RuntimeError as exc:
            QMessageBox.warning(self, "Copy", str(exc))
            return

        ClipboardService.copy_image(pixmap)
        self._status.showMessage("Copied to clipboard.", 3000)

    def _zoom_in(self) -> None:
        self._scale_zoom(1.15)

    def _zoom_out(self) -> None:
        self._scale_zoom(1 / 1.15)

    def _zoom_fit(self) -> None:
        self._canvas.zoom_to_fit()
        self._update_zoom_indicator()

    def _zoom_reset(self) -> None:
        self._canvas.resetTransform()
        self._update_zoom_indicator()

    def _scale_zoom(self, factor: float) -> None:
        if not self._canvas.has_background():
            return
        current = self._canvas.current_zoom()
        next_scale = current * factor
        if not (MIN_ZOOM <= next_scale <= MAX_ZOOM):
            return
        self._canvas.scale(factor, factor)
        self._update_zoom_indicator()

    def _update_zoom_indicator(self) -> None:
        percent = int(round(self._canvas.current_zoom() * 100))
        self._zoom_label.setText(f"Zoom: {percent}%")

    def _update_annotation_count(self) -> None:
        count = self._canvas.annotation_count()
        total = self._canvas.inventory_count
        current = self._canvas.current_index_1based
        if total == 0:
            self._annotation_label.setText(f"{count} annotations")
        else:
            self._annotation_label.setText(
                f"Screenshot {current} of {total} · {count} annotations"
            )

    def _update_inventory_state(self) -> None:
        total = self._canvas.inventory_count
        current = self._canvas.current_index_1based
        self._inventory_toolbar.update_inventory_state(
            current,
            total,
            self._canvas.can_go_prev(),
            self._canvas.can_go_next(),
            self._canvas.has_screenshot(),
        )
        self._update_annotation_count()

    def _prev_screenshot(self) -> None:
        if self._canvas.prev_screenshot():
            self._status.showMessage(
                f"Screenshot {self._canvas.current_index_1based}"
                f" of {self._canvas.inventory_count}.",
                3000,
            )

    def _next_screenshot(self) -> None:
        if self._canvas.next_screenshot():
            self._status.showMessage(
                f"Screenshot {self._canvas.current_index_1based}"
                f" of {self._canvas.inventory_count}.",
                3000,
            )

    def _delete_screenshot(self) -> None:
        if not self._canvas.has_screenshot():
            self._status.showMessage("Capture a screenshot first.", 4000)
            return
        if self._canvas.remove_current():
            total = self._canvas.inventory_count
            if total == 0:
                self._status.showMessage("Deleted screenshot. Inventory empty.", 4000)
            else:
                self._status.showMessage(
                    f"Deleted screenshot. Screenshot {self._canvas.current_index_1based}"
                    f" of {total}.",
                    4000,
                )

    def _clear_inventory(self) -> None:
        if not self._canvas.has_screenshot():
            self._status.showMessage("Inventory already empty.", 4000)
            return
        count = self._canvas.inventory_count
        self._canvas.clear_inventory()
        self._status.showMessage(f"Cleared {count} screenshots.", 4000)
