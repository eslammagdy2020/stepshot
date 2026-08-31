"""Tests for the framework-neutral annotation document/history module."""

from __future__ import annotations

import pytest

from models.document_history import (
    AnnotationAdapter,
    AnnotationAdapterRegistry,
    AnnotationRecord,
    AcceptedMutation,
    ArrowRecord,
    BlurRecord,
    DocumentHistory,
    DocumentState,
    HighlightRecord,
    ImageFormat,
    ImageValue,
    PenRecord,
    RectangleRecord,
    RejectedMutation,
    StepRecord,
    TextRecord,
    build_default_registry,
    empty_document,
)


def _rgba_image(
    width: int = 4,
    height: int = 3,
    *,
    pixel: tuple[int, int, int, int] = (10, 20, 30, 255),
    device_pixel_ratio: float = 1.0,
) -> ImageValue:
    pixels = bytes(pixel) * (width * height)
    return ImageValue(
        pixels=pixels,
        width=width,
        height=height,
        format=ImageFormat.RGBA8888,
        stride=width * 4,
        device_pixel_ratio=device_pixel_ratio,
    )


def _stub_adapter(
    kind: str, supported_versions: tuple[int, ...] = (1,)
) -> AnnotationAdapter:
    def capture(_annotation: object) -> AnnotationRecord:
        raise NotImplementedError

    def restore(_record: AnnotationRecord) -> object:
        raise NotImplementedError

    return AnnotationAdapter(
        kind=kind,
        supported_versions=supported_versions,
        capture=capture,
        restore=restore,
    )


def _registry() -> AnnotationAdapterRegistry:
    return AnnotationAdapterRegistry(
        [
            _stub_adapter("arrow"),
            _stub_adapter("step"),
            _stub_adapter("text"),
            _stub_adapter("rectangle"),
            _stub_adapter("highlight"),
            _stub_adapter("blur"),
            _stub_adapter("pen"),
        ]
    )


def _state_with(*records: AnnotationRecord, step_counter: int = 1) -> DocumentState:
    return DocumentState(
        version=DocumentHistory.DOCUMENT_VERSION,
        image=_rgba_image(),
        annotations=tuple(records),
        step_counter=step_counter,
    )


class TestImageValue:
    def test_holds_owned_pixel_bytes(self):
        image = _rgba_image()
        assert image.pixels == bytes((10, 20, 30, 255)) * (4 * 3)
        assert image.width == 4
        assert image.height == 3
        assert image.format is ImageFormat.RGBA8888
        assert image.stride == 16
        assert image.device_pixel_ratio == 1.0

    def test_is_immutable(self):
        image = _rgba_image()
        with pytest.raises((AttributeError, TypeError)):
            image.pixels = b""  # type: ignore[misc]

    def test_strides_and_format_are_preserved_without_qt(self):
        image = _rgba_image(width=5, height=7, device_pixel_ratio=2.0)
        assert image.stride == 20
        assert image.device_pixel_ratio == 2.0
        assert image.format.value == "RGBA8888"


class TestAnnotationRecords:
    def test_arrow_record_is_immutable(self):
        record = ArrowRecord(
            start=(1.0, 2.0),
            end=(3.0, 4.0),
            color_rgba=(255, 0, 0, 255),
            thickness=3,
        )
        assert record.kind == "arrow"
        assert record.version == 1
        with pytest.raises((AttributeError, TypeError)):
            record.start = (0.0, 0.0)  # type: ignore[misc]

    def test_all_supported_records_carry_kind_and_version(self):
        image = _rgba_image()
        records: list[AnnotationRecord] = [
            ArrowRecord(start=(0.0, 0.0), end=(1.0, 1.0), color_rgba=(0, 0, 0, 255), thickness=1),
            StepRecord(position=(0.0, 0.0), number=1, color_rgba=(0, 0, 0, 255), size=28),
            TextRecord(position=(0.0, 0.0), text="hi", color_rgba=(0, 0, 0, 255), font_size=14, bold=False),
            RectangleRecord(position=(0.0, 0.0), rect=(0.0, 0.0, 10.0, 10.0), color_rgba=(0, 0, 0, 255), thickness=1, filled=False),
            HighlightRecord(position=(0.0, 0.0), rect=(0.0, 0.0, 10.0, 10.0), color_rgba=(255, 255, 0, 255), opacity=128),
            BlurRecord(position=(0.0, 0.0), patch=image, mode="blur", strength=8, source_rect=(0.0, 0.0, 4.0, 3.0)),
            PenRecord(position=(0.0, 0.0), points=((0.0, 0.0), (1.0, 1.0)), color_rgba=(0, 0, 0, 255), thickness=2),
        ]
        for record in records:
            assert isinstance(record, AnnotationRecord)
            assert record.version == 1
            assert record.kind


