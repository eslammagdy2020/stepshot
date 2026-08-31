"""Image export helpers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtGui import QPixmap


class ExportService:
    @staticmethod
    def default_save_directory() -> Path:
        pictures = Path.home() / "Pictures"
        if pictures.is_dir():
            return pictures
        return Path.home()

    @staticmethod
    def generate_filename(
        directory: Path | None = None,
        extension: str = "png",
    ) -> str:
        target_dir = directory or ExportService.default_save_directory()
        date_str = datetime.now().strftime("%d%m%y")
        prefix = f"stepshot{date_str}"
        extension = extension.lstrip(".").lower()

        numbers: list[int] = []
        for path in target_dir.glob(f"{prefix}*.{extension}"):
            suffix = path.stem.removeprefix(prefix)
            if suffix.isdigit():
                numbers.append(int(suffix))

        next_number = (max(numbers) if numbers else 0) + 1
        return f"{prefix}{next_number:03d}.{extension}"

    @staticmethod
    def save_png(pixmap: QPixmap, path: str | Path) -> None:
        target = Path(path)
        if not pixmap.save(str(target), "PNG"):
            raise RuntimeError(f"Failed to save PNG to {target}")

    @staticmethod
    def save_jpg(pixmap: QPixmap, path: str | Path, quality: int = 90) -> None:
        target = Path(path)
        if not pixmap.save(str(target), "JPG", quality):
            raise RuntimeError(f"Failed to save JPG to {target}")
