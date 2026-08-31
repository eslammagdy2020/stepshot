"""Tests for step marker numbering."""

from __future__ import annotations

from models.step_marker import StepCounter


class TestStepCounter:
    def test_auto_increment(self):
        counter = StepCounter()
        assert counter.next_number == 1
        assert counter.next_number == 2
        assert counter.next_number == 3
        assert counter.next_number == 4

    def test_reset_to_default(self):
        counter = StepCounter()
        counter.next_number
        counter.next_number
        counter.reset()
        assert counter.next_number == 1

    def test_reset_to_custom_start(self):
        counter = StepCounter(start=10)
        assert counter.next_number == 10
        counter.reset(start=5)
        assert counter.next_number == 5
