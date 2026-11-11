from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app_dnd.data.feats import find_feat
from app_dnd.services.feats import (
    add_feat,
    available_feats,
    increase_options,
    prerequisite_text,
    remove_feat,
)
from app_dnd.ui.saved_tab import SavedCharacterTab

NOTE = (
    "Talentos com aumento de atributo (Aumento de Atributo, Agarrador, Dádivas) aplicam o aumento ao serem "
    "adicionados. Remover o talento não desfaz o aumento: ajuste os atributos na aba Ficha."
)


class FeatsWidget(SavedCharacterTab):
    warning_title = "Talento"

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
        note = QLabel(NOTE)
        note.setWordWrap(True)
        row = QHBoxLayout()
        for text, slot in (("Adicionar…", self._add), ("Remover", self._remove)):
            button = QPushButton(text)
            button.clicked.connect(slot)
            row.addWidget(button)
        for widget in (self.hint, self.list, self.details, note):
            root.addWidget(widget)
        root.addLayout(row)
        root.addStretch(1)
        self.setEnabled(False)

    def refresh(self) -> None:
        self.list.clear()
        self.details.setText("")
        ch = self._character
        if ch is None:
            self.hint.setText("")
            return
        if ch.ruleset != "dnd-5e-2024":
            self.hint.setText("Os talentos do SRD 5.2.1 valem para as regras de 2024.")
        else:
            self.hint.setText(f"Talentos da ficha: {len(ch.feats)}")
        for name in ch.feats:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, name)
            self.list.addItem(item)

    def _show_details(self) -> None:
        item = self.list.currentItem()
        feat = find_feat(item.data(Qt.UserRole)) if item else None
        if feat is None:
            self.details.setText("")
            return
        prereq = prerequisite_text(feat)
        header = f"{feat.name} — talento de {feat.category}" + (f" (pré-requisito: {prereq})" if prereq else "")
        self.details.setText(f"{header}\n\n{feat.description}")

    def _add(self) -> None:
        ch = self._character
        if ch is None:
            return
        if ch.ruleset != "dnd-5e-2024":
            QMessageBox.information(self, self.warning_title, "Os talentos do SRD 5.2.1 valem para as regras de 2024.")
            return
        options = {f"{f.name} [{f.category}]": f.name for f in available_feats(ch)}
        if not options:
            QMessageBox.information(self, self.warning_title, "Nenhum talento disponível para esta ficha.")
            return
        label, ok = QInputDialog.getItem(self, "Adicionar talento", "Talento:", list(options), 0, False)
        if not ok:
            return
        name = options[label]
        increases = None
        if choices := increase_options(find_feat(name)):
            pick, ok = QInputDialog.getItem(self, "Aumento de atributo", "Distribuição:", list(choices), 0, False)
            if not ok:
                return
            increases = choices[pick]
        self._apply(lambda c: add_feat(c, name, increases), f"Talento adicionado: {name}")

    def _remove(self) -> None:
        item = self.list.currentItem()
        if item is not None:
            name = item.data(Qt.UserRole)
            self._apply(lambda c: remove_feat(c, name), f"Talento removido: {name}")
