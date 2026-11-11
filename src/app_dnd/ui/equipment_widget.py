from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QVBoxLayout,
    QWidget,
)

from app_dnd.data.equipment import ARMORS, WEAPONS
from app_dnd.models import Coins
from app_dnd.services.equipment import (
    add_catalog_item,
    add_custom_item,
    armor_class,
    armor_warnings,
    carrying_capacity,
    remove_item,
    set_equipped,
    set_quantity,
    total_weight,
)
from app_dnd.ui.saved_tab import SavedCharacterTab
from app_dnd.ui.sizing import fit_to_screen
from app_dnd.ui.theme import ERROR_COLOR


class CatalogPickerDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        fit_to_screen(self, 480, 520)
        self.setWindowTitle("Adicionar do catálogo")
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar…")
        self.search.textChanged.connect(self._fill)
        self.list = QListWidget()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        for w in (self.search, self.list, buttons):
            layout.addWidget(w)
        self._fill()

    def _fill(self) -> None:
        needle = self.search.text().strip().lower()
        self.list.clear()
        entries = [(w.id, f"[Arma] {w.name} — {w.dice} {w.damage_type}", w.name) for w in WEAPONS.values()]
        entries += [(a.id, f"[Armadura] {a.name} — CA {a.base_ac}" if a.kind != "escudo" else f"[Escudo] {a.name} — +2 CA", a.name) for a in ARMORS.values()]
        for cid, text, name in entries:
            if needle and needle not in name.lower():
                continue
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, cid)
            self.list.addItem(item)

    def selected_id(self) -> str | None:
        item = self.list.currentItem()
        return item.data(Qt.UserRole) if item else None


class CustomItemDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Item personalizado")
        form = QFormLayout(self)
        self.name = QLineEdit()
        self.quantity = QSpinBox()
        self.quantity.setRange(1, 9999)
        self.weight = QDoubleSpinBox()
        self.weight.setRange(0, 100000)
        self.weight.setDecimals(2)
        self.weight.setSuffix(" lb")
        self.notes = QLineEdit()
        form.addRow("Nome", self.name)
        form.addRow("Quantidade", self.quantity)
        form.addRow("Peso (unidade)", self.weight)
        form.addRow("Notas", self.notes)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)


class EquipmentWidget(SavedCharacterTab):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        root.addWidget(self.summary)

        self.list = QListWidget()
        root.addWidget(self.list, 1)

        row = QHBoxLayout()
        for text, slot in (
            ("Adicionar do catálogo…", self._add_catalog),
            ("Item personalizado…", self._add_custom),
            ("Equipar/Desequipar", self._toggle_equipped),
            ("Quantidade…", self._quantity),
            ("Remover", self._remove),
        ):
            b = QPushButton(text)
            b.clicked.connect(slot)
            row.addWidget(b)
        root.addLayout(row)

        coins_box = QGroupBox("Moedas")
        grid = QGridLayout(coins_box)
        self.coin_spins: dict[str, QSpinBox] = {}
        for col, (key, label) in enumerate((("cp", "PC (cobre)"), ("sp", "PP (prata)"), ("ep", "PE (electro)"), ("gp", "PO (ouro)"), ("pp", "PL (platina)"))):
            spin = QSpinBox()
            spin.setRange(0, 10_000_000)
            grid.addWidget(QLabel(label), 0, col)
            grid.addWidget(spin, 1, col)
            self.coin_spins[key] = spin
        save = QPushButton("Atualizar moedas")
        save.clicked.connect(self._save_coins)
        grid.addWidget(save, 1, 5)
        root.addWidget(coins_box)
        self.setEnabled(False)

    def refresh(self) -> None:
        self.list.clear()
        ch = self._character
        if ch is None:
            self.summary.clear()
            return
        weight, cap = total_weight(ch), carrying_capacity(ch)
        over = f" <b style='color:{ERROR_COLOR}'>(acima da capacidade!)</b>" if weight > cap else ""
        self.summary.setText(
            f"<b>CA {armor_class(ch)}</b> &nbsp;·&nbsp; Peso {weight:g}/{cap} lb{over} &nbsp;·&nbsp; "
            f"Moedas: {ch.coins.total_gp:g} PO (valor total)"
            + "".join(f"<br><b style='color:{ERROR_COLOR}'>Aviso:</b> {w}" for w in armor_warnings(ch))
        )
        for item in ch.inventory:
            mark = "[E] " if item.equipped else ""
            weight_text = f" ({item.weight * item.quantity:g} lb)" if item.weight else ""
            li = QListWidgetItem(f"{mark}{item.name} ×{item.quantity}{weight_text}")
            li.setData(Qt.UserRole, str(item.id))
            self.list.addItem(li)
        for key, spin in self.coin_spins.items():
            spin.setValue(getattr(ch.coins, key))

    def _selected_item(self):
        li = self.list.currentItem()
        if li is None or self._character is None:
            return None
        return next((i for i in self._character.inventory if str(i.id) == li.data(Qt.UserRole)), None)

    def _add_catalog(self) -> None:
        dialog = CatalogPickerDialog(self)
        if dialog.exec() == QDialog.Accepted and (cid := dialog.selected_id()):
            self._apply(lambda ch: add_catalog_item(ch, cid))

    def _add_custom(self) -> None:
        dialog = CustomItemDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self._apply(
                lambda ch: add_custom_item(
                    ch, dialog.name.text(), dialog.quantity.value(), dialog.weight.value(), dialog.notes.text().strip() or None
                )
            )

    def _toggle_equipped(self) -> None:
        if (item := self._selected_item()) is not None:
            self._apply(lambda ch: set_equipped(ch, item.id, not item.equipped))

    def _quantity(self) -> None:
        if (item := self._selected_item()) is None:
            return
        value, ok = QInputDialog.getInt(self, "Quantidade", f"Quantidade de {item.name}:", item.quantity, 1, 9999)
        if ok:
            self._apply(lambda ch: set_quantity(ch, item.id, value))

    def _remove(self) -> None:
        if (item := self._selected_item()) is not None:
            self._apply(lambda ch: remove_item(ch, item.id))

    def _save_coins(self) -> None:
        coins = Coins(**{k: s.value() for k, s in self.coin_spins.items()})

        def action(ch):
            ch.coins = coins

        self._apply(action)
