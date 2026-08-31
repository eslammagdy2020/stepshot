"""Tests for interactive annotation resize (Phase 13)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from tests.conftest import drag_on_canvas
from ui.canvas import ToolMode
from ui.graphics_items import (
    ArrowGraphicsItem,
    HighlightGraphicsItem,
    RectangleGraphicsItem,
)


def _select_item(canvas, item):
    item.setSelected(True)
    QApplication.processEvents()
    canvas._refresh_resize_layer()


def _handle_at(canvas, item, role):
    canvas._refresh_resize_layer()
    for handle in canvas._resize_layer._handles:
        if handle.role is role:
            return handle
    raise AssertionError(f"handle {role} not present for {type(item).__name__}")


class TestArrowResize:
    def _arrow_end_role(self):
        from ui.resize_handles import HandleRole

        return HandleRole.ARROW_END

    def test_drag_end_endpoint_changes_end_point(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)

        arrow = ArrowGraphicsItem(QPointF(50, 50), QPointF(150, 150), QColor(255, 0, 0), 3)
        canvas.scene().addItem(arrow)
        _select_item(canvas, arrow)

        end_handle = _handle_at(canvas, arrow, self._arrow_end_role())
        handle_view_center = QPointF(
            end_handle.rect.x() + end_handle.rect.width() / 2,
            end_handle.rect.y() + end_handle.rect.height() / 2,
        )
        target_view = handle_view_center + QPointF(40, 0)

        drag_on_canvas(canvas, qapp, handle_view_center, target_view)

        new_end_scene = arrow.end_point + arrow.pos()
        assert new_end_scene.x() > 150
        assert abs(new_end_scene.y() - 150) < 1

    def test_undo_restores_pre_resize_arrow(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)

        arrow = ArrowGraphicsItem(QPointF(50, 50), QPointF(150, 150), QColor(255, 0, 0), 3)
        canvas.scene().addItem(arrow)
        canvas._push_undo_state()
        _select_item(canvas, arrow)

        end_handle = _handle_at(canvas, arrow, self._arrow_end_role())
        start = QPointF(end_handle.rect.x() + 1, end_handle.rect.y() + 1)
        end = start + QPointF(60, 0)
        drag_on_canvas(canvas, qapp, start, end)

        post_resize = next(
            i for i in canvas.scene().items() if isinstance(i, ArrowGraphicsItem)
        )
        changed_end = post_resize.end_point + post_resize.pos()
        assert changed_end.x() != 150
        assert changed_end.y() != 150

        canvas.undo()
        restored = next(
            i for i in canvas.scene().items() if isinstance(i, ArrowGraphicsItem)
        )
        restored_end = restored.end_point + restored.pos()
        assert restored_end == QPointF(150, 150)

    def test_redo_applies_resize_again(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)

        arrow = ArrowGraphicsItem(QPointF(50, 50), QPointF(150, 150), QColor(255, 0, 0), 3)
        canvas.scene().addItem(arrow)
        canvas._push_undo_state()
        _select_item(canvas, arrow)

        end_handle = _handle_at(canvas, arrow, self._arrow_end_role())
        start = QPointF(end_handle.rect.x() + 1, end_handle.rect.y() + 1)
        end = start + QPointF(60, 0)
        drag_on_canvas(canvas, qapp, start, end)
        post_resize = next(
            i for i in canvas.scene().items() if isinstance(i, ArrowGraphicsItem)
        )
        post_resize_end = post_resize.end_point + post_resize.pos()
        canvas.undo()
        canvas.redo()
        redone = next(
            i for i in canvas.scene().items() if isinstance(i, ArrowGraphicsItem)
        )
        assert (redone.end_point + redone.pos()) == post_resize_end


class TestRectangleResize:
    def test_drag_br_corner_grows_rectangle(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas
        from ui.resize_handles import HandleRole

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)

        rect_item = RectangleGraphicsItem(QRectF(50, 50, 100, 80), QColor(255, 0, 0), 3)
        canvas.scene().addItem(rect_item)
        _select_item(canvas, rect_item)

        br = _handle_at(canvas, rect_item, HandleRole.RECT_BR)
        start = QPointF(br.rect.x() + 1, br.rect.y() + 1)
        end = start + QPointF(40, 30)
        drag_on_canvas(canvas, qapp, start, end)

        assert rect_item.rect.width() > 100
        assert rect_item.rect.height() > 80

    def test_minimum_size_clamped_to_four_pixels(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas
        from ui.resize_handles import HandleRole

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)

        rect_item = RectangleGraphicsItem(QRectF(100, 100, 80, 60), QColor(255, 0, 0), 3)
        canvas.scene().addItem(rect_item)
        _select_item(canvas, rect_item)

        br = _handle_at(canvas, rect_item, HandleRole.RECT_BR)
        start = QPointF(br.rect.x() + 1, br.rect.y() + 1)
        end = start + QPointF(-200, -200)
        drag_on_canvas(canvas, qapp, start, end)

        assert rect_item.rect.width() >= 4
        assert rect_item.rect.height() >= 4

    def test_undo_redo_round_trip(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas
        from ui.resize_handles import HandleRole

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)

        rect_item = RectangleGraphicsItem(QRectF(20, 20, 100, 80), QColor(255, 0, 0), 3)
        canvas.scene().addItem(rect_item)
        canvas._push_undo_state()
        _select_item(canvas, rect_item)

        br = _handle_at(canvas, rect_item, HandleRole.RECT_BR)
        start = QPointF(br.rect.x() + 1, br.rect.y() + 1)
        end = start + QPointF(50, 25)
        drag_on_canvas(canvas, qapp, start, end)
        post_resize = next(
            i for i in canvas.scene().items() if isinstance(i, RectangleGraphicsItem)
        )
        post = QRectF(post_resize.rect)

        canvas.undo()
        restored = next(
            i for i in canvas.scene().items() if isinstance(i, RectangleGraphicsItem)
        )
        assert QRectF(restored.rect) == QRectF(20, 20, 100, 80)
        canvas.redo()
        redone = next(
            i for i in canvas.scene().items() if isinstance(i, RectangleGraphicsItem)
        )
        assert QRectF(redone.rect) == post


class TestResizeAtNonZeroPos:
    def test_rectangle_resize_with_offset(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas
        from ui.resize_handles import HandleRole

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)

        rect_item = RectangleGraphicsItem(QRectF(0, 0, 50, 30), QColor(255, 0, 0), 3)
        rect_item.setPos(100, 100)
        canvas.scene().addItem(rect_item)
        canvas._push_undo_state()
        _select_item(canvas, rect_item)

        br = _handle_at(canvas, rect_item, HandleRole.RECT_BR)
        start = QPointF(br.rect.x() + 1, br.rect.y() + 1)
        end = start + QPointF(40, 30)
        drag_on_canvas(canvas, qapp, start, end)

        after = next(
            i for i in canvas.scene().items() if isinstance(i, RectangleGraphicsItem)
        )
        new_br_scene = QPointF(
            after.pos().x() + after.rect.right(),
            after.pos().y() + after.rect.bottom(),
        )
        assert abs(new_br_scene.x() - 190) < 5
        assert abs(new_br_scene.y() - 160) < 5

    def test_arrow_resize_preserves_scene_endpoint(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas
        from ui.resize_handles import HandleRole

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)

        arrow = ArrowGraphicsItem(
            QPointF(20, 20), QPointF(120, 80), QColor(255, 0, 0), 3
        )
        arrow.setPos(100, 100)
        canvas.scene().addItem(arrow)
        canvas._push_undo_state()
        _select_item(canvas, arrow)

        end_handle = _handle_at(canvas, arrow, HandleRole.ARROW_END)
        start = QPointF(end_handle.rect.x() + 1, end_handle.rect.y() + 1)
        end = start + QPointF(50, 30)
        drag_on_canvas(canvas, qapp, start, end)

        after = next(
            i for i in canvas.scene().items() if isinstance(i, ArrowGraphicsItem)
        )
        cursor_scene_target = canvas.mapToScene(end.toPoint())
        new_end_scene = after.end_point + after.pos()
        assert abs(new_end_scene.x() - cursor_scene_target.x()) < 5
        assert abs(new_end_scene.y() - cursor_scene_target.y()) < 5


class TestHighlightResize:
    def test_resize_preserves_opacity(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas
        from ui.resize_handles import HandleRole

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)

        hl = HighlightGraphicsItem(QRectF(30, 30, 60, 40), QColor(255, 255, 0), opacity=200)
        canvas.scene().addItem(hl)
        _select_item(canvas, hl)

        br = _handle_at(canvas, hl, HandleRole.RECT_BR)
        start = QPointF(br.rect.x() + 1, br.rect.y() + 1)
        end = start + QPointF(20, 10)
        drag_on_canvas(canvas, qapp, start, end)
        after = next(
            i for i in canvas.scene().items() if isinstance(i, HighlightGraphicsItem)
        )

        assert after.opacity == 200
        assert after.color.alpha() == 200
        assert after.rect.width() > 60

    def test_highlight_undo_redo_round_trip(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas
        from ui.resize_handles import HandleRole

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)

        hl = HighlightGraphicsItem(QRectF(40, 40, 50, 30), QColor(0, 255, 0), opacity=180)
        canvas.scene().addItem(hl)
        canvas._push_undo_state()
        _select_item(canvas, hl)

        br = _handle_at(canvas, hl, HandleRole.RECT_BR)
        start = QPointF(br.rect.x() + 1, br.rect.y() + 1)
        end = start + QPointF(30, 20)
        drag_on_canvas(canvas, qapp, start, end)
        post_resize = next(
            i for i in canvas.scene().items() if isinstance(i, HighlightGraphicsItem)
        )
        post = QRectF(post_resize.rect)

        canvas.undo()
        restored = next(
            i for i in canvas.scene().items() if isinstance(i, HighlightGraphicsItem)
        )
        assert QRectF(restored.rect) == QRectF(40, 40, 50, 30)
        canvas.redo()
        redone = next(
            i for i in canvas.scene().items() if isinstance(i, HighlightGraphicsItem)
        )
        assert QRectF(redone.rect) == post


class TestResizeRenderedOutput:
    def test_resized_rectangle_appears_in_rendered_pixmap(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas
        from ui.resize_handles import HandleRole

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)

        rect_item = RectangleGraphicsItem(
            QRectF(50, 50, 40, 30), QColor(255, 0, 0), 3, filled=True
        )
        canvas.scene().addItem(rect_item)
        canvas._push_undo_state()
        _select_item(canvas, rect_item)

        br = _handle_at(canvas, rect_item, HandleRole.RECT_BR)
        start = QPointF(br.rect.x() + 1, br.rect.y() + 1)
        end = start + QPointF(40, 30)
        drag_on_canvas(canvas, qapp, start, end)

        rendered = canvas.render_to_pixmap()
        assert rendered.width() > 0
        after = next(
            i for i in canvas.scene().items() if isinstance(i, RectangleGraphicsItem)
        )
        scene_top_left = QPointF(
            after.pos().x() + after.rect.left(),
            after.pos().y() + after.rect.top(),
        )
        bg = canvas._background_item.pixmap()
        scale_x = bg.width() / bg.devicePixelRatio() / sample_pixmap.width()
        scale_y = bg.height() / bg.devicePixelRatio() / sample_pixmap.height()
        sample = rendered.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
        interior_x = int((scene_top_left.x() + 5) * scale_x)
        interior_y = int((scene_top_left.y() + 5) * scale_y)
        interior_color = QColor(sample.pixel(interior_x, interior_y))
        assert interior_color.red() > 200


class TestResizeLayerBehavior:
    def test_handles_hidden_when_no_selection(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)

        rect_item = RectangleGraphicsItem(QRectF(10, 10, 50, 40), QColor(255, 0, 0), 3)
        canvas.scene().addItem(rect_item)
        _select_item(canvas, rect_item)
        assert canvas._resize_layer.target() is rect_item

        rect_item.setSelected(False)
        QApplication.processEvents()
        canvas._refresh_resize_layer()
        assert canvas._resize_layer.target() is None

    def test_handles_hidden_for_text_item(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas
        from ui.graphics_items import TextGraphicsItem

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)

        text = TextGraphicsItem("hello", QPointF(50, 50), QColor(255, 0, 0), 14, False)
        canvas.scene().addItem(text)
        text.setSelected(True)
        QApplication.processEvents()
        canvas._refresh_resize_layer()
        assert canvas._resize_layer.target() is None

    def test_tool_mode_change_clears_in_flight_resize_state(
        self, qapp, qtbot, sample_pixmap
    ):
        from ui.canvas import AnnotationCanvas
        from ui.resize_handles import HandleRole

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)

        rect_item = RectangleGraphicsItem(QRectF(10, 10, 50, 40), QColor(255, 0, 0), 3)
        canvas.scene().addItem(rect_item)
        _select_item(canvas, rect_item)
        handle = _handle_at(canvas, rect_item, HandleRole.RECT_BR)
        canvas._begin_resize_tracking(handle)
        assert canvas._resize_item is rect_item

        canvas.set_tool_mode(ToolMode.CROP)
        assert canvas._resize_item is None
        assert canvas._resize_handle is None
        assert canvas._resize_geometry_before is None
        assert canvas._resize_pos_before is None

    def test_apply_crop_clears_in_flight_resize_state(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas
        from ui.resize_handles import HandleRole

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)

        rect_item = RectangleGraphicsItem(QRectF(10, 10, 50, 40), QColor(255, 0, 0), 3)
        canvas.scene().addItem(rect_item)
        _select_item(canvas, rect_item)
        handle = _handle_at(canvas, rect_item, HandleRole.RECT_BR)
        canvas._begin_resize_tracking(handle)
        assert canvas._resize_item is rect_item

        assert canvas._apply_crop(QRectF(0, 0, 400, 300))
        assert canvas._resize_item is None
        assert canvas._resize_handle is None
        assert canvas._resize_geometry_before is None
        assert canvas._resize_pos_before is None

    def test_handle_size_is_constant_in_screen_pixels_at_zoom_changes(
        self, qapp, qtbot, sample_pixmap
    ):
        from ui.canvas import AnnotationCanvas
        from ui.resize_handles import HandleRole

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)

        rect_item = RectangleGraphicsItem(QRectF(100, 100, 80, 60), QColor(255, 0, 0), 3)
        canvas.scene().addItem(rect_item)
        _select_item(canvas, rect_item)

        canvas.zoom_to_fit()
        small = next(
            h for h in canvas._resize_layer._handles if h.role is HandleRole.RECT_TL
        )
        small_size = small.rect.width()

        canvas.scale(0.2, 0.2)
        large = next(
            h for h in canvas._resize_layer._handles if h.role is HandleRole.RECT_TL
        )
        large_size = large.rect.width()
        assert small_size == large_size

    def test_handles_refresh_after_select_tool_drag(self, qapp, qtbot, sample_pixmap):
        from tests.conftest import drag_item_on_canvas
        from ui.canvas import AnnotationCanvas
        from ui.resize_handles import HandleRole

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)

        rect_item = RectangleGraphicsItem(QRectF(50, 50, 80, 60), QColor(255, 0, 0), 3)
        canvas.scene().addItem(rect_item)
        _select_item(canvas, rect_item)

        canvas._refresh_resize_layer()
        before_br = next(
            h for h in canvas._resize_layer._handles if h.role is HandleRole.RECT_BR
        )
        before_rect = QRectF(before_br.rect)

        drag_item_on_canvas(
            canvas, qapp, QPointF(80, 70), QPointF(180, 170)
        )

        # The drag-committed refresh in _commit_drag_tracking must have moved
        # the handles; rely on the layer's own state, not a manual refresh.
        after_br = next(
            h for h in canvas._resize_layer._handles if h.role is HandleRole.RECT_BR
        )
        after_rect = QRectF(after_br.rect)
        assert after_rect.x() > before_rect.x() + 50

    def test_non_left_release_clears_in_flight_resize(self, qapp, qtbot, sample_pixmap):
        from PySide6.QtCore import QEvent, QPoint, Qt
        from PySide6.QtGui import QMouseEvent
        from ui.canvas import AnnotationCanvas
        from ui.resize_handles import HandleRole

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)

        rect_item = RectangleGraphicsItem(QRectF(20, 20, 60, 50), QColor(255, 0, 0), 3)
        canvas.scene().addItem(rect_item)
        _select_item(canvas, rect_item)
        handle = _handle_at(canvas, rect_item, HandleRole.RECT_BR)
        canvas._begin_resize_tracking(handle)
        assert canvas._resize_item is rect_item

        viewport = canvas.viewport()
        release_pos = QPoint(handle.rect.x() + 1, handle.rect.y() + 1)
        event = QMouseEvent(
            QEvent.MouseButtonRelease,
            QPointF(release_pos),
            viewport.mapToGlobal(release_pos),
            Qt.MouseButton.RightButton,
            Qt.NoButton,
            Qt.NoModifier,
        )
        qapp.sendEvent(viewport, event)

        assert canvas._resize_item is None
        assert canvas._resize_handle is None
        assert canvas._resize_geometry_before is None
        assert canvas._resize_pos_before is None

    def test_undo_clears_in_flight_resize_state(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas
        from ui.resize_handles import HandleRole

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)

        rect_item = RectangleGraphicsItem(QRectF(20, 20, 60, 50), QColor(255, 0, 0), 3)
        canvas.scene().addItem(rect_item)
        _select_item(canvas, rect_item)
        handle = _handle_at(canvas, rect_item, HandleRole.RECT_BR)
        canvas._begin_resize_tracking(handle)
        assert canvas._resize_item is rect_item

        canvas.undo()
        assert canvas._resize_item is None

    def test_redo_clears_in_flight_resize_state(self, qapp, qtbot, sample_pixmap):
        from ui.canvas import AnnotationCanvas
        from ui.resize_handles import HandleRole

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)

        rect_item = RectangleGraphicsItem(QRectF(20, 20, 60, 50), QColor(255, 0, 0), 3)
        canvas.scene().addItem(rect_item)
        canvas._push_undo_state()
        _select_item(canvas, rect_item)
        handle = _handle_at(canvas, rect_item, HandleRole.RECT_BR)
        canvas._begin_resize_tracking(handle)
        assert canvas._resize_item is rect_item

        canvas.undo()
        canvas.redo()
        assert canvas._resize_item is None

    def test_delete_selected_clears_in_flight_resize_state(
        self, qapp, qtbot, sample_pixmap
    ):
        from ui.canvas import AnnotationCanvas
        from ui.resize_handles import HandleRole

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)

        rect_item = RectangleGraphicsItem(QRectF(20, 20, 60, 50), QColor(255, 0, 0), 3)
        canvas.scene().addItem(rect_item)
        _select_item(canvas, rect_item)
        handle = _handle_at(canvas, rect_item, HandleRole.RECT_BR)
        canvas._begin_resize_tracking(handle)
        assert canvas._resize_item is rect_item

        canvas.delete_selected()
        assert canvas._resize_item is None

    def test_load_image_clears_in_flight_resize_state(
        self, qapp, qtbot, sample_pixmap
    ):
        from PySide6.QtGui import QPixmap, QColor
        from ui.canvas import AnnotationCanvas
        from ui.resize_handles import HandleRole

        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(800, 600)
        canvas.load_image(sample_pixmap)
        canvas.set_tool_mode(ToolMode.SELECT)

        rect_item = RectangleGraphicsItem(QRectF(20, 20, 60, 50), QColor(255, 0, 0), 3)
        canvas.scene().addItem(rect_item)
        _select_item(canvas, rect_item)
        handle = _handle_at(canvas, rect_item, HandleRole.RECT_BR)
        canvas._begin_resize_tracking(handle)

        new_pixmap = QPixmap(100, 100)
        new_pixmap.fill(QColor("steelblue"))
        canvas.load_image(new_pixmap)
        assert canvas._resize_item is None
