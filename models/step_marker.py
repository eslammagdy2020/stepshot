"""Step marker numbering state."""

from __future__ import annotations


class StepCounter:
    def __init__(self, start: int = 1) -> None:
        self._next = start

    @property
    def next_number(self) -> int:
        value = self._next
        self._next += 1
        return value

    @property
    def current(self) -> int:
        return self._next

    def reset(self, start: int = 1) -> None:
        self._next = start

    def reset_to(self, value: int) -> None:
        self._next = value
