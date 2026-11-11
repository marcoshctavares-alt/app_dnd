from __future__ import annotations

WIDE_LAYOUT_MIN_WIDTH = 980
SMALL_SCREEN_WIDTH = 1200
SCREEN_FRACTION = 0.9
MIN_WINDOW = (640, 480)


def fit_size(desired: tuple[int, int], available: tuple[int, int], fraction: float = SCREEN_FRACTION) -> tuple[int, int]:
    width = min(desired[0], int(available[0] * fraction))
    height = min(desired[1], int(available[1] * fraction))
    return max(1, width), max(1, height)


def minimum_size(available: tuple[int, int], fraction: float = SCREEN_FRACTION) -> tuple[int, int]:
    return fit_size(MIN_WINDOW, available, fraction)


def list_panel_width(window_width: int) -> int:
    return max(180, min(320, int(window_width * 0.2)))


def use_wide_layout(width: int) -> bool:
    return width >= WIDE_LAYOUT_MIN_WIDTH


def dice_dock_at_bottom(available_width: int) -> bool:
    return available_width < SMALL_SCREEN_WIDTH


def centered_origin(available: tuple[int, int, int, int], size: tuple[int, int]) -> tuple[int, int]:
    x, y, w, h = available
    return x + max(0, (w - size[0]) // 2), y + max(0, (h - size[1]) // 2)
