from __future__ import annotations

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFrame, QScrollArea, QWidget

from app_dnd.ui.layout_rules import centered_origin, fit_size, minimum_size

FALLBACK_SCREEN = (1366, 768)


def available_geometry(widget: QWidget | None = None) -> tuple[int, int, int, int]:
    screen = None
    if widget is not None and hasattr(widget, "screen"):
        screen = widget.screen()
    screen = screen or QGuiApplication.primaryScreen()
    if screen is None:
        return 0, 0, *FALLBACK_SCREEN
    rect = screen.availableGeometry()
    return rect.x(), rect.y(), rect.width(), rect.height()


def fit_to_screen(widget: QWidget, width: int, height: int) -> tuple[int, int]:
    x, y, w, h = available_geometry(widget)
    size = fit_size((width, height), (w, h))
    widget.setMinimumSize(*minimum_size((w, h)))
    widget.resize(*size)
    return size


def center_on_screen(widget: QWidget, size: tuple[int, int]) -> None:
    widget.move(*centered_origin(available_geometry(widget), size))


def scrollable(widget: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.NoFrame)
    area.setWidget(widget)
    return area
