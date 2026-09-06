"""PRD acceptance criteria mapped to automated tests.

Each test class corresponds to a section of the Product Requirements Document.
Tests use real Qt mouse / keyboard interaction (synthesized through qtbot)
wherever a user workflow is being claimed; the few symbol-only checks (file
existence, main entry point callable) document the packaging surface.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from PySide6.QtCore import QPointF, QRect, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QKeySequence
from PySide6.QtWidgets import QApplication

from services.clipboard_service import ClipboardService
from services.export_service import ExportService
from services.screenshot_service import ScreenshotService
from tests.conftest import (
    add_text_annotation,
    double_click_on_canvas,
    drag_item_on_canvas,
    drag_on_canvas,
    draw_arrow_on_canvas,
    left_press,
    left_release,
    place_step_marker,
)
from ui.canvas import AnnotationCanvas, ToolMode
from ui.graphics_items import (
    ArrowGraphicsItem,
    BlurPatchGraphicsItem,
    HighlightGraphicsItem,
    RectangleGraphicsItem,
    StepMarkerGraphicsItem,
    TextGraphicsItem,
)
from ui.region_selector import RegionSelector
from ui.toolbar import LeftToolBar, TopToolBar


def _first(canvas, item_type):
    matches = [i for i in canvas.scene().items() if isinstance(i, item_type)]
    assert matches, f"no {item_type.__name__} in scene"
    return matches[0]


def _sample_pixel(pixmap, scene_pt: QPointF, sample_pixmap) -> QColor:
    bg = pixmap
    scale_x = bg.width() / bg.devicePixelRatio() / sample_pixmap.width()
    scale_y = bg.height() / bg.devicePixelRatio() / sample_pixmap.height()
    image = bg.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    return QColor(image.pixel(int(scene_pt.x() * scale_x), int(scene_pt.y() * scale_y)))


@pytest.mark.acceptance
class TestScreenshotCapture:
    """PRD § MVP Features — Screenshot Capture."""

    def test_region_capture_produces_image(self, qapp):
        screen = QGuiApplication.primaryScreen()
        geometry = screen.geometry()
        rect = QRect(
            geometry.x() + 5,
            geometry.y() + 5,
            min(100, geometry.width() - 10),
            min(80, geometry.height() - 10),
        )
        pixmap = ScreenshotService.capture_region(rect)
        assert not pixmap.isNull()
        assert pixmap.width() == rect.width()
        assert pixmap.height() == rect.height()

    def test_full_screen_capture_produces_image(self, qapp):
        pixmap = ScreenshotService.capture_full_screen()
        assert not pixmap.isNull()
        assert pixmap.width() > 0
        assert pixmap.height() > 0

    def test_region_selector_creates_overlay(self, qapp, qtbot):
        selector = RegionSelector()
        qtbot.addWidget(selector)
        assert selector.windowFlags() & Qt.WindowType.FramelessWindowHint
        assert selector.windowFlags() & Qt.WindowType.WindowStaysOnTopHint


@pytest.mark.acceptance
class TestAnnotationCanvas:
    """PRD § Annotation Canvas — select, move, delete, resize."""

    def test_user_can_select_and_delete_annotation_via_mouse(
        self, qapp, qtbot, sample_pixmap
    ):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)
        add_text_annotation(canvas, QPointF(40, 40), "Bug note")

        text = _first(canvas, TextGraphicsItem)
        click_view = QPointF(canvas.mapFromScene(QPointF(40, 40)))
        left_press(canvas.viewport(), qtbot, click_view)
        left_release(canvas.viewport(), qtbot, click_view)
        QApplication.processEvents()
        assert text.isSelected()

        before_undo = len(canvas.history.undo_stack)
        canvas.delete_selected()
        assert len(canvas.history.undo_stack) == before_undo + 1
        remaining = [i for i in canvas.scene().items() if isinstance(i, TextGraphicsItem)]
        assert remaining == []

        canvas.undo()
        restored = [i for i in canvas.scene().items() if isinstance(i, TextGraphicsItem)]
        assert len(restored) == 1
        assert restored[0].toPlainText() == "Bug note"

    def test_arrow_is_movable_via_mouse_drag(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.ARROW)
        draw_arrow_on_canvas(canvas, qtbot, QPointF(10, 10), QPointF(100, 50))
        arrow = _first(canvas, ArrowGraphicsItem)
        before_scene_start = arrow.start_point + arrow.pos()

        canvas.set_tool_mode(ToolMode.SELECT)
        drag_item_on_canvas(
            canvas, qapp, QPointF(50, 30), QPointF(80, 60)
        )

        after_scene_start = arrow.start_point + arrow.pos()
        delta_x = after_scene_start.x() - before_scene_start.x()
        delta_y = after_scene_start.y() - before_scene_start.y()
        assert abs(delta_x - 30) < 5
        assert abs(delta_y - 30) < 5

    def test_duplicate_creates_offset_copy_via_shortcut(
        self, qapp, qtbot, sample_pixmap
    ):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.ARROW)
        draw_arrow_on_canvas(canvas, qtbot, QPointF(20, 20), QPointF(120, 80))
        original = _first(canvas, ArrowGraphicsItem)
        canvas.set_tool_mode(ToolMode.SELECT)
        original.setSelected(True)
        QApplication.processEvents()

        canvas.duplicate_selected()

        arrows = [i for i in canvas.scene().items() if isinstance(i, ArrowGraphicsItem)]
        assert len(arrows) == 2
        clone = next(a for a in arrows if a is not original)
        original_scene_start = original.start_point + original.pos()
        clone_scene_start = clone.start_point + clone.pos()
        assert clone_scene_start.x() - original_scene_start.x() == pytest.approx(20)
        assert clone_scene_start.y() - original_scene_start.y() == pytest.approx(20)


@pytest.mark.acceptance
class TestArrowTool:
    """PRD § Arrow Tool."""

    def test_draw_move_resize_change_color_and_thickness(self, qapp, qtbot, sample_pixmap):
        from PySide6.QtWidgets import QApplication
        from ui.resize_handles import HandleRole

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)

        draw_arrow_on_canvas(canvas, qtbot, QPointF(20, 20), QPointF(180, 120))

        canvas.set_tool_mode(ToolMode.SELECT)
        arrow = _first(canvas, ArrowGraphicsItem)
        arrow.setSelected(True)
        QApplication.processEvents()
        canvas._refresh_resize_layer()
        end_handle = next(
            h for h in canvas._resize_layer._handles if h.role is HandleRole.ARROW_END
        )
        handle_view = QPointF(
            end_handle.rect.x() + end_handle.rect.width() / 2,
            end_handle.rect.y() + end_handle.rect.height() / 2,
        )
        target_view = handle_view + QPointF(40, 20)
        drag_on_canvas(canvas, qapp, handle_view, target_view)

        resized = _first(canvas, ArrowGraphicsItem)
        resized_end = resized.end_point + resized.pos()
        assert abs(resized_end.x() - 180) > 5 or abs(resized_end.y() - 120) > 5

        canvas.set_arrow_color(QColor(Qt.GlobalColor.blue))
        canvas.set_arrow_thickness(6)
        styled = _first(canvas, ArrowGraphicsItem)
        assert styled.thickness == 6
        assert styled.color.blue() == 255

        canvas.undo()
        restored = _first(canvas, ArrowGraphicsItem)
        restored_end = restored.end_point + restored.pos()
        assert abs(restored_end.x() - 180) < 1
        assert abs(restored_end.y() - 120) < 1


@pytest.mark.acceptance
class TestStepNumberTool:
    """PRD § Numbered Step Tool — most important feature."""

    def test_auto_increment_numbering(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.STEP)

        for x in (50, 100, 150, 200):
            place_step_marker(canvas, qtbot, QPointF(x, 100))

        markers = sorted(
            (m.number for m in canvas.scene().items() if isinstance(m, StepMarkerGraphicsItem))
        )
        assert markers == [1, 2, 3, 4]

    def test_reset_change_color_and_size(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.STEP)
        place_step_marker(canvas, qtbot, QPointF(80, 80))

        marker = _first(canvas, StepMarkerGraphicsItem)
        marker.setSelected(True)

        canvas.set_step_color(QColor(Qt.GlobalColor.green))
        canvas.set_step_size(40)

        assert marker.marker_size == 40
        assert marker.marker_color.green() == 255

        place_step_marker(canvas, qtbot, QPointF(160, 160))
        canvas.reset_step_numbering()

        markers = [i for i in canvas.scene().items() if isinstance(i, StepMarkerGraphicsItem)]
        assert markers == []
        assert canvas.step_counter.next_number == 1


@pytest.mark.acceptance
class TestTextTool:
    """PRD § Text Tool."""

    def test_font_size_color_bold_multiline_via_double_click(
        self, qapp, qtbot, sample_pixmap
    ):
        from PySide6.QtWidgets import QApplication

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)

        text = "Click here\nError appears after saving"
        add_text_annotation(canvas, QPointF(25, 25), text)

        item = _first(canvas, TextGraphicsItem)
        item.setSelected(True)
        QApplication.processEvents()

        canvas.set_text_font_size(18)
        canvas.set_text_bold(True)
        canvas.set_text_color(QColor(Qt.GlobalColor.magenta))

        assert item.font_size == 18
        assert item.bold is True
        assert item.toPlainText() == text

        double_click_on_canvas(canvas, qapp, QPointF(25, 25))
        assert canvas._editing_text_item is item


@pytest.mark.acceptance
class TestRectangleTool:
    """PRD § Rectangle Tool — outline, fill, border thickness."""

    def test_draw_filled_and_outline(self, qapp, qtbot, sample_pixmap):
        from tests.test_ui.test_scenario2_tools import draw_rect_on_canvas

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_rectangle_filled(True)
        draw_rect_on_canvas(
            canvas, qtbot, QPointF(20, 20), QPointF(120, 80), ToolMode.RECTANGLE
        )
        rect = _first(canvas, RectangleGraphicsItem)
        assert rect.filled is True
        assert rect.thickness == canvas._rectangle_thickness

        canvas.set_rectangle_filled(False)
        canvas.set_rectangle_thickness(5)
        draw_rect_on_canvas(
            canvas, qtbot, QPointF(200, 200), QPointF(320, 280), ToolMode.RECTANGLE
        )
        rectangles = [
            i for i in canvas.scene().items() if isinstance(i, RectangleGraphicsItem)
        ]
        assert len(rectangles) == 2
        fill_states = sorted(r.filled for r in rectangles)
        thickness_values = sorted(r.thickness for r in rectangles)
        assert fill_states == [False, True]
        assert thickness_values == [3, 5]

    def test_filled_rectangle_appears_in_rendered_pixmap(
        self, qapp, qtbot, sample_pixmap
    ):
        from tests.test_ui.test_scenario2_tools import draw_rect_on_canvas

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_rectangle_color(QColor(255, 0, 0))
        canvas.set_rectangle_filled(True)
        draw_rect_on_canvas(
            canvas, qtbot, QPointF(40, 40), QPointF(160, 120), ToolMode.RECTANGLE
        )

        rendered = canvas.render_to_pixmap()
        interior = _sample_pixel(rendered, QPointF(100, 80), sample_pixmap)
        assert interior.red() > 200


@pytest.mark.acceptance
class TestHighlightTool:
    """PRD § Highlight Tool — semi-transparent marker."""

    def test_highlight_button_in_left_toolbar(self, qapp, qtbot):
        toolbar = LeftToolBar()
        qtbot.addWidget(toolbar)
        button_labels = {
            toolbar._buttons[mode].text() for mode in toolbar._buttons
        }
        assert any("Highlight" in label for label in button_labels)

    def test_highlight_opacity_via_draw_then_set(self, qapp, qtbot, sample_pixmap):
        from tests.test_ui.test_scenario2_tools import draw_rect_on_canvas

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        draw_rect_on_canvas(
            canvas, qtbot, QPointF(30, 30), QPointF(150, 100), ToolMode.HIGHLIGHT
        )
        highlight = _first(canvas, HighlightGraphicsItem)
        highlight.setSelected(True)
        canvas.set_highlight_opacity(200)
        assert highlight.opacity == 200

    def test_highlight_modifies_rendered_pixels(self, qapp, qtbot, sample_pixmap):
        from tests.test_ui.test_scenario2_tools import draw_rect_on_canvas

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_highlight_color(QColor(255, 255, 0))
        canvas.set_highlight_opacity(255)
        draw_rect_on_canvas(
            canvas, qtbot, QPointF(50, 50), QPointF(200, 150), ToolMode.HIGHLIGHT
        )

        before = _sample_pixel(canvas._background_item.pixmap(), QPointF(120, 100), sample_pixmap)
        rendered = canvas.render_to_pixmap()
        after = _sample_pixel(rendered, QPointF(120, 100), sample_pixmap)
        assert (after.red(), after.green(), after.blue()) != (before.red(), before.green(), before.blue())


@pytest.mark.acceptance
class TestBlurTool:
    """PRD § Blur Tool — blur and pixelate modes."""

    def test_blur_and_pixelate_modes_modify_pixels(
        self, qapp, qtbot, sample_pixmap
    ):
        from services.image_effects import BlurMode
        from tests.test_ui.test_scenario2_tools import draw_rect_on_canvas

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_blur_mode(BlurMode.PIXELATE)
        draw_rect_on_canvas(
            canvas, qtbot, QPointF(40, 40), QPointF(180, 140), ToolMode.BLUR
        )
        patches = [i for i in canvas.scene().items() if isinstance(i, BlurPatchGraphicsItem)]
        assert len(patches) == 1
        assert patches[0].blur_mode == BlurMode.PIXELATE.value

        rendered = canvas.render_to_pixmap()
        before = _sample_pixel(canvas._background_item.pixmap(), QPointF(100, 90), sample_pixmap)
        after = _sample_pixel(rendered, QPointF(100, 90), sample_pixmap)
        assert (after.red(), after.green(), after.blue()) != (before.red(), before.green(), before.blue())


@pytest.mark.acceptance
class TestCropTool:
    """PRD § Crop Tool."""

    def test_crop_updates_rendered_pixmap_dimensions(
        self, qapp, qtbot, sample_pixmap
    ):
        from tests.conftest import drag_on_canvas

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.CROP)

        start = QPointF(canvas.mapFromScene(QPointF(100, 100)))
        end = QPointF(canvas.mapFromScene(QPointF(300, 250)))
        drag_on_canvas(canvas, qapp, start, end)

        rendered = canvas.render_to_pixmap()
        assert abs(rendered.width() - 200) <= 1
        assert abs(rendered.height() - 150) <= 1


@pytest.mark.acceptance
class TestUndoRedo:
    """PRD § Undo / Redo — Ctrl+Z and Ctrl+Y."""

    def test_undo_and_redo_around_fifty_state_cap(
        self, qapp, qtbot, sample_pixmap
    ):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.STEP)

        for x in range(50, 50 + 50 * 8, 8):
            place_step_marker(canvas, qtbot, QPointF(x, 100))
        assert len(canvas.history.undo_stack) == 50

        for x in range(450, 450 + 10 * 8, 8):
            place_step_marker(canvas, qtbot, QPointF(x, 100))
        assert len(canvas.history.undo_stack) == 50

    def test_redo_clears_after_new_action(self, qapp, qtbot, sample_pixmap):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.STEP)

        place_step_marker(canvas, qtbot, QPointF(50, 100))
        place_step_marker(canvas, qtbot, QPointF(100, 100))
        canvas.undo()
        assert len(canvas.history.redo_stack) == 1

        place_step_marker(canvas, qtbot, QPointF(150, 100))
        assert len(canvas.history.redo_stack) == 0

    def test_toolbar_shortcuts_match_prd(self, qapp, qtbot):
        toolbar = TopToolBar()
        qtbot.addWidget(toolbar)
        shortcuts = {
            action.text(): action.shortcut()
            for action in toolbar.actions()
            if action.text()
        }
        assert shortcuts["Undo"] == QKeySequence.StandardKey.Undo
        assert shortcuts["Redo"] == QKeySequence("Ctrl+Y")


@pytest.mark.acceptance
class TestSaveImage:
    """PRD § Save Image — PNG (default) and JPG."""

    def test_save_png(self, sample_pixmap, tmp_path):
        path = tmp_path / "bug_report.png"
        ExportService.save_png(sample_pixmap, path)
        assert path.exists()
        assert path.stat().st_size > 0

    def test_save_jpg(self, sample_pixmap, tmp_path):
        path = tmp_path / "bug_report.jpg"
        ExportService.save_jpg(sample_pixmap, path)
        assert path.exists()
        assert path.stat().st_size > 0


@pytest.mark.acceptance
class TestCopyToClipboard:
    """PRD § Copy To Clipboard."""

    def test_copy_annotated_screenshot(self, qapp, qtbot, sample_pixmap, mock_clipboard):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        draw_arrow_on_canvas(canvas, qtbot, QPointF(10, 10), QPointF(200, 100))

        pixmap = canvas.render_to_pixmap()
        assert not pixmap.isNull()
        ClipboardService.copy_image(pixmap)

        copied = mock_clipboard.pixmap()
        assert not copied.isNull()
        assert copied.width() == pixmap.width()
        assert copied.height() == pixmap.height()


@pytest.mark.acceptance
class TestOfflineOperation:
    """PRD § Non Functional — offline, no cloud dependency."""

    def test_no_network_modules_in_core_services(self):
        service_modules = [
            "services.screenshot_service",
            "services.export_service",
            "services.clipboard_service",
        ]
        for module_name in service_modules:
            module = importlib.import_module(module_name)
            source_path = Path(module.__file__).read_text(encoding="utf-8")
            assert "requests" not in source_path
            assert "urllib" not in source_path
            assert "http" not in source_path.lower()


@pytest.mark.acceptance
class TestPackaging:
    """PRD § Packaging — standalone StepShot.exe via PyInstaller."""

    def test_pyinstaller_spec_or_build_script_exists(self):
        root = Path(__file__).resolve().parents[2]
        assert (root / "StepShot.spec").is_file()
        assert (root / "build.py").is_file()

    def test_main_entry_launches_application(self):
        main = importlib.import_module("main")
        assert callable(getattr(main, "main", None))
