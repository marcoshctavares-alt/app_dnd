from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app_dnd.services import rests
from app_dnd.ui.saved_tab import SavedCharacterTab


class RestWidget(SavedCharacterTab):
    warning_title = "Descanso"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        self.dice_label = QLabel("")
        self.dice_label.setWordWrap(True)
        root.addWidget(self.dice_label)

        row = QHBoxLayout()
        for text, slot in (
            ("Gastar Dado de Vida", self._spend_die),
            ("Descanso curto", self._short),
            ("Descanso longo", self._long),
        ):
            button = QPushButton(text)
            button.clicked.connect(slot)
            row.addWidget(button)
        row.addStretch(1)
        root.addLayout(row)

        self.hint = QLabel("")
        self.hint.setWordWrap(True)
        self.list = QListWidget()
        root.addWidget(self.hint)
        root.addWidget(self.list)
        row = QHBoxLayout()
        for text, slot in (("Usar", self._use), ("Recuperar 1", self._restore)):
            button = QPushButton(text)
            button.clicked.connect(slot)
            row.addWidget(button)
        row.addStretch(1)
        root.addLayout(row)
        self.setEnabled(False)

    def refresh(self) -> None:
        keep = self._selected_key()
        self.list.clear()
        ch = self._character
        if ch is None:
            self.dice_label.setText("")
            self.hint.setText("")
            return
        sides = rests.hit_die_sides(ch)
        die = f"d{sides}" if sides else "—"
        self.dice_label.setText(
            f"Dados de Vida: {rests.hit_dice_remaining(ch)}/{rests.hit_dice_total(ch)} ({die}) — "
            f"PV {ch.hit_points.current}/{ch.hit_points.maximum}"
        )
        states = rests.class_resources(ch)
        if ch.ruleset != rests.RULESET_2024:
            self.hint.setText("Recursos de classe disponíveis apenas para as regras de 2024.")
        elif not states:
            self.hint.setText("Esta classe e nível não têm recursos com usos limitados neste controle.")
        else:
            self.hint.setText("Recursos de classe:")
        for state in states:
            item = QListWidgetItem(f"{state.rule.name}: {state.remaining}/{state.maximum} restantes")
            item.setData(Qt.UserRole, state.rule.key)
            self.list.addItem(item)
            if state.rule.key == keep:
                self.list.setCurrentItem(item)

    def _selected_key(self) -> str | None:
        item = self.list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _spend_die(self) -> None:
        self._apply(rests.spend_hit_die, "Dado de Vida gasto")

    def _short(self) -> None:
        self._apply(rests.short_rest, "Descanso curto concluído")

    def _long(self) -> None:
        self._apply(rests.long_rest, "Descanso longo concluído")

    def _use(self) -> None:
        if key := self._selected_key():
            self._apply(lambda c: rests.use_resource(c, key))

    def _restore(self) -> None:
        if key := self._selected_key():
            self._apply(lambda c: rests.restore_resource(c, key))
