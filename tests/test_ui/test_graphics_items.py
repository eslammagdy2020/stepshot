"""Tests for custom graphics items."""

from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor

from ui.graphics_items import ArrowGraphicsItem, StepMarkerGraphicsItem, TextGraphicsItem


class TestArrowGraphicsItem:
    def test_default_color_is_red(self):
        arrow = ArrowGraphicsItem(QPointF(0, 0), QPointF(100, 0))
        assert arrow.color.red() == 255
        assert arrow.color.green() == 0
        assert arrow.color.blue() == 0

    def test_default_thickness(self):
        arrow = ArrowGraphicsItem(QPointF(0, 0), QPointF(50, 50))
        assert arrow.thickness == 3

    def test_set_color_updates_item(self):
        arrow = ArrowGraphicsItem(QPointF(0, 0), QPointF(50, 50))
        arrow.set_color(QColor(0, 128, 255))
        assert arrow.color.blue() == 255

    def test_set_thickness_updates_item(self):
        arrow = ArrowGraphicsItem(QPointF(0, 0), QPointF(50, 50))
        arrow.set_thickness(8)
        assert arrow.thickness == 8

    def test_bounding_rect_covers_line(self):
        arrow = ArrowGraphicsItem(QPointF(10, 10), QPointF(110, 60))
        rect = arrow.boundingRect()
        assert rect.contains(QPointF(10, 10))
        assert rect.contains(QPointF(110, 60))

    def test_is_selectable_and_movable(self):
        from PySide6.QtWidgets import QGraphicsItem

        arrow = ArrowGraphicsItem(QPointF(0, 0), QPointF(10, 10))
        flags = arrow.flags()
        assert flags & QGraphicsItem.ItemIsSelectable
        assert flags & QGraphicsItem.ItemIsMovable


class TestStepMarkerGraphicsItem:
    def test_displays_number(self):
        marker = StepMarkerGraphicsItem(QPointF(0, 0), number=7)
        assert marker.number == 7
        assert marker.label.toPlainText() == "7"

    def test_default_size(self):
        marker = StepMarkerGraphicsItem(QPointF(0, 0), number=1)
        assert marker.marker_size == 28

    def test_set_color(self):
        marker = StepMarkerGraphicsItem(QPointF(0, 0), number=1)
        marker.set_color(QColor(0, 200, 0))
        assert marker.marker_color.green() == 200

    def test_set_size(self):
        marker = StepMarkerGraphicsItem(QPointF(0, 0), number=1, size=28)
        marker.set_size(40)
        assert marker.marker_size == 40


class TestTextGraphicsItem:
    def test_stores_text_and_style(self):
        item = TextGraphicsItem(
            "Click here",
            QPointF(20, 30),
            color=QColor(255, 0, 0),
            font_size=16,
            bold=True,
        )
        assert item.toPlainText() == "Click here"
        assert item.font_size == 16
        assert item.bold is True

    def test_multiline_text(self):
        content = "Click here\nError appears after saving"
        item = TextGraphicsItem(content, QPointF(0, 0))
        assert item.toPlainText() == content

    def test_set_font_size(self):
        item = TextGraphicsItem("Note", QPointF(0, 0), font_size=14)
        item.set_font_size(22)
        assert item.font_size == 22

    def test_set_bold(self):
        item = TextGraphicsItem("Note", QPointF(0, 0), bold=False)
        item.set_bold(True)
        assert item.bold is True

    def test_dark_text_gets_light_backdrop(self):
        item = TextGraphicsItem("x", QPointF(0, 0), QColor(0, 0, 0))
        backdrop = item._backdrop_color()
        assert backdrop.red() > 200
        assert backdrop.alpha() > 0

    def test_light_text_gets_dark_backdrop(self):
        item = TextGraphicsItem("x", QPointF(0, 0), QColor(255, 255, 255))
        backdrop = item._backdrop_color()
        assert backdrop.red() < 100
        assert backdrop.alpha() > 0

    def test_bounding_rect_has_backdrop_margin(self):
        item = TextGraphicsItem("Note", QPointF(0, 0), font_size=14)
        assert item.boundingRect().width() > item.document().size().width()
