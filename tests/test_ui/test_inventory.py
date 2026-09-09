"""Tests for multi-screenshot inventory on the canvas."""

from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPixmap

from tests.conftest import draw_arrow_on_canvas
from ui.canvas import AnnotationCanvas
from ui.graphics_items import ArrowGraphicsItem


def _pixmap(color: tuple[int, int, int]) -> QPixmap:
    pixmap = QPixmap(640, 480)
    pixmap.fill(QColor(*color))
    return pixmap


class TestInventoryAddSwitch:
    def test_add_two_screenshots_counter(self, qapp, qtbot):
        """Two adds yield count 2 and 1-based index 2."""
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.add_screenshot(_pixmap((70, 130, 180)), "region")
        canvas.add_screenshot(_pixmap((180, 70, 70)), "fullscreen")
        assert canvas.inventory_count == 2
        assert canvas.current_index_1based == 2

    def test_annotations_persist_across_switch(self, qapp, qtbot):
        """Annotations on #1 survive a round-trip to #2."""
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.add_screenshot(_pixmap((70, 130, 180)), "region")
        draw_arrow_on_canvas(canvas, qtbot, QPointF(50, 50), QPointF(200, 150))
        assert canvas.annotation_count() == 1
        canvas.add_screenshot(_pixmap((180, 70, 70)), "fullscreen")
        assert canvas.annotation_count() == 0
        assert canvas.switch_to(0) is True
        assert canvas.annotation_count() == 1
        arrows = [i for i in canvas.scene().items() if isinstance(i, ArrowGraphicsItem)]
        assert len(arrows) == 1

    def test_undo_isolated_per_screenshot(self, qapp, qtbot):
        """Undo on #1 does not affect #2."""
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.add_screenshot(_pixmap((70, 130, 180)), "region")
        draw_arrow_on_canvas(canvas, qtbot, QPointF(50, 50), QPointF(200, 150))
        canvas.add_screenshot(_pixmap((180, 70, 70)), "fullscreen")
        draw_arrow_on_canvas(canvas, qtbot, QPointF(60, 60), QPointF(210, 160))
        assert canvas.annotation_count() == 1
        canvas.switch_to(0)
        assert canvas.annotation_count() == 1
        canvas.undo()
        assert canvas.annotation_count() == 0
        canvas.switch_to(1)
        assert canvas.annotation_count() == 1

    def test_prev_next_navigation(self, qapp, qtbot):
        """Prev/next move the active screenshot."""
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.add_screenshot(_pixmap((70, 130, 180)), "region")
        canvas.add_screenshot(_pixmap((180, 70, 70)), "fullscreen")
        assert canvas.can_go_prev() is True
        assert canvas.can_go_next() is False
        assert canvas.prev_screenshot() is True
        assert canvas.current_index_1based == 1
        assert canvas.can_go_next() is True
        assert canvas.next_screenshot() is True
        assert canvas.current_index_1based == 2

    def test_switch_same_index_noop(self, qapp, qtbot):
        """Switching to the active index is a no-op."""
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.add_screenshot(_pixmap((70, 130, 180)), "region")
        assert canvas.switch_to(0) is False


class TestInventoryDeleteClear:
    def test_remove_current_selects_neighbor(self, qapp, qtbot):
        """Delete removes active and neighbor becomes active."""
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.add_screenshot(_pixmap((70, 130, 180)), "region")
        canvas.add_screenshot(_pixmap((180, 70, 70)), "fullscreen")
        canvas.add_screenshot(_pixmap((70, 180, 130)), "region")
        canvas.switch_to(1)
        assert canvas.remove_current() is True
        assert canvas.inventory_count == 2
        assert canvas.has_screenshot() is True

    def test_remove_last_empties_placeholder(self, qapp, qtbot):
        """Deleting the last screenshot shows the empty placeholder."""
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.add_screenshot(_pixmap((70, 130, 180)), "region")
        assert canvas.remove_current() is True
        assert canvas.inventory_count == 0
        assert canvas.has_screenshot() is False
        assert canvas._background_item is None

    def test_clear_inventory(self, qapp, qtbot):
        """Clear All empties inventory and canvas."""
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.add_screenshot(_pixmap((70, 130, 180)), "region")
        canvas.add_screenshot(_pixmap((180, 70, 70)), "fullscreen")
        canvas.clear_inventory()
        assert canvas.inventory_count == 0
        assert canvas.has_screenshot() is False

    def test_reset_all_scoped_to_current(self, qapp, qtbot):
        """Reset All clears annotations on active only."""
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.add_screenshot(_pixmap((70, 130, 180)), "region")
        draw_arrow_on_canvas(canvas, qtbot, QPointF(50, 50), QPointF(200, 150))
        canvas.add_screenshot(_pixmap((180, 70, 70)), "fullscreen")
        assert canvas.annotation_count() == 0
        canvas.switch_to(0)
        assert canvas.annotation_count() == 1
        assert canvas.reset_to_original() is True
        assert canvas.annotation_count() == 0
        canvas.switch_to(1)
        assert canvas.annotation_count() == 0
        canvas.switch_to(0)
        assert canvas.annotation_count() == 0


class TestInventoryToolbarState:
    def test_load_shim_adds_to_inventory(self, qapp, qtbot, sample_pixmap):
        """Legacy load_image appends instead of replacing."""
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(sample_pixmap)
        canvas.load_image(sample_pixmap)
        assert canvas.inventory_count == 2

    def test_inventory_changed_emitted(self, qapp, qtbot):
        """Add/switch/remove emit inventory_changed."""
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        fired: list[bool] = []
        canvas.inventory_changed.connect(lambda: fired.append(True))
        canvas.add_screenshot(_pixmap((70, 130, 180)), "region")
        canvas.add_screenshot(_pixmap((180, 70, 70)), "fullscreen")
        canvas.switch_to(0)
        canvas.remove_current()
        assert len(fired) == 4

    def test_copy_renders_active(self, qapp, qtbot):
        """render_to_pixmap works after switching."""
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.add_screenshot(_pixmap((70, 130, 180)), "region")
        canvas.add_screenshot(_pixmap((180, 70, 70)), "fullscreen")
        canvas.switch_to(0)
        rendered = canvas.render_to_pixmap()
        assert not rendered.isNull()
        assert rendered.width() == 640
