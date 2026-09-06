"""Tests for the Qt annotation adapters between canvas items and records."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPixmap

from models.document_history import (
    AnnotationRecord,
    ImageFormat,
    ImageValue,
)
from ui.annotation_adapters import (
    build_canvas_registry,
    capture_annotation,
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


def _solid_pixmap(width: int, height: int, color: QColor, ratio: float = 1.0) -> QPixmap:
    pixmap = QPixmap(width, height)
    pixmap.fill(color)
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


def _to_qimage(pixmap: QPixmap) -> QImage:
    return pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)


class TestImageConversion:
    def test_round_trip_preserves_pixels_and_dimensions(self):
        original = _solid_pixmap(37, 5, QColor(255, 0, 0))
        value = qpixmap_to_image_value(original)

        assert value.width == 37
        assert value.height == 5
        assert value.format is ImageFormat.RGBA8888
        assert value.stride >= 37 * 4
        assert len(value.pixels) == value.stride * value.height

        restored = image_value_to_qpixmap(value)
        assert restored.width() == 37
        assert restored.height() == 5
        before = _to_qimage(original)
        after = _to_qimage(restored)
        assert after == before

    def test_round_trip_preserves_device_pixel_ratio(self):
        original = _solid_pixmap(20, 10, QColor(0, 128, 255), ratio=2.0)
        value = qpixmap_to_image_value(original)
        assert value.device_pixel_ratio == 2.0

        restored = image_value_to_qpixmap(value)
        assert restored.devicePixelRatio() == 2.0

    def test_round_trip_preserves_odd_width_pixels(self):
        original = QPixmap(37, 5)
        original.fill(QColor(255, 0, 0))
        painter = QPainter(original)
        painter.fillRect(36, 0, 1, 5, QColor(0, 0, 255))
        painter.end()

        restored = image_value_to_qpixmap(qpixmap_to_image_value(original))
        before = _to_qimage(original)
        after = _to_qimage(restored)
        assert after.pixelColor(0, 2).red() == 255
        assert after.pixelColor(36, 2).blue() == 255
        assert after == before


class TestArrowAdapter:
    def test_round_trip_preserves_scene_geometry_and_properties(self):
        original = ArrowGraphicsItem(QPointF(10, 20), QPointF(80, 95), QColor(255, 0, 0), 4)

        record = capture_annotation(original)
        assert isinstance(record, AnnotationRecord)
        assert record.kind == "arrow"

        restored = restore_annotation(build_canvas_registry(), record)
        assert isinstance(restored, ArrowGraphicsItem)
        assert restored.start_point == original.start_point
        assert restored.end_point == original.end_point
        assert restored.color.rgba() == original.color.rgba()
        assert restored.thickness == original.thickness

    def test_round_trip_includes_item_position(self, qapp):
        original = ArrowGraphicsItem(QPointF(5, 5), QPointF(15, 15), QColor(255, 0, 0), 3)
        original.setPos(QPointF(100, 50))

        restored = restore_annotation(build_canvas_registry(), capture_annotation(original))
        assert isinstance(restored, ArrowGraphicsItem)
        assert restored.start_point + restored.pos() == original.start_point + original.pos()
        assert restored.end_point + restored.pos() == original.end_point + original.pos()


class TestStepMarkerAdapter:
    def test_round_trip_preserves_position_number_color_size(self):
        original = StepMarkerGraphicsItem(QPointF(120, 75), 7, QColor(0, 200, 100), 36)

        record = capture_annotation(original)
        assert record.kind == "step"

        restored = restore_annotation(build_canvas_registry(), record)
        assert isinstance(restored, StepMarkerGraphicsItem)
        assert restored.pos() == original.pos()
        assert restored.number == original.number
        assert QColor(restored.marker_color).rgba() == QColor(original.marker_color).rgba()
        assert restored.marker_size == original.marker_size


class TestTextAdapter:
    def test_round_trip_preserves_text_properties(self):
        original = TextGraphicsItem("Hello", QPointF(30, 40), QColor(10, 20, 30), 17, True)

        record = capture_annotation(original)
        assert record.kind == "text"

        restored = restore_annotation(build_canvas_registry(), record)
        assert isinstance(restored, TextGraphicsItem)
        assert restored.pos() == original.pos()
        assert restored.toPlainText() == original.toPlainText()
        assert QColor(restored.text_color).rgba() == QColor(original.text_color).rgba()
        assert restored.font_size == original.font_size
        assert restored.bold == original.bold


class TestRectangleAdapter:
    def test_round_trip_preserves_local_rect_position_and_properties(self):
        original = RectangleGraphicsItem(QRectF(11, 12, 60, 45), QColor(0, 255, 0), 5, True)
        original.setPos(QPointF(300, 200))

        record = capture_annotation(original)
        assert record.kind == "rectangle"

        restored = restore_annotation(build_canvas_registry(), record)
        assert isinstance(restored, RectangleGraphicsItem)
        assert restored.pos() == original.pos()
        assert restored.rect == original.rect
        assert QColor(restored.color).rgba() == QColor(original.color).rgba()
        assert restored.thickness == original.thickness
        assert restored.filled == original.filled


class TestHighlightAdapter:
    def test_round_trip_preserves_rect_color_opacity(self):
        original = HighlightGraphicsItem(QRectF(5, 6, 70, 30), QColor(255, 255, 0), 90)
        original.setPos(QPointF(15, 25))

        record = capture_annotation(original)
        assert record.kind == "highlight"

        restored = restore_annotation(build_canvas_registry(), record)
        assert isinstance(restored, HighlightGraphicsItem)
        assert restored.pos() == original.pos()
        assert restored.rect == original.rect
        assert restored.color.rgba() == original.color.rgba()
        assert restored.opacity == original.opacity


class TestBlurPatchAdapter:
    def test_round_trip_preserves_patch_mode_strength_source_rect(self):
        patch = _solid_pixmap(24, 16, QColor(30, 30, 30), ratio=1.5)
        original = BlurPatchGraphicsItem(
            patch,
            QPointF(40, 55),
            "pixelate",
            9,
            source_rect=QRectF(40, 55, 24, 16),
        )

        record = capture_annotation(original)
        assert record.kind == "blur"
        assert record.patch is not None
        assert record.patch.width == 24
        assert record.patch.height == 16
        assert record.patch.device_pixel_ratio == 1.5

        restored = restore_annotation(build_canvas_registry(), record)
        assert isinstance(restored, BlurPatchGraphicsItem)
        assert restored.pos() == original.pos()
        assert restored.blur_mode == original.blur_mode
        assert restored.strength == original.strength
        assert restored.source_rect == original.source_rect
        assert restored.pixmap().devicePixelRatio() == patch.devicePixelRatio()

    def test_round_trip_with_missing_source_rect(self):
        patch = _solid_pixmap(10, 10, QColor(0, 0, 0))
        original = BlurPatchGraphicsItem(patch, QPointF(1, 2), "blur", 4, source_rect=None)

        record = capture_annotation(original)
        assert record.source_rect is None

        restored = restore_annotation(build_canvas_registry(), record)
        assert isinstance(restored, BlurPatchGraphicsItem)
        assert restored.source_rect is None


class TestPenAdapter:
    def test_round_trip_preserves_points_color_thickness(self):
        path = QPainterPath(QPointF(50, 50))
        path.lineTo(QPointF(90, 90))
        path.lineTo(QPointF(120, 60))
        original = PenStrokeGraphicsItem(path, QColor(0, 0, 255), 6)
        original.setPos(QPointF(10, 10))

        record = capture_annotation(original)
        assert record.kind == "pen"
        assert record.points[0] == (50.0, 50.0)
        assert record.points[2] == (120.0, 60.0)

        restored = restore_annotation(build_canvas_registry(), record)
        assert isinstance(restored, PenStrokeGraphicsItem)
        assert restored.pos() == original.pos()
        assert restored.path.elementCount() == original.path.elementCount()
        for index in range(original.path.elementCount()):
            original_element = original.path.elementAt(index)
            restored_element = restored.path.elementAt(index)
            assert (restored_element.x, restored_element.y) == (
                original_element.x,
                original_element.y,
            )
        assert QColor(restored.color).rgba() == QColor(original.color).rgba()
        assert restored.thickness == original.thickness


class TestCaptureFailures:
    def test_capture_rejects_unregistered_item_types(self, qapp):
        from PySide6.QtWidgets import QGraphicsEllipseItem

        ellipse = QGraphicsEllipseItem(0, 0, 10, 10)
        with pytest.raises(LookupError):
            capture_annotation(ellipse)

    def test_restore_rejects_unknown_kind(self):
        class UnknownRecord(AnnotationRecord):
            kind = "stamp"

        record = UnknownRecord(kind="stamp")
        with pytest.raises(LookupError):
            restore_annotation(build_canvas_registry(), record)

    def test_registry_supports_every_captured_family(self, qapp):
        registry = build_canvas_registry()
        items: list[object] = [
            ArrowGraphicsItem(QPointF(0, 0), QPointF(9, 9), QColor(255, 0, 0), 2),
            StepMarkerGraphicsItem(QPointF(0, 0), 1, QColor(255, 0, 0), 28),
            TextGraphicsItem("t", QPointF(0, 0), QColor(255, 0, 0), 12, False),
            RectangleGraphicsItem(QRectF(0, 0, 5, 5), QColor(255, 0, 0), 2, False),
            HighlightGraphicsItem(QRectF(0, 0, 5, 5), QColor(255, 255, 0), 100),
            BlurPatchGraphicsItem(_solid_pixmap(4, 4, QColor(0, 0, 0)), QPointF(0, 0), "blur", 3),
            PenStrokeGraphicsItem(QPainterPath(QPointF(0, 0)), QColor(255, 0, 0), 2),
        ]
        for item in items:
            record = capture_annotation(item)
            assert registry.supports(record.kind, record.version)
