"""Tests for the screenshot inventory model."""

from __future__ import annotations

from models.document_history import (
    DocumentHistory,
    DocumentState,
    ImageFormat,
    ImageValue,
)
from models.screenshot_inventory import ScreenshotInventory, ScreenshotRecord


def _image(seed: int = 1) -> ImageValue:
    pixels = bytes([seed % 256]) * (8 * 4 * 2)
    return ImageValue(
        pixels=pixels,
        width=8,
        height=2,
        format=ImageFormat.RGBA8888,
        stride=8 * 4,
    )


def _state(image: ImageValue, step: int = 1) -> DocumentState:
    return DocumentState(
        version=DocumentHistory.DOCUMENT_VERSION,
        image=image,
        annotations=(),
        step_counter=step,
    )


def _record(seed: int = 1, source: str = "region") -> ScreenshotRecord:
    img = _image(seed)
    return ScreenshotRecord(
        original=img, current=_state(img), timestamp=float(seed), source=source
    )


class TestScreenshotInventoryEmpty:
    def test_empty_state(self):
        """Empty inventory has no current and no navigation."""
        inv = ScreenshotInventory()
        assert len(inv) == 0
        assert inv.get_current() is None
        assert inv.current_index == -1
        assert inv.can_go_next() is False
        assert inv.can_go_prev() is False
        assert inv.next() is None
        assert inv.prev() is None

    def test_remove_from_empty_returns_none(self):
        """Removing from empty inventory is a no-op."""
        inv = ScreenshotInventory()
        assert inv.remove_at(0) is None

    def test_switch_in_empty_returns_none(self):
        """Switching in empty inventory is a no-op."""
        inv = ScreenshotInventory()
        assert inv.switch_to(0) is None


class TestScreenshotInventoryAdd:
    def test_add_sets_current(self):
        """Adding records makes the newest current."""
        inv = ScreenshotInventory()
        inv.add(_record(1))
        assert len(inv) == 1
        assert inv.current_index == 0
        inv.add(_record(2))
        assert len(inv) == 2
        assert inv.current_index == 1
        assert inv.get_current() is not None
        assert inv.get_current().timestamp == 2.0

    def test_add_returns_index(self):
        """Add returns the new current index."""
        inv = ScreenshotInventory()
        assert inv.add(_record(1)) == 0
        assert inv.add(_record(2)) == 1


class TestScreenshotInventoryNavigation:
    def test_next_prev_cycle(self):
        """Next/prev move the active index within bounds."""
        inv = ScreenshotInventory()
        inv.add(_record(1))
        inv.add(_record(2))
        inv.add(_record(3))
        assert inv.current_index == 2
        assert inv.can_go_prev() is True
        assert inv.can_go_next() is False
        inv.prev()
        assert inv.current_index == 1
        assert inv.can_go_next() is True
        inv.prev()
        assert inv.current_index == 0
        assert inv.can_go_prev() is False
        assert inv.prev() is None
        inv.next()
        assert inv.current_index == 1

    def test_switch_to_bounds(self):
        """Switch rejects out-of-range indexes."""
        inv = ScreenshotInventory()
        inv.add(_record(1))
        inv.add(_record(2))
        assert inv.switch_to(0) is not None
        assert inv.current_index == 0
        assert inv.switch_to(5) is None
        assert inv.switch_to(-1) is None
        assert inv.current_index == 0


class TestScreenshotInventoryRemove:
    def test_remove_current_selects_neighbor(self):
        """Removing current selects the neighbor at the same index."""
        inv = ScreenshotInventory()
        inv.add(_record(1))
        inv.add(_record(2))
        inv.add(_record(3))
        inv.switch_to(1)
        removed = inv.remove_at(1)
        assert removed is not None
        assert removed.timestamp == 2.0
        assert len(inv) == 2
        assert inv.current_index == 1
        assert inv.get_current().timestamp == 3.0

    def test_remove_last_empties(self):
        """Removing the last record empties the inventory."""
        inv = ScreenshotInventory()
        inv.add(_record(1))
        inv.remove_at(0)
        assert len(inv) == 0
        assert inv.current_index == -1
        assert inv.get_current() is None

    def test_remove_before_current_shifts_index(self):
        """Removing before current decrements the index."""
        inv = ScreenshotInventory()
        inv.add(_record(1))
        inv.add(_record(2))
        inv.add(_record(3))
        assert inv.current_index == 2
        inv.remove_at(0)
        assert inv.current_index == 1
        assert inv.get_current().timestamp == 3.0

    def test_clear(self):
        """Clear empties the inventory."""
        inv = ScreenshotInventory()
        inv.add(_record(1))
        inv.add(_record(2))
        inv.clear()
        assert len(inv) == 0
        assert inv.current_index == -1


class TestScreenshotInventoryUpdate:
    def test_update_current_replaces_state(self):
        """Updating current replaces the document state only."""
        inv = ScreenshotInventory()
        inv.add(_record(1))
        img = _image(1)
        new_state = _state(img, step=5)
        assert inv.update_current(new_state) is True
        assert inv.get_current().current.step_counter == 5
        assert inv.get_current().original == img

    def test_update_empty_returns_false(self):
        """Updating empty inventory fails."""
        inv = ScreenshotInventory()
        assert inv.update_current(_state(_image())) is False