class TestDocumentStateEquality:
    def test_empty_documents_are_equal(self):
        assert empty_document() == empty_document()

    def test_state_equality_includes_image_pixels(self):
        a = _state_with()
        b = DocumentState(
            version=DocumentHistory.DOCUMENT_VERSION,
            image=_rgba_image(pixel=(200, 100, 50, 255)),
            annotations=(),
            step_counter=1,
        )
        assert a != b

    def test_state_equality_includes_annotation_order(self):
        arrow = ArrowRecord(start=(0.0, 0.0), end=(1.0, 1.0), color_rgba=(0, 0, 0, 255), thickness=1)
        rect = RectangleRecord(position=(0.0, 0.0), rect=(0.0, 0.0, 1.0, 1.0), color_rgba=(0, 0, 0, 255), thickness=1, filled=False)
        first = _state_with(arrow, rect)
        second = _state_with(rect, arrow)
        assert first != second

    def test_state_equality_includes_annotation_properties(self):
        a = _state_with(ArrowRecord(start=(0.0, 0.0), end=(1.0, 1.0), color_rgba=(0, 0, 0, 255), thickness=2))
        b = _state_with(ArrowRecord(start=(0.0, 0.0), end=(1.0, 1.0), color_rgba=(0, 0, 0, 255), thickness=3))
        assert a != b

    def test_state_equality_includes_step_counter(self):
        a = _state_with(step_counter=1)
        b = _state_with(step_counter=2)
        assert a != b

    def test_state_equality_includes_device_pixel_ratio(self):
        a = DocumentState(
            version=DocumentHistory.DOCUMENT_VERSION,
            image=_rgba_image(device_pixel_ratio=1.0),
            annotations=(),
            step_counter=1,
        )
        b = DocumentState(
            version=DocumentHistory.DOCUMENT_VERSION,
            image=_rgba_image(device_pixel_ratio=2.0),
            annotations=(),
            step_counter=1,
        )
        assert a != b


class TestDocumentHistoryBasics:
    def test_starts_with_empty_document(self):
        history = DocumentHistory(_registry())
        assert history.current == empty_document()
        assert history.can_undo is False
        assert history.can_redo is False

    def test_apply_accepts_new_state(self):
        history = DocumentHistory(_registry())
        arrow = ArrowRecord(start=(0.0, 0.0), end=(1.0, 1.0), color_rgba=(0, 0, 0, 255), thickness=1)
        result = history.apply(_state_with(arrow))
        assert isinstance(result, AcceptedMutation)
        assert history.current == _state_with(arrow)

    def test_apply_records_history(self):
        history = DocumentHistory(_registry())
        history.apply(_state_with())
        assert history.can_undo is True
        assert history.can_redo is False


class TestHistoryDirection:
    def test_undo_returns_previous_state(self):
        history = DocumentHistory(_registry())
        first = _state_with()
        second = _state_with(ArrowRecord(start=(0.0, 0.0), end=(1.0, 1.0), color_rgba=(0, 0, 0, 255), thickness=1))
        history.apply(first)
        history.apply(second)
        assert history.current == second
        restored = history.undo()
        assert restored == first
        assert history.current == first

    def test_redo_restores_undone_state(self):
        history = DocumentHistory(_registry())
        first = _state_with()
        second = _state_with(ArrowRecord(start=(0.0, 0.0), end=(1.0, 1.0), color_rgba=(0, 0, 0, 255), thickness=1))
        history.apply(first)
        history.apply(second)
        history.undo()
        redone = history.redo()
        assert redone == second
        assert history.current == second

    def test_undo_short_circuits_at_history_bottom(self):
        history = DocumentHistory(_registry())
        assert history.undo() is None
        assert history.current == empty_document()
        history.apply(_state_with())
        history.undo()
        assert history.current == empty_document()
        assert history.undo() is None
        assert history.current == empty_document()

    def test_redo_short_circuits_with_empty_redo_stack(self):
        history = DocumentHistory(_registry())
        assert history.redo() is None

    def test_new_mutation_invalidates_redo_stack(self):
        history = DocumentHistory(_registry())
        first = _state_with()
        second = _state_with(ArrowRecord(start=(0.0, 0.0), end=(1.0, 1.0), color_rgba=(0, 0, 0, 255), thickness=1))
        third = _state_with(StepRecord(position=(0.0, 0.0), number=1, color_rgba=(0, 0, 0, 255), size=28))
        history.apply(first)
        history.apply(second)
        history.undo()
        assert history.can_redo is True
        history.apply(third)
        assert history.can_redo is False


