from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from pydantic import ValidationError

from app_dnd.data.equipment import WEAPONS
from app_dnd.dice import Advantage
from app_dnd.services.equipment import (
    add_custom_attack,
    attack_bonus,
    attack_from_weapon,
    damage_expression,
    remove_attack,
    roll_attack,
    roll_damage,
)
from app_dnd.services.sheet import ABILITY_LABELS, format_modifier
from app_dnd.ui.saved_tab import SavedCharacterTab
from app_dnd.ui.sizing import fit_to_screen


class WeaponPickerDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Adicionar arma")
        fit_to_screen(self, 560, 520)
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar…")
        self.search.textChanged.connect(self._fill)
        self.list = QListWidget()
        self.two_handed = QCheckBox("Empunhar com duas mãos (propriedade versátil)")
        self.off_hand = QCheckBox("Mão secundária (ação bônus, arma Leve; sem modificador no dano)")
        self.off_hand_style = QCheckBox("Estilo de Luta com Duas Armas (soma o modificador no dano)")
        self.off_hand.toggled.connect(self.off_hand_style.setEnabled)
        self.off_hand_style.setEnabled(False)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        for w in (self.search, self.list, self.two_handed, self.off_hand, self.off_hand_style, buttons):
            layout.addWidget(w)
        self._fill()

    def _fill(self) -> None:
        needle = self.search.text().strip().lower()
        self.list.clear()
        for w in WEAPONS.values():
            if needle and needle not in w.name.lower():
                continue
            item = QListWidgetItem(f"{w.name} — {w.dice} {w.damage_type} ({w.category})")
            item.setData(Qt.UserRole, w.id)
            self.list.addItem(item)

    def selected(self) -> tuple[str, bool, bool, bool] | None:
        item = self.list.currentItem()
        if not item:
            return None
        off_hand = self.off_hand.isChecked()
        return item.data(Qt.UserRole), self.two_handed.isChecked(), off_hand, off_hand and self.off_hand_style.isChecked()


class CustomAttackDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ataque personalizado")
        form = QFormLayout(self)
        self.name = QLineEdit()
        self.ability = QComboBox()
        for key, label in ABILITY_LABELS.items():
            self.ability.addItem(label, key)
        self.dice = QLineEdit("1d6")
        self.dice.setPlaceholderText("Ex.: 1d8, 2d6")
        self.damage_type = QLineEdit()
        self.to_hit = QSpinBox()
        self.to_hit.setRange(-20, 20)
        self.dmg_bonus = QSpinBox()
        self.dmg_bonus.setRange(-20, 20)
        self.proficient = QCheckBox("Proficiente")
        self.proficient.setChecked(True)
        form.addRow("Nome", self.name)
        form.addRow("Atributo", self.ability)
        form.addRow("Dado de dano", self.dice)
        form.addRow("Tipo de dano", self.damage_type)
        form.addRow("Bônus para acertar", self.to_hit)
        form.addRow("Bônus de dano", self.dmg_bonus)
        form.addRow("", self.proficient)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self) -> dict:
        return dict(
            name=self.name.text(),
            ability=self.ability.currentData(),
            damage_dice=self.dice.text().strip().lower(),
            damage_type=self.damage_type.text().strip(),
            to_hit_bonus=self.to_hit.value(),
            damage_bonus=self.dmg_bonus.value(),
            proficient=self.proficient.isChecked(),
        )


class AttacksWidget(SavedCharacterTab):
    def __init__(self, advantage_provider=lambda: Advantage.NONE, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._advantage = advantage_provider
        root = QVBoxLayout(self)
        root.addWidget(QLabel("Bônus e dano calculados com a ficha salva. Vantagem/desvantagem: use o painel de dados."))
        self.list = QListWidget()
        root.addWidget(self.list, 1)

        rolls = QHBoxLayout()
        for text, slot in (("Atacar", self._attack), ("Dano", lambda: self._damage(False)), ("Dano crítico", lambda: self._damage(True))):
            b = QPushButton(text)
            b.clicked.connect(slot)
            rolls.addWidget(b)
        rolls.addStretch(1)
        root.addLayout(rolls)

        manage = QHBoxLayout()
        for text, slot in (("Adicionar arma…", self._add_weapon), ("Ataque personalizado…", self._add_custom), ("Remover", self._remove)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            manage.addWidget(b)
        manage.addStretch(1)
        root.addLayout(manage)
        self.setEnabled(False)

    def refresh(self) -> None:
        self.list.clear()
        if self._character is None:
            return
        for a in self._character.attacks:
            text = (
                f"{a.name} — {format_modifier(attack_bonus(self._character, a))} para acertar, "
                f"{damage_expression(self._character, a)} {a.damage_type}".rstrip()
                + (" [ação bônus]" if a.off_hand else "")
            )
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, str(a.id))
            self.list.addItem(item)

    def _selected(self):
        item = self.list.currentItem()
        if item is None or self._character is None:
            return None
        return next((a for a in self._character.attacks if str(a.id) == item.data(Qt.UserRole)), None)

    def _attack(self) -> None:
        if (a := self._selected()) is not None:
            self.message.emit(f"{self._character.name} — {a.name}: {roll_attack(self._character, a, self._advantage())}")

    def _damage(self, critical: bool) -> None:
        if (a := self._selected()) is not None:
            tag = "dano crítico" if critical else "dano"
            self.message.emit(f"{self._character.name} — {a.name} ({tag}): {roll_damage(self._character, a, critical)}")

    def _add_weapon(self) -> None:
        dialog = WeaponPickerDialog(self)
        if dialog.exec() == QDialog.Accepted and (choice := dialog.selected()):
            self._apply(lambda ch: attack_from_weapon(ch, *choice))

    def _add_custom(self) -> None:
        dialog = CustomAttackDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return

        def action(ch):
            try:
                add_custom_attack(ch, **dialog.values())
            except ValidationError as exc:
                raise ValueError("; ".join(f"{e['loc'][0]}: {e['msg']}" for e in exc.errors())) from exc

        self._apply(action)

    def _remove(self) -> None:
        if (a := self._selected()) is not None:
            self._apply(lambda ch: remove_attack(ch, a.id))
