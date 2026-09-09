"""Ordered in-memory screenshot inventory."""

from __future__ import annotations

from dataclasses import dataclass

from models.document_history import DocumentHistory, DocumentState, ImageValue


@dataclass(frozen=True)
class ScreenshotRecord:
    original: ImageValue
    current: DocumentState
    timestamp: float
    source: str
    history: DocumentHistory | None = None


class ScreenshotInventory:
    def __init__(self) -> None:
        self._records: list[ScreenshotRecord] = []
        self._current: int = -1

    def __len__(self) -> int:
        return len(self._records)

    @property
    def current_index(self) -> int:
        return self._current

    def add(self, record: ScreenshotRecord) -> int:
        self._records.append(record)
        self._current = len(self._records) - 1
        return self._current

    def get_current(self) -> ScreenshotRecord | None:
        if 0 <= self._current < len(self._records):
            return self._records[self._current]
        return None

    def get_at(self, index: int) -> ScreenshotRecord | None:
        if 0 <= index < len(self._records):
            return self._records[index]
        return None

    def update_current(self, state: DocumentState) -> bool:
        record = self.get_current()
        if record is None:
            return False
        self._records[self._current] = ScreenshotRecord(
            original=record.original,
            current=state,
            timestamp=record.timestamp,
            source=record.source,
            history=record.history,
        )
        return True

    def set_history(self, history: DocumentHistory | None) -> bool:
        record = self.get_current()
        if record is None:
            return False
        self._records[self._current] = ScreenshotRecord(
            original=record.original,
            current=record.current,
            timestamp=record.timestamp,
            source=record.source,
            history=history,
        )
        return True

    def remove_at(self, index: int) -> ScreenshotRecord | None:
        if not 0 <= index < len(self._records):
            return None
        removed = self._records.pop(index)
        if not self._records:
            self._current = -1
        elif index == self._current:
            self._current = min(index, len(self._records) - 1)
        elif index < self._current:
            self._current -= 1
        return removed

    def clear(self) -> None:
        self._records.clear()
        self._current = -1

    def can_go_next(self) -> bool:
        return 0 <= self._current < len(self._records) - 1

    def can_go_prev(self) -> bool:
        return self._current > 0 and len(self._records) > 0

    def next(self) -> ScreenshotRecord | None:
        if not self.can_go_next():
            return None
        self._current += 1
        return self._records[self._current]

    def prev(self) -> ScreenshotRecord | None:
        if not self.can_go_prev():
            return None
        self._current -= 1
        return self._records[self._current]

    def switch_to(self, index: int) -> ScreenshotRecord | None:
        if not 0 <= index < len(self._records):
            return None
        self._current = index
        return self._records[self._current]


__all__ = [
    "ScreenshotInventory",
    "ScreenshotRecord",
]
