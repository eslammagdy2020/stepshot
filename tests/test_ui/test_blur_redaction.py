"""Phase 9 — safe blur/redaction model.

Locks the redaction contract: a blur/pixelate patch obscures the pixels under
its visible location, cannot be moved or duplicated to reveal content sampled
elsewhere, survives undo/redo and crop exactly, and never destroys the original
capture (Reset All restores the pre-blur screenshot). Pixel assertions use a
non-uniform source so a stale or misplaced patch cannot pass.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QGraphicsItem

from tests.conftest import left_move, left_press, left_release
from ui.canvas import AnnotationCanvas, ToolMode
from ui.graphics_items import BlurPatchGraphicsItem


def gradient_pixmap(width: int = 200, height: int = 200) -> QPixmap:
    pixmap = QPixmap(width, height)
    painter = QPainter(pixmap)
    gradient = QLinearGradient(0, 0, width, height)
    gradient.setColorAt(0.0, QColor(0, 0, 0))
    gradient.setColorAt(0.5, QColor(0, 200, 0))
    gradient.setColorAt(1.0, QColor(255, 255, 255))
    painter.fillRect(0, 0, width, height, gradient)
    painter.end()
    return pixmap


def draw_blur(canvas, qtbot, start: QPointF, end: QPointF, mode: ToolMode = ToolMode.BLUR) -> None:
    canvas.set_tool_mode(mode)
    left_press(canvas.viewport(), qtbot, canvas.mapFromScene(start))
    left_move(canvas.viewport(), qtbot, canvas.mapFromScene(end))
    left_release(canvas.viewport(), qtbot, canvas.mapFromScene(end))


def _patches(canvas):
    return [i for i in canvas.scene().items() if isinstance(i, BlurPatchGraphicsItem)]


def _rendered_region(canvas, rect: QRectF) -> QImage:
    rendered = canvas.render_to_pixmap().toImage()
    physical = canvas._logical_to_physical_rect(rect)
    return rendered.copy(physical)


def _images_differ(a: QImage, b: QImage) -> bool:
    if a.size() != b.size():
        return True
    for y in range(0, a.height(), max(1, a.height() // 20)):
        for x in range(0, a.width(), max(1, a.width() // 20)):
            if a.pixel(x, y) != b.pixel(x, y):
                return True
    return False


class TestBlurObscuresPixels:
    def test_blur_changes_rendered_pixels_under_patch(self, qapp, qtbot):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        source = gradient_pixmap()
        canvas.load_image(source)
        rect = QRectF(60, 60, 80, 60)

        before = _rendered_region(canvas, rect)
        draw_blur(canvas, qtbot, rect.topLeft(), rect.bottomRight())
        after = _rendered_region(canvas, rect)

        assert len(_patches(canvas)) == 1
        assert _images_differ(before, after)

    def test_pixelate_changes_rendered_pixels_under_patch(self, qapp, qtbot):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(gradient_pixmap())
        canvas.set_blur_mode(canvas._blur_mode.__class__.PIXELATE)
        rect = QRectF(50, 50, 90, 70)

        before = _rendered_region(canvas, rect)
        draw_blur(canvas, qtbot, rect.topLeft(), rect.bottomRight(), ToolMode.BLUR)
        after = _rendered_region(canvas, rect)

        assert len(_patches(canvas)) == 1
        assert _images_differ(before, after)


class TestPatchIsNotMovable:
    def test_patch_lacks_movable_flag(self, qapp, qtbot):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(gradient_pixmap())
        draw_blur(canvas, qtbot, QPointF(60, 60), QPointF(140, 120))

        patch = _patches(canvas)[0]
        assert not (patch.flags() & QGraphicsItem.ItemIsMovable)
        assert patch.flags() & QGraphicsItem.ItemIsSelectable

    def test_patch_is_not_duplicated(self, qapp, qtbot):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(gradient_pixmap())
        draw_blur(canvas, qtbot, QPointF(60, 60), QPointF(140, 120))

        patch = _patches(canvas)[0]
        patch.setSelected(True)
        undo_depth = len(canvas._undo_stack)

        canvas.duplicate_selected()

        assert len(_patches(canvas)) == 1
        assert len(canvas._undo_stack) == undo_depth


class TestUndoRedoRestoresPixels:
    def test_undo_removes_patch_and_restores_original_pixels(self, qapp, qtbot):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(gradient_pixmap())
        rect = QRectF(60, 60, 80, 60)
        before = _rendered_region(canvas, rect)

        draw_blur(canvas, qtbot, rect.topLeft(), rect.bottomRight())
        blurred = _rendered_region(canvas, rect)

        canvas.undo()
        assert _patches(canvas) == []
        assert not _images_differ(before, _rendered_region(canvas, rect))

        canvas.redo()
        assert len(_patches(canvas)) == 1
        assert not _images_differ(blurred, _rendered_region(canvas, rect))


class TestCropKeepsPatchAligned:
    def test_source_rect_translates_with_crop(self, qapp, qtbot):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(gradient_pixmap())
        draw_blur(canvas, qtbot, QPointF(60, 60), QPointF(140, 120))
        before = QRectF(_patches(canvas)[0].source_rect)

        canvas._apply_crop(QRectF(30, 30, 140, 140))
        canvas._push_undo_state()

        patch = _patches(canvas)[0]
        assert patch.source_rect.topLeft().x() == before.left() - 30
        assert patch.source_rect.topLeft().y() == before.top() - 30

    def test_undo_crop_restores_source_rect(self, qapp, qtbot):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(gradient_pixmap())
        draw_blur(canvas, qtbot, QPointF(60, 60), QPointF(140, 120))
        original = QRectF(_patches(canvas)[0].source_rect)

        canvas._apply_crop(QRectF(30, 30, 140, 140))
        canvas._push_undo_state()
        canvas.undo()

        assert _patches(canvas)[0].source_rect == original


class TestSnapshotDoesNotAlias:
    def test_in_place_source_rect_edit_does_not_mutate_snapshot(self, qapp, qtbot):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        canvas.load_image(gradient_pixmap())
        draw_blur(canvas, qtbot, QPointF(60, 60), QPointF(140, 120))

        snapshot = canvas._snapshot_state()
        stored = next(entry for entry in snapshot if entry[0] == "blur")[5]
        captured = QRectF(stored)

        _patches(canvas)[0].source_rect.translate(-25, -25)

        assert stored == captured


class TestResetRestoresOriginal:
    def test_reset_removes_patch_and_restores_capture(self, qapp, qtbot):
        canvas = AnnotationCanvas()
        qtbot.addWidget(canvas)
        source = gradient_pixmap()
        canvas.load_image(source)
        rect = QRectF(60, 60, 80, 60)
        before = _rendered_region(canvas, rect)

        draw_blur(canvas, qtbot, rect.topLeft(), rect.bottomRight())
        assert canvas.reset_to_original() is True

        assert _patches(canvas) == []
        assert not _images_differ(before, _rendered_region(canvas, rect))
