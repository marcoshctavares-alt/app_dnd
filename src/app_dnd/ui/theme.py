from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

SETTINGS_KEY = "ui/theme"
SYSTEM, LIGHT, DARK = "sistema", "claro", "escuro"
MODES = ((SYSTEM, "Padrão do sistema"), (LIGHT, "Claro"), (DARK, "Escuro"))
ERROR_COLOR = "#e5484d"

_default_look: tuple[str, QPalette] | None = None

LIGHT_COLORS = {
    "Window": "#f0f0f0", "WindowText": "#202020", "Base": "#ffffff", "AlternateBase": "#f5f5f5",
    "Text": "#202020", "Button": "#e8e8e8", "ButtonText": "#202020", "ToolTipBase": "#ffffdc",
    "ToolTipText": "#202020", "Highlight": "#2f6fd6", "HighlightedText": "#ffffff",
    "Link": "#1a5fb4", "PlaceholderText": "#767676", "BrightText": "#ffffff",
}
DARK_COLORS = {
    "Window": "#2b2b2b", "WindowText": "#e6e6e6", "Base": "#1f1f1f", "AlternateBase": "#292929",
    "Text": "#e6e6e6", "Button": "#3a3a3a", "ButtonText": "#e6e6e6", "ToolTipBase": "#3a3a3a",
    "ToolTipText": "#e6e6e6", "Highlight": "#4a8ff0", "HighlightedText": "#101010",
    "Link": "#7ab2ff", "PlaceholderText": "#9a9a9a", "BrightText": "#ffffff",
}
DISABLED_DARK = {"WindowText": "#7a7a7a", "Text": "#7a7a7a", "ButtonText": "#7a7a7a"}
DISABLED_LIGHT = {"WindowText": "#9a9a9a", "Text": "#9a9a9a", "ButtonText": "#9a9a9a"}


def palette_colors(mode: str) -> tuple[dict[str, str], dict[str, str]] | None:
    if mode == DARK:
        return DARK_COLORS, DISABLED_DARK
    if mode == LIGHT:
        return LIGHT_COLORS, DISABLED_LIGHT
    return None


def normalize(mode: object) -> str:
    return mode if mode in (SYSTEM, LIGHT, DARK) else SYSTEM


def saved_mode() -> str:
    return normalize(QSettings("APP_DND", "APP_DND").value(SETTINGS_KEY, SYSTEM))


def save_mode(mode: str) -> None:
    QSettings("APP_DND", "APP_DND").setValue(SETTINGS_KEY, normalize(mode))


def _build_palette(colors: dict[str, str], disabled: dict[str, str]) -> QPalette:
    palette = QPalette()
    for role, value in colors.items():
        palette.setColor(getattr(QPalette.ColorRole, role), QColor(value))
    for role, value in disabled.items():
        palette.setColor(QPalette.ColorGroup.Disabled, getattr(QPalette.ColorRole, role), QColor(value))
    return palette


def apply_theme(app: QApplication, mode: str) -> str:
    mode = normalize(mode)
    global _default_look
    if _default_look is None:
        _default_look = (app.style().objectName(), app.palette())
    colors = palette_colors(mode)
    if colors is None:
        style, palette = _default_look
        app.setStyle(style)
        app.setPalette(palette)
    else:
        app.setStyle("Fusion")
        app.setPalette(_build_palette(*colors))
    return mode
