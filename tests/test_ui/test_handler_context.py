"""Tests for HandlerContext interface and MainWindow-facing canvas methods."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsItem

from tools.handlers.arrow import ArrowHandler
from tools.handlers.blur import BlurHandler
from tools.handlers.context import HandlerContext
from tools.handlers.crop import CropHandler
from tools.handlers.highlight import HighlightHandler
from tools.handlers.pen import PenHandler
from tools.handlers.rectangle import RectangleHandler
from tools.handlers.step import StepHandler
from tools.handlers.text import TextHandler
from ui.canvas import AnnotationCanvas
from models.step_marker import StepCounter
from ui.graphics_items import TextGraphicsItem


class FakeHandlerContext:
    """Minimal fake HandlerContext for testing handlers without a real canvas."""

    def __init__(self):
        self.items = []
        self.removed_items = []
        self.undo_pushes = 0
        self.image_changed_emits = 0
        self.blur_regions = []
        self.crop_rects = []
        self.text_edits_started = []
        self.text_edits_finalized = 0
        self.editing_text = False

    def add_item(self, item: QGraphicsItem) -> None:
        self.items.append(item)

    def remove_item(self, item: QGraphicsItem) -> None:
        if item in self.items:
            self.items.remove(item)
        self.removed_items.append(item)

    def push_undo_state(self) -> None:
        self.undo_pushes += 1

    def emit_image_changed(self) -> None:
        self.image_changed_emits += 1

    def apply_blur_region(self, rect: QRectF) -> None:
        self.blur_regions.append(rect)

    def apply_crop(self, rect: QRectF) -> bool:
        self.crop_rects.append(rect)
        return True

    def get_arrow_settings(self) -> tuple[QColor, int]:
        return QColor(255, 0, 0), 3

    def get_rectangle_settings(self) -> tuple[QColor, int, bool]:
        return QColor(0, 255, 0), 2, False

    def get_highlight_settings(self) -> tuple[QColor, int]:
        return QColor(255, 255, 0), 128

    def get_step_settings(self) -> tuple[QColor, int, StepCounter]:
        counter = StepCounter()
        return QColor(255, 0, 0), 28, counter

    def get_text_settings(self) -> tuple[QColor, int, bool]:
        return QColor(0, 0, 0), 14, False

    def get_pen_settings(self) -> tuple[QColor, int]:
        return QColor(0, 0, 255), 3

    def get_text_item_at(self, scene_pos: QPointF) -> TextGraphicsItem | None:
        return None

    def start_text_edit(self, item: TextGraphicsItem, *, is_new: bool) -> None:
        self.text_edits_started.append((item, is_new))
        self.editing_text = True

    def finalize_text_edit(self) -> None:
        self.text_edits_finalized += 1
        self.editing_text = False

    def is_editing_text(self) -> bool:
        return self.editing_text


class TestHandlerContextProtocol:
    def test_fake_context_implements_protocol(self, qapp):
        """Verify FakeHandlerContext satisfies the HandlerContext protocol."""
        ctx = FakeHandlerContext()
        assert isinstance(ctx, HandlerContext)

    def test_arrow_handler_uses_context(self, qapp):
        """ArrowHandler should use context methods for settings and scene operations."""
        ctx = FakeHandlerContext()
        handler = ArrowHandler()
        handler.attach(ctx)

        # Press creates preview
        handler.on_press(QPointF(10, 10))
        assert len(ctx.items) == 1

        # Move updates preview
        handler.on_move(QPointF(100, 100))

        # Release with sufficient distance commits
        handler.on_release(QPointF(100, 100))
        assert ctx.undo_pushes == 1
        assert ctx.image_changed_emits == 1
        assert len(ctx.items) == 1  # Preview removed, real item added

    def test_arrow_handler_short_drag_discarded(self, qapp):
        """ArrowHandler should discard short drags via context.remove_item."""
        ctx = FakeHandlerContext()
        handler = ArrowHandler()
        handler.attach(ctx)

        handler.on_press(QPointF(10, 10))
        handler.on_release(QPointF(11, 11))  # Too short
        assert ctx.undo_pushes == 0
        assert ctx.image_changed_emits == 0
        assert len(ctx.items) == 0  # Preview removed

    def test_rectangle_handler_uses_context(self, qapp):
        """RectangleHandler should use context for settings and commits."""
        ctx = FakeHandlerContext()
        handler = RectangleHandler()
        handler.attach(ctx)

        handler.on_press(QPointF(10, 10))
        handler.on_move(QPointF(100, 100))
        handler.on_release(QPointF(100, 100))
        assert ctx.undo_pushes == 1
        assert ctx.image_changed_emits == 1
        assert len(ctx.items) == 1

    def test_highlight_handler_uses_context(self, qapp):
        """HighlightHandler should use context for settings and commits."""
        ctx = FakeHandlerContext()
        handler = HighlightHandler()
        handler.attach(ctx)

        handler.on_press(QPointF(10, 10))
        handler.on_release(QPointF(100, 100))
        assert ctx.undo_pushes == 1
        assert ctx.image_changed_emits == 1
        assert len(ctx.items) == 1

    def test_blur_handler_uses_context(self, qapp):
        """BlurHandler should call apply_blur_region via context."""
        ctx = FakeHandlerContext()
        handler = BlurHandler()
        handler.attach(ctx)

        handler.on_press(QPointF(10, 10))
        handler.on_release(QPointF(100, 100))
        assert len(ctx.blur_regions) == 1
        assert ctx.undo_pushes == 1
        assert ctx.image_changed_emits == 1

    def test_crop_handler_uses_context(self, qapp):
        """CropHandler should call apply_crop via context."""
        ctx = FakeHandlerContext()
        handler = CropHandler()
        handler.attach(ctx)

        handler.on_press(QPointF(10, 10))
        handler.on_release(QPointF(100, 100))
        assert len(ctx.crop_rects) == 1
        assert ctx.undo_pushes == 1
        assert ctx.image_changed_emits == 1

    def test_pen_handler_uses_context(self, qapp):
        """PenHandler should use context for settings and commits."""
        ctx = FakeHandlerContext()
        handler = PenHandler()
        handler.attach(ctx)

        handler.on_press(QPointF(10, 10))
        handler.on_move(QPointF(20, 20))
        handler.on_release(QPointF(30, 30))
        assert ctx.undo_pushes == 1
        assert ctx.image_changed_emits == 1
        assert len(ctx.items) == 1

    def test_pen_handler_single_point_discarded(self, qapp):
        """PenHandler should discard single-point strokes."""
        ctx = FakeHandlerContext()
        handler = PenHandler()
        handler.attach(ctx)

        handler.on_press(QPointF(10, 10))
        handler.on_release(QPointF(10, 10))
        assert ctx.undo_pushes == 0
        assert ctx.image_changed_emits == 0
        assert len(ctx.items) == 0

    def test_step_handler_uses_context(self, qapp):
        """StepHandler should use context for counter and commits."""
        ctx = FakeHandlerContext()
        handler = StepHandler()
        handler.attach(ctx)

        handler.on_press(QPointF(50, 50))
        assert len(ctx.items) == 1
        assert ctx.undo_pushes == 1
        assert ctx.image_changed_emits == 1

    def test_text_handler_uses_context(self, qapp):
        """TextHandler should use context for text editing lifecycle."""
        ctx = FakeHandlerContext()
        handler = TextHandler()
        handler.attach(ctx)

        handler.on_press(QPointF(50, 50))
        assert len(ctx.text_edits_started) == 1
        assert ctx.text_edits_started[0][1] is True  # is_new
        assert len(ctx.items) == 1

    def test_text_handler_clicks_existing_item(self, qapp):
        """TextHandler should start edit on existing item via context."""
        ctx = FakeHandlerContext()
        handler = TextHandler()
        handler.attach(ctx)

        # Create a mock text item
        mock_item = MagicMock(spec=TextGraphicsItem)
        ctx.get_text_item_at = lambda pos: mock_item

        handler.on_press(QPointF(50, 50))
        assert len(ctx.text_edits_started) == 1
        assert ctx.text_edits_started[0][0] is mock_item
        assert ctx.text_edits_started[0][1] is False  # not new

    def test_text_handler_finalizes_before_new(self, qapp):
        """TextHandler should finalize existing edit before starting new one."""
        ctx = FakeHandlerContext()
        handler = TextHandler()
        handler.attach(ctx)

        # First press starts edit on new item
        handler.on_press(QPointF(50, 50))
        assert ctx.editing_text is True
        assert len(ctx.text_edits_started) == 1
        assert ctx.text_edits_started[0][1] is True

        # Second press with no item at position: finalizes first, does NOT create new
        handler.on_press(QPointF(100, 100))
        assert ctx.text_edits_finalized == 1
        # No new edit started because no item at click position
        assert ctx.editing_text is False
        assert len(ctx.text_edits_started) == 1

        # Third press with no item at position: creates new item
        handler.on_press(QPointF(200, 200))
        assert ctx.editing_text is True
        assert len(ctx.text_edits_started) == 2
        assert ctx.text_edits_started[1][1] is True

    def test_rect_drag_handler_cancel_cleans_up(self, qapp):
        """RectDragHandler.cancel should remove preview via context."""
        ctx = FakeHandlerContext()
        handler = RectangleHandler()
        handler.attach(ctx)

        handler.on_press(QPointF(10, 10))
        assert len(ctx.items) == 1
        handler.cancel()
        assert len(ctx.items) == 0
        assert len(ctx.removed_items) == 1


class TestMainWindowCanvasInterface:
    """Tests for canvas methods used by MainWindow."""

    @pytest.fixture
    def canvas(self, qtbot, sample_pixmap):
        c = AnnotationCanvas()
        qtbot.addWidget(c)
        c.load_image(sample_pixmap)
        return c

    def test_annotation_count_returns_zero_before_load(self, qtbot):
        """annotation_count should return 0 before any image is loaded."""
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        assert canvas.annotation_count() == 0

    def test_annotation_count_increments_with_items(self, canvas):
        """annotation_count should reflect number of annotation items."""
        assert canvas.annotation_count() == 0

        from ui.graphics_items import ArrowGraphicsItem
        arrow = ArrowGraphicsItem(QPointF(10, 10), QPointF(100, 100), QColor(255, 0, 0), 3)
        canvas.scene().addItem(arrow)
        assert canvas.annotation_count() == 1

        from ui.graphics_items import RectangleGraphicsItem
        rect = RectangleGraphicsItem(QRectF(20, 20, 50, 50), QColor(0, 255, 0), 2, False)
        canvas.scene().addItem(rect)
        assert canvas.annotation_count() == 2

    def test_annotation_count_excludes_background(self, canvas):
        """annotation_count should not count the background item."""
        assert canvas.annotation_count() == 0
        # Background exists but count is still 0
        assert canvas._background_item is not None

    def test_current_zoom_returns_scale(self, canvas):
        """current_zoom should return the current transform scale."""
        # Default zoom after load is fit-to-window, so scale varies
        zoom = canvas.current_zoom()
        assert zoom > 0

    def test_current_zoom_changes_with_scale(self, canvas):
        """current_zoom should reflect scale changes."""
        initial = canvas.current_zoom()
        canvas.scale(2.0, 2.0)
        assert canvas.current_zoom() == initial * 2.0

    def test_has_background_true_after_load(self, canvas):
        """has_background should return True after image load."""
        assert canvas.has_background() is True

    def test_has_background_false_before_load(self, qtbot):
        """has_background should return False before image load."""
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        assert canvas.has_background() is False

    def test_has_screenshot_true_after_load(self, canvas):
        """has_screenshot should return True after image load."""
        assert canvas.has_screenshot() is True

    def test_annotation_count_updates_after_delete(self, canvas):
        """annotation_count should update after delete_selected."""
        from ui.graphics_items import ArrowGraphicsItem
        arrow = ArrowGraphicsItem(QPointF(10, 10), QPointF(100, 100), QColor(255, 0, 0), 3)
        canvas.scene().addItem(arrow)
        assert canvas.annotation_count() == 1

        arrow.setSelected(True)
        canvas.delete_selected()
        assert canvas.annotation_count() == 0

    def test_annotation_count_updates_after_undo(self, canvas):
        """annotation_count should update after undo."""
        from ui.graphics_items import ArrowGraphicsItem
        arrow = ArrowGraphicsItem(QPointF(10, 10), QPointF(100, 100), QColor(255, 0, 0), 3)
        canvas.scene().addItem(arrow)
        canvas._push_undo_state()
        assert canvas.annotation_count() == 1

        canvas.undo()
        assert canvas.annotation_count() == 0


class TestHandlerContextMutationCheck:
    """Mutation-check tests: reverting a context method to no-op should break a specific test."""

    def test_apply_blur_region_mutation(self):
        """Reverting apply_blur_region to no-op should break blur handler test."""
        ctx = FakeHandlerContext()
        original = ctx.apply_blur_region
        ctx.apply_blur_region = lambda rect: None  # Mutation: no-op

        handler = BlurHandler()
        handler.attach(ctx)
        handler.on_press(QPointF(10, 10))
        handler.on_release(QPointF(100, 100))

        # With mutation, blur_regions should be empty
        assert len(ctx.blur_regions) == 0

        # Restore
        ctx.apply_blur_region = original
        ctx.blur_regions.clear()
        handler.on_press(QPointF(10, 10))
        handler.on_release(QPointF(100, 100))
        assert len(ctx.blur_regions) == 1

    def test_apply_crop_mutation(self):
        """Reverting apply_crop to return False should break crop handler test."""
        ctx = FakeHandlerContext()
        original = ctx.apply_crop
        ctx.apply_crop = lambda rect: False  # Mutation: always fail

        handler = CropHandler()
        handler.attach(ctx)
        handler.on_press(QPointF(10, 10))
        handler.on_release(QPointF(100, 100))

        # With mutation, undo should not be pushed (crop failed)
        assert ctx.undo_pushes == 0

        # Restore
        ctx.apply_crop = original
        ctx.undo_pushes = 0
        handler.on_press(QPointF(10, 10))
        handler.on_release(QPointF(100, 100))
        assert ctx.undo_pushes == 1

    def test_get_text_item_at_mutation(self):
        """Reverting get_text_item_at to always return None should break text handler test."""
        ctx = FakeHandlerContext()
        mock_item = MagicMock(spec=TextGraphicsItem)
        original = ctx.get_text_item_at
        ctx.get_text_item_at = lambda pos: mock_item

        handler = TextHandler()
        handler.attach(ctx)
        handler.on_press(QPointF(50, 50))

        # Should start edit on the mock item
        assert len(ctx.text_edits_started) == 1
        assert ctx.text_edits_started[0][0] is mock_item

        # Mutation: return None
        ctx.get_text_item_at = lambda pos: None
        ctx.text_edits_started.clear()
        # First finalize the existing edit
        handler.on_press(QPointF(100, 100))  # This finalizes
        # Now editing is done, press again to create new
        handler.on_press(QPointF(200, 200))

        # Should create new item (is_new=True)
        assert len(ctx.text_edits_started) == 1
        assert ctx.text_edits_started[0][1] is True