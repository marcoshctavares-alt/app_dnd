import pytest

from app_dnd.ui.layout_rules import (
    centered_origin,
    dice_dock_at_bottom,
    fit_size,
    list_panel_width,
    minimum_size,
    use_wide_layout,
)

SCREENS = [(800, 600), (1280, 720), (1366, 768), (1920, 1080), (2560, 1440), (3840, 2160)]


@pytest.mark.parametrize("screen", SCREENS)
def test_window_never_exceeds_screen(screen):
    width, height = fit_size((1280, 820), screen)
    assert width <= screen[0] and height <= screen[1]
    assert width <= screen[0] * 0.9 and height <= screen[1] * 0.9
    min_w, min_h = minimum_size(screen)
    assert min_w <= width and min_h <= height


def test_large_screens_keep_the_desired_size():
    assert fit_size((1280, 820), (3840, 2160)) == (1280, 820)


def test_small_screens_shrink_the_window():
    assert fit_size((1280, 820), (1280, 720)) == (1152, 648)
    assert fit_size((560, 620), (800, 600)) == (560, 540)


def test_minimum_size_is_clamped_on_tiny_screens():
    assert minimum_size((640, 400)) == (576, 360)


def test_list_panel_width_is_bounded():
    assert list_panel_width(600) == 180
    assert list_panel_width(1280) == 256
    assert list_panel_width(4000) == 320


def test_wide_layout_threshold():
    assert not use_wide_layout(700) and not use_wide_layout(979)
    assert use_wide_layout(980) and use_wide_layout(1900)


def test_dice_dock_goes_to_bottom_on_narrow_screens():
    assert dice_dock_at_bottom(1024) and dice_dock_at_bottom(1199)
    assert not dice_dock_at_bottom(1200) and not dice_dock_at_bottom(1920)


def test_centered_origin_respects_the_screen_offset():
    assert centered_origin((0, 0, 1920, 1080), (1280, 820)) == (320, 130)
    assert centered_origin((1920, 0, 1366, 768), (1229, 691)) == (1920 + 68, 38)
    assert centered_origin((0, 0, 800, 600), (900, 700)) == (0, 0)