class TestHistoryCap:
    def test_undo_stack_is_capped_at_50_entries(self):
        history = DocumentHistory(_registry())
        for index in range(60):
            history.apply(_state_with(step_counter=index + 1))
        assert len(history.undo_stack) == 50


class TestRejectedMutations:
    def test_apply_with_unsupported_kind_is_rejected(self):
        registry = AnnotationAdapterRegistry([_stub_adapter("arrow")])
        history = DocumentHistory(registry)
        invalid = _state_with(
            StepRecord(position=(0.0, 0.0), number=1, color_rgba=(0, 0, 0, 255), size=28)
        )
        result = history.apply(invalid)
        assert isinstance(result, RejectedMutation)
        assert history.current == empty_document()
        assert history.can_undo is False

    def test_apply_with_unsupported_version_is_rejected(self):
        registry = AnnotationAdapterRegistry([_stub_adapter("arrow", supported_versions=(2,))])
        history = DocumentHistory(registry)
        invalid = _state_with(
            ArrowRecord(start=(0.0, 0.0), end=(1.0, 1.0), color_rgba=(0, 0, 0, 255), thickness=1)
        )
        result = history.apply(invalid)
        assert isinstance(result, RejectedMutation)
        assert history.current == empty_document()

    def test_rejected_mutation_does_not_grow_history(self):
        registry = AnnotationAdapterRegistry([_stub_adapter("arrow")])
        history = DocumentHistory(registry)
        history.apply(_state_with(ArrowRecord(start=(0.0, 0.0), end=(1.0, 1.0), color_rgba=(0, 0, 0, 255), thickness=1)))
        assert history.can_undo is True
        snapshot_count = len(history.undo_stack)
        result = history.apply(
            _state_with(StepRecord(position=(0.0, 0.0), number=1, color_rgba=(0, 0, 0, 255), size=28))
        )
        assert isinstance(result, RejectedMutation)
        assert len(history.undo_stack) == snapshot_count

    def test_rejected_mutation_does_not_invalidate_redo(self):
        arrow = ArrowRecord(start=(0.0, 0.0), end=(1.0, 1.0), color_rgba=(0, 0, 0, 255), thickness=1)
        history = DocumentHistory(_registry())
        history.apply(_state_with(arrow))
        history.apply(_state_with())
        history.undo()
        assert history.can_redo is True
        registry = AnnotationAdapterRegistry([_stub_adapter("arrow")])
        rejected = DocumentHistory(registry)
        rejected.apply(_state_with(arrow))
        rejected.apply(_state_with())
        rejected.undo()
        assert rejected.can_redo is True
        result = rejected.apply(
            _state_with(StepRecord(position=(0.0, 0.0), number=1, color_rgba=(0, 0, 0, 255), size=28))
        )
        assert isinstance(result, RejectedMutation)
        assert rejected.can_redo is True


