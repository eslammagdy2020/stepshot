"""Framework-neutral annotation document and history."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Iterable


class ImageFormat(str, Enum):
    RGBA8888 = "RGBA8888"


RECORD_VERSION: int = 1

SUPPORTED_ANNOTATION_KINDS: tuple[str, ...] = (
    "arrow",
    "step",
    "text",
    "rectangle",
    "highlight",
    "blur",
    "pen",
)


@dataclass(frozen=True)
class ImageValue:
    pixels: bytes
    width: int
    height: int
    format: ImageFormat
    stride: int
    device_pixel_ratio: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "pixels", bytes(self.pixels))
        if self.width <= 0 or self.height <= 0 or self.stride < 0:
            raise ValueError("image dimensions must be positive and stride non-negative")
        if self.stride < self.width * 4:
            raise ValueError("image stride is too small for RGBA8888 pixels")
        if len(self.pixels) < self.stride * self.height:
            raise ValueError("image pixels do not cover the image stride")
        if self.device_pixel_ratio <= 0:
            raise ValueError("device pixel ratio must be positive")


@dataclass(frozen=True)
class AnnotationRecord:
    kind: str
    version: int = RECORD_VERSION


@dataclass(frozen=True)
class ArrowRecord(AnnotationRecord):
    kind: str = "arrow"
    version: int = RECORD_VERSION
    start: tuple[float, float] = (0.0, 0.0)
    end: tuple[float, float] = (0.0, 0.0)
    color_rgba: tuple[int, int, int, int] = (0, 0, 0, 255)
    thickness: int = 1


@dataclass(frozen=True)
class StepRecord(AnnotationRecord):
    kind: str = "step"
    version: int = RECORD_VERSION
    position: tuple[float, float] = (0.0, 0.0)
    number: int = 1
    color_rgba: tuple[int, int, int, int] = (0, 0, 0, 255)
    size: int = 28


@dataclass(frozen=True)
class TextRecord(AnnotationRecord):
    kind: str = "text"
    version: int = RECORD_VERSION
    position: tuple[float, float] = (0.0, 0.0)
    text: str = ""
    color_rgba: tuple[int, int, int, int] = (0, 0, 0, 255)
    font_size: int = 14
    bold: bool = False


@dataclass(frozen=True)
class RectangleRecord(AnnotationRecord):
    kind: str = "rectangle"
    version: int = RECORD_VERSION
    position: tuple[float, float] = (0.0, 0.0)
    rect: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    color_rgba: tuple[int, int, int, int] = (0, 0, 0, 255)
    thickness: int = 1
    filled: bool = False


@dataclass(frozen=True)
class HighlightRecord(AnnotationRecord):
    kind: str = "highlight"
    version: int = RECORD_VERSION
    position: tuple[float, float] = (0.0, 0.0)
    rect: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    color_rgba: tuple[int, int, int, int] = (255, 255, 0, 255)
    opacity: int = 128


@dataclass(frozen=True)
class BlurRecord(AnnotationRecord):
    kind: str = "blur"
    version: int = RECORD_VERSION
    position: tuple[float, float] = (0.0, 0.0)
    patch: ImageValue | None = None
    mode: str = "blur"
    strength: int = 0
    source_rect: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class PenRecord(AnnotationRecord):
    kind: str = "pen"
    version: int = RECORD_VERSION
    position: tuple[float, float] = (0.0, 0.0)
    points: tuple[tuple[float, float], ...] = ()
    color_rgba: tuple[int, int, int, int] = (0, 0, 0, 255)
    thickness: int = 1


@dataclass(frozen=True)
class DocumentState:
    version: int
    image: ImageValue | None
    annotations: tuple[AnnotationRecord, ...] = ()
    step_counter: int = 1


def empty_document() -> DocumentState:
    return DocumentState(version=DocumentHistory.DOCUMENT_VERSION, image=None)


@dataclass(frozen=True)
class AcceptedMutation:
    state: DocumentState


@dataclass(frozen=True)
class RejectedMutation:
    reason: str


MutationResult = AcceptedMutation | RejectedMutation


@dataclass(frozen=True)
class AnnotationAdapter:
    kind: str
    supported_versions: tuple[int, ...]
    capture: Callable[[object], AnnotationRecord]
    restore: Callable[[AnnotationRecord], object]


class AnnotationAdapterRegistry:
    def __init__(self, adapters: Iterable[AnnotationAdapter]) -> None:
        self._adapters: dict[str, AnnotationAdapter] = {
            adapter.kind: adapter for adapter in adapters
        }

    def supports(self, kind: str, version: int) -> bool:
        adapter = self._adapters.get(kind)
        if adapter is None:
            return False
        return version in adapter.supported_versions

    def adapter(self, kind: str) -> AnnotationAdapter | None:
        return self._adapters.get(kind)


def _placeholder_capture(_annotation: object) -> AnnotationRecord:
    raise NotImplementedError(
        "Annotation capture is provided by the canvas adapter, not the document/history module."
    )


def _placeholder_restore(_record: AnnotationRecord) -> object:
    raise NotImplementedError(
        "Annotation restoration is provided by the canvas adapter, not the document/history module."
    )


def _stub_adapter(kind: str) -> AnnotationAdapter:
    return AnnotationAdapter(
        kind=kind,
        supported_versions=(RECORD_VERSION,),
        capture=_placeholder_capture,
        restore=_placeholder_restore,
    )


def build_default_registry() -> AnnotationAdapterRegistry:
    return AnnotationAdapterRegistry(
        [_stub_adapter(kind) for kind in SUPPORTED_ANNOTATION_KINDS]
    )


def _validate_document(
    document: DocumentState,
    registry: AnnotationAdapterRegistry,
) -> str | None:
    if document.version != DocumentHistory.DOCUMENT_VERSION:
        return f"unsupported document version: {document.version}"
    if document.image is not None:
        if document.image.format is not ImageFormat.RGBA8888:
            return f"unsupported image format: {document.image.format}"
    for record in document.annotations:
        if not isinstance(record, AnnotationRecord):
            return f"malformed annotation record: {record!r}"
        if not registry.supports(record.kind, record.version):
            return f"unsupported annotation kind or version: {record.kind} v{record.version}"
        if record.kind == "blur":
            if record.patch is None:
                return "blur record missing patch"
        if record.kind == "pen":
            if not record.points:
                return "pen record has no points"
    return None


class DocumentHistory:
    DOCUMENT_VERSION: int = 1
    HISTORY_CAP: int = 50

    def __init__(
        self,
        registry: AnnotationAdapterRegistry,
        initial_state: DocumentState | None = None,
    ) -> None:
        self._registry = registry
        seed = initial_state if initial_state is not None else empty_document()
        rejection = _validate_document(seed, registry)
        if rejection is not None:
            raise ValueError(f"invalid initial document state: {rejection}")
        self._current: DocumentState = seed
        self._history: list[DocumentState] = [seed]
        self._cursor: int = 0

    @property
    def current(self) -> DocumentState:
        return self._current

    @property
    def can_undo(self) -> bool:
        return self._cursor > 0

    @property
    def can_redo(self) -> bool:
        return self._cursor < len(self._history) - 1

    @property
    def undo_stack(self) -> tuple[DocumentState, ...]:
        return tuple(self._history[: self._cursor])

    @property
    def redo_stack(self) -> tuple[DocumentState, ...]:
        return tuple(self._history[self._cursor + 1 :])

    def apply(self, new_state: DocumentState) -> MutationResult:
        rejection = _validate_document(new_state, self._registry)
        if rejection is not None:
            return RejectedMutation(reason=rejection)
        if new_state == self._current and self._cursor == len(self._history) - 1:
            return AcceptedMutation(state=self._current)
        del self._history[self._cursor + 1 :]
        self._history.append(new_state)
        while len(self._history) > self.HISTORY_CAP + 1:
            del self._history[:1]
            self._cursor -= 1
        self._cursor = len(self._history) - 1
        self._current = new_state
        return AcceptedMutation(state=new_state)

    def restore_snapshot(self, snapshot: DocumentState) -> MutationResult:
        return self.apply(snapshot)

    def undo(self) -> DocumentState | None:
        if self._cursor <= 0:
            return None
        self._cursor -= 1
        self._current = self._history[self._cursor]
        return self._current

    def redo(self) -> DocumentState | None:
        if self._cursor >= len(self._history) - 1:
            return None
        self._cursor += 1
        self._current = self._history[self._cursor]
        return self._current


__all__ = [
    "AcceptedMutation",
    "AnnotationAdapter",
    "AnnotationAdapterRegistry",
    "AnnotationRecord",
    "ArrowRecord",
    "BlurRecord",
    "DocumentHistory",
    "DocumentState",
    "HighlightRecord",
    "ImageFormat",
    "ImageValue",
    "MutationResult",
    "PenRecord",
    "RectangleRecord",
    "RECORD_VERSION",
    "RejectedMutation",
    "StepRecord",
    "TextRecord",
    "SUPPORTED_ANNOTATION_KINDS",
    "build_default_registry",
    "empty_document",
]