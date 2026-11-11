from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from app_dnd.services.subclass import class_features, subclass_features
from app_dnd.ui.saved_tab import SavedCharacterTab


class FeaturesWidget(SavedCharacterTab):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        self.hint = QLabel("")
        self.hint.setWordWrap(True)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._show_details)
        self.details = QLabel("")
        self.details.setWordWrap(True)
        self.details.setTextFormat(Qt.PlainText)
        for widget in (self.hint, self.list, self.details):
            root.addWidget(widget)
        root.addStretch(1)
        self.setEnabled(False)

    def refresh(self) -> None:
        self.list.clear()
        self.details.setText("")
        ch = self._character
        if ch is None:
            self.hint.setText("")
            return
        rows = [(f.level, 0, f.name, f"{f.name} ({f.name_en})\n\n{f.text}", "") for f in class_features(ch)]
        rows += [(f.level, 1, f.name, f"{f.name}\n\n{f.text}", "Subclasse: ") for f in subclass_features(ch)]
        if not rows:
            self.hint.setText(
                "Sem características para exibir. A lista usa as classes e subclasses do SRD 5.2.1 nas regras "
                "de 2024 (salve a ficha após escolher classe e subclasse)."
            )
            return
        self.hint.setText(f"Características até o nível {ch.level}; as demais aparecem como bloqueadas.")
        for level, _order, name, details, prefix in sorted(rows, key=lambda r: (r[0], r[1])):
            suffix = "  (bloqueada)" if level > ch.level else ""
            item = QListWidgetItem(f"Nível {level} — {prefix}{name}{suffix}")
            item.setData(Qt.UserRole, details)
            self.list.addItem(item)

    def _show_details(self) -> None:
        item = self.list.currentItem()
        self.details.setText(item.data(Qt.UserRole) if item else "")
