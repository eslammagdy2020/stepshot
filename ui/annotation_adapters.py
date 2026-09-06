"""Qt annotation adapters between the canvas scene and document records."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QImage, QPainterPath, QPixmap

from models.document_history import (
    AnnotationAdapter,
    AnnotationAdapterRegistry,
    ArrowRecord,
    BlurRecord,
    HighlightRecord,
    ImageFormat,
    ImageValue,
    PenRecord,
    RectangleRecord,
    RECORD_VERSION,
    StepRecord,
    TextRecord,
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


def qpixmap_to_image_value(pixmap: QPixmap) -> ImageValue:
    image = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    return ImageValue(
        pixels=bytes(image.constBits()),
        width=image.width(),
        height=image.height(),
        format=ImageFormat.RGBA8888,
        stride=image.bytesPerLine(),
        device_pixel_ratio=pixmap.devicePixelRatio(),
    )


def image_value_to_qpixmap(value: ImageValue) -> QPixmap:
    image = QImage(
        value.pixels,
        value.width,
        value.height,
        value.stride,
        QImage.Format.Format_RGBA8888,
    )
    premultiplied = image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    pixmap = QPixmap.fromImage(premultiplied)
    pixmap.setDevicePixelRatio(value.device_pixel_ratio)
    return pixmap


def qcolor_to_rgba(color: QColor) -> tuple[int, int, int, int]:
    return (color.red(), color.green(), color.blue(), color.alpha())


def rgba_to_qcolor(rgba: tuple[int, int, int, int]) -> QColor:
    return QColor(rgba[0], rgba[1], rgba[2], rgba[3])


def qpaintpath_to_points(path: QPainterPath) -> tuple[tuple[float, float], ...]:
    return tuple(
        (path.elementAt(index).x, path.elementAt(index).y)
        for index in range(path.elementCount())
    )


def points_to_qpaintpath(points: tuple[tuple[float, float], ...]) -> QPainterPath:
    path = QPainterPath(QPointF(points[0][0], points[0][1]))
    for x, y in points[1:]:
        path.lineTo(QPointF(x, y))
    return path


def _capture_arrow(item: ArrowGraphicsItem) -> ArrowRecord:
    return ArrowRecord(
        start=(item.start_point.x() + item.pos().x(), item.start_point.y() + item.pos().y()),
        end=(item.end_point.x() + item.pos().x(), item.end_point.y() + item.pos().y()),
        color_rgba=qcolor_to_rgba(QColor(item.color)),
        thickness=item.thickness,
    )


def _restore_arrow(record: ArrowRecord) -> ArrowGraphicsItem:
    return ArrowGraphicsItem(
        QPointF(record.start[0], record.start[1]),
        QPointF(record.end[0], record.end[1]),
        rgba_to_qcolor(record.color_rgba),
        record.thickness,
    )


def _capture_step(item: StepMarkerGraphicsItem) -> StepRecord:
    return StepRecord(
        position=(item.pos().x(), item.pos().y()),
        number=item.number,
        color_rgba=qcolor_to_rgba(QColor(item.marker_color)),
        size=item.marker_size,
    )


def _restore_step(record: StepRecord) -> StepMarkerGraphicsItem:
    return StepMarkerGraphicsItem(
        QPointF(record.position[0], record.position[1]),
        record.number,
        rgba_to_qcolor(record.color_rgba),
        record.size,
    )


def _capture_text(item: TextGraphicsItem) -> TextRecord:
    return TextRecord(
        position=(item.pos().x(), item.pos().y()),
        text=item.toPlainText(),
        color_rgba=qcolor_to_rgba(QColor(item.text_color)),
        font_size=item.font_size,
        bold=item.bold,
    )


def _restore_text(record: TextRecord) -> TextGraphicsItem:
    return TextGraphicsItem(
        record.text,
        QPointF(record.position[0], record.position[1]),
        rgba_to_qcolor(record.color_rgba),
        record.font_size,
        record.bold,
    )


def _capture_rectangle(item: RectangleGraphicsItem) -> RectangleRecord:
    return RectangleRecord(
        position=(item.pos().x(), item.pos().y()),
        rect=(item.rect.x(), item.rect.y(), item.rect.width(), item.rect.height()),
        color_rgba=qcolor_to_rgba(QColor(item.color)),
        thickness=item.thickness,
        filled=item.filled,
    )


def _restore_rectangle(record: RectangleRecord) -> RectangleGraphicsItem:
    item = RectangleGraphicsItem(
        QRectF(record.rect[0], record.rect[1], record.rect[2], record.rect[3]),
        rgba_to_qcolor(record.color_rgba),
        record.thickness,
        record.filled,
    )
    item.setPos(QPointF(record.position[0], record.position[1]))
    return item


def _capture_highlight(item: HighlightGraphicsItem) -> HighlightRecord:
    return HighlightRecord(
        position=(item.pos().x(), item.pos().y()),
        rect=(item.rect.x(), item.rect.y(), item.rect.width(), item.rect.height()),
        color_rgba=qcolor_to_rgba(QColor(item.color)),
        opacity=item.opacity,
    )


def _restore_highlight(record: HighlightRecord) -> HighlightGraphicsItem:
    item = HighlightGraphicsItem(
        QRectF(record.rect[0], record.rect[1], record.rect[2], record.rect[3]),
        rgba_to_qcolor(record.color_rgba),
        record.opacity,
    )
    item.setPos(QPointF(record.position[0], record.position[1]))
    return item


def _capture_blur(item: BlurPatchGraphicsItem) -> BlurRecord:
    return BlurRecord(
        position=(item.pos().x(), item.pos().y()),
        patch=qpixmap_to_image_value(item.pixmap()),
        mode=item.blur_mode,
        strength=item.strength,
        source_rect=(item.source_rect.x(), item.source_rect.y(), item.source_rect.width(), item.source_rect.height())
        if item.source_rect is not None
        else None,
    )


def _restore_blur(record: BlurRecord) -> BlurPatchGraphicsItem:
    patch = image_value_to_qpixmap(record.patch)
    item = BlurPatchGraphicsItem(
        patch,
        QPointF(0, 0),
        record.mode,
        record.strength,
        source_rect=QRectF(*record.source_rect) if record.source_rect is not None else None,
    )
    item.setPos(QPointF(record.position[0], record.position[1]))
    return item


def _capture_pen(item: PenStrokeGraphicsItem) -> PenRecord:
    return PenRecord(
        position=(item.pos().x(), item.pos().y()),
        points=qpaintpath_to_points(item.path),
        color_rgba=qcolor_to_rgba(QColor(item.color)),
        thickness=item.thickness,
    )


def _restore_pen(record: PenRecord) -> PenStrokeGraphicsItem:
    item = PenStrokeGraphicsItem(
        points_to_qpaintpath(record.points),
        rgba_to_qcolor(record.color_rgba),
        record.thickness,
    )
    item.setPos(QPointF(record.position[0], record.position[1]))
    return item


_ADAPTER_SPECS: tuple[tuple[type, AnnotationAdapter], ...] = (
    (ArrowGraphicsItem, AnnotationAdapter("arrow", (RECORD_VERSION,), _capture_arrow, _restore_arrow)),
    (StepMarkerGraphicsItem, AnnotationAdapter("step", (RECORD_VERSION,), _capture_step, _restore_step)),
    (TextGraphicsItem, AnnotationAdapter("text", (RECORD_VERSION,), _capture_text, _restore_text)),
    (RectangleGraphicsItem, AnnotationAdapter("rectangle", (RECORD_VERSION,), _capture_rectangle, _restore_rectangle)),
    (HighlightGraphicsItem, AnnotationAdapter("highlight", (RECORD_VERSION,), _capture_highlight, _restore_highlight)),
    (BlurPatchGraphicsItem, AnnotationAdapter("blur", (RECORD_VERSION,), _capture_blur, _restore_blur)),
    (PenStrokeGraphicsItem, AnnotationAdapter("pen", (RECORD_VERSION,), _capture_pen, _restore_pen)),
)


def build_canvas_registry() -> AnnotationAdapterRegistry:
    return AnnotationAdapterRegistry(adapter for _, adapter in _ADAPTER_SPECS)


def capturable_types() -> tuple[type, ...]:
    return tuple(item_type for item_type, _ in _ADAPTER_SPECS)


def capture_annotation(item: object) -> object:
    for item_type, adapter in _ADAPTER_SPECS:
        if isinstance(item, item_type):
            return adapter.capture(item)
    raise LookupError(f"no registered adapter captures {type(item).__name__}")


def restore_annotation(registry: AnnotationAdapterRegistry, record: object) -> object:
    if not hasattr(record, "kind"):
        raise LookupError(f"malformed annotation record: {record!r}")
    adapter = registry.adapter(record.kind)
    if adapter is None:
        raise LookupError(f"no registered adapter restores {record.kind!r}")
    return adapter.restore(record)
