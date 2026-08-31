"""Image effect helpers using Pillow."""

from __future__ import annotations

from enum import Enum

from PIL import Image, ImageFilter
from PySide6.QtCore import QRect
from PySide6.QtGui import QImage, QPixmap


class BlurMode(Enum):
    BLUR = "blur"
    PIXELATE = "pixelate"


def qpixmap_to_pil(pixmap: QPixmap) -> Image.Image:
    image = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    return Image.frombytes(
        "RGBA",
        (image.width(), image.height()),
        bytes(image.constBits()),
        "raw",
        "RGBA",
        image.bytesPerLine(),
    )


def pil_to_qpixmap(image: Image.Image, device_pixel_ratio: float = 1.0) -> QPixmap:
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    data = image.tobytes("raw", "RGBA")
    qimage = QImage(data, image.width, image.height, QImage.Format.Format_RGBA8888)
    pixmap = QPixmap.fromImage(qimage.copy())
    pixmap.setDevicePixelRatio(device_pixel_ratio)
    return pixmap


def apply_region_effect(
    source: QPixmap,
    rect: QRect,
    mode: BlurMode,
    pixelate_size: int = 12,
    blur_radius: int = 12,
    device_pixel_ratio: float = 1.0,
) -> QPixmap:
    if rect.width() <= 0 or rect.height() <= 0:
        raise ValueError("Effect region must have positive width and height.")

    bounded = QRect(
        max(0, rect.x()),
        max(0, rect.y()),
        min(rect.width(), source.width() - max(0, rect.x())),
        min(rect.height(), source.height() - max(0, rect.y())),
    )
    if bounded.width() <= 0 or bounded.height() <= 0:
        raise ValueError("Effect region is outside the image bounds.")

    region = source.copy(bounded)
    image = qpixmap_to_pil(region)

    if mode == BlurMode.BLUR:
        image = image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    else:
        small_w = max(1, bounded.width() // max(2, pixelate_size))
        small_h = max(1, bounded.height() // max(2, pixelate_size))
        image = image.resize((small_w, small_h), Image.Resampling.NEAREST)
        image = image.resize((bounded.width(), bounded.height()), Image.Resampling.NEAREST)

    return pil_to_qpixmap(image, device_pixel_ratio=device_pixel_ratio)
