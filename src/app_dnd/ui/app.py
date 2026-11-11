from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from app_dnd.services.sheet import default_db_path
from app_dnd.storage import Database
from app_dnd.ui import theme
from app_dnd.ui.main_window import MainWindow

EXPECTED_SRD_SPELLS = 339
EXPECTED_SPELLCASTING_CLASSES = 8


def _selftest_problems() -> list[str]:
    import PIL.Image
    import pypdf

    from app_dnd.data.spellcasting import SPELLCASTING_2024
    from app_dnd.data.spells import SRD_SPELLS

    problems = []
    if len(SRD_SPELLS) != EXPECTED_SRD_SPELLS or not all(s.description_pt for s in SRD_SPELLS):
        problems.append("catálogo de magias incompleto")
    if len(SPELLCASTING_2024) != EXPECTED_SPELLCASTING_CLASSES:
        problems.append("tabela de conjuração incompleta")
    app = QApplication.instance() or QApplication(sys.argv[:1])
    db = Database(":memory:")
    window = MainWindow(db)
    window._new()
    if len(db.list_characters()) != 1:
        problems.append("a janela não conseguiu criar e salvar uma ficha")
    window.close()
    db.close()
    del app
    return problems


def selftest(report_path: str | None = None) -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        problems = _selftest_problems()
    except Exception as exc:
        problems = [f"{type(exc).__name__}: {exc}"]
    message = "selftest ok" if not problems else "selftest FALHOU: " + "; ".join(problems)
    if report_path:
        Path(report_path).write_text(message + "\n", encoding="utf-8")
    else:
        print(message)
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    for arg in sys.argv[1:] if argv is None else argv:
        if arg == "--selftest" or arg.startswith("--selftest="):
            return selftest(arg.partition("=")[2] or None)
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    theme.apply_theme(app, theme.saved_mode())
    db = Database(default_db_path())
    window = MainWindow(db)
    window.show()
    code = app.exec()
    db.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