class TestAtomicRestoration:
    def test_restore_accepts_valid_state(self):
        history = DocumentHistory(_registry())
        arrow = ArrowRecord(start=(0.0, 0.0), end=(1.0, 1.0), color_rgba=(0, 0, 0, 255), thickness=1)
        target = _state_with(arrow, step_counter=4)
        result = history.restore_snapshot(target)
        assert isinstance(result, AcceptedMutation)
        assert history.current == target

    def test_restore_rejects_unknown_kind(self):
        registry = AnnotationAdapterRegistry([_stub_adapter("arrow")])
        history = DocumentHistory(registry)
        mixed = _state_with(
            ArrowRecord(start=(0.0, 0.0), end=(1.0, 1.0), color_rgba=(0, 0, 0, 255), thickness=1),
            StepRecord(position=(0.0, 0.0), number=1, color_rgba=(0, 0, 0, 255), size=28),
        )
        result = history.restore_snapshot(mixed)
        assert isinstance(result, RejectedMutation)
        assert history.current == empty_document()

    def test_restore_rejects_unsupported_version(self):
        registry = AnnotationAdapterRegistry([_stub_adapter("arrow", supported_versions=(2,))])
        history = DocumentHistory(registry)
        result = history.restore_snapshot(
            _state_with(ArrowRecord(start=(0.0, 0.0), end=(1.0, 1.0), color_rgba=(0, 0, 0, 255), thickness=1))
        )
        assert isinstance(result, RejectedMutation)
        assert history.current == empty_document()

    def test_restore_leaves_state_unchanged_on_rejection(self):
        history = DocumentHistory(_registry())
        arrow = ArrowRecord(start=(0.0, 0.0), end=(1.0, 1.0), color_rgba=(0, 0, 0, 255), thickness=1)
        history.apply(_state_with(arrow))
        snapshot_undo_count = len(history.undo_stack)
        registry = AnnotationAdapterRegistry([_stub_adapter("arrow")])
        reject_history = DocumentHistory(registry)
        reject_history.apply(_state_with(ArrowRecord(start=(0.0, 0.0), end=(1.0, 1.0), color_rgba=(0, 0, 0, 255), thickness=1)))
        snapshot_before = reject_history.current
        result = reject_history.restore_snapshot(
            _state_with(StepRecord(position=(0.0, 0.0), number=1, color_rgba=(0, 0, 0, 255), size=28))
        )
        assert isinstance(result, RejectedMutation)
        assert reject_history.current == snapshot_before

    def test_restore_records_previous_state_for_undo(self):
        history = DocumentHistory(_registry())
        history.apply(_state_with())
        arrow = ArrowRecord(start=(0.0, 0.0), end=(1.0, 1.0), color_rgba=(0, 0, 0, 255), thickness=1)
        target = _state_with(arrow)
        history.restore_snapshot(target)
        assert history.undo() == _state_with()


class TestMixedDocuments:
    def test_round_trip_through_apply_undo_redo_preserves_mixed_state(self):
        history = DocumentHistory(_registry())
        image_a = _rgba_image(pixel=(10, 20, 30, 255))
        image_b = _rgba_image(pixel=(200, 150, 100, 255))
        arrow = ArrowRecord(start=(1.0, 2.0), end=(3.0, 4.0), color_rgba=(255, 0, 0, 255), thickness=4)
        text = TextRecord(position=(5.0, 5.0), text="hi", color_rgba=(0, 0, 0, 255), font_size=14, bold=True)
        rect = RectangleRecord(position=(0.0, 0.0), rect=(0.0, 0.0, 50.0, 50.0), color_rgba=(0, 255, 0, 255), thickness=2, filled=True)
        highlight = HighlightRecord(position=(0.0, 0.0), rect=(60.0, 60.0, 40.0, 20.0), color_rgba=(255, 255, 0, 255), opacity=128)
        pen = PenRecord(position=(0.0, 0.0), points=((0.0, 0.0), (5.0, 5.0), (10.0, 0.0)), color_rgba=(0, 0, 255, 255), thickness=3)
        blur = BlurRecord(position=(0.0, 0.0), patch=_rgba_image(), mode="pixelate", strength=8, source_rect=(0.0, 0.0, 4.0, 3.0))
        step = StepRecord(position=(100.0, 100.0), number=3, color_rgba=(0, 0, 0, 255), size=28)

        first = DocumentState(
            version=DocumentHistory.DOCUMENT_VERSION,
            image=image_a,
            annotations=(arrow, text, step),
            step_counter=4,
        )
        second = DocumentState(
            version=DocumentHistory.DOCUMENT_VERSION,
            image=image_b,
            annotations=(rect, highlight, pen, blur),
            step_counter=4,
        )
        history.apply(first)
        history.apply(second)
        assert history.current == second
        assert history.undo() == first
        assert history.redo() == second


class TestDefaultRegistry:
    def test_supports_all_currently_supported_kinds(self):
        registry = build_default_registry()
        for kind in ("arrow", "step", "text", "rectangle", "highlight", "blur", "pen"):
            assert registry.supports(kind, 1), f"missing {kind}"

    def test_does_not_support_unknown_kinds(self):
        registry = build_default_registry()
        assert registry.supports("stamp", 1) is False

    def test_does_not_support_unknown_versions(self):
        registry = build_default_registry()
        assert registry.supports("arrow", 99) is False