from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app_dnd.services.sheet import ABILITY_LABELS
from app_dnd.services.spells import (
    SpellCatalog,
    add_spell,
    cantrip_count,
    cast_spell,
    format_spell,
    load_spell_pack,
    max_cantrips,
    max_prepared,
    remaining_slots,
    remove_spell,
    set_prepared,
    spellcasting_stats,
    spend_slot,
)
from app_dnd.services import rests
from app_dnd.storage import Database
from app_dnd.ui.saved_tab import SavedCharacterTab
from app_dnd.ui.sizing import fit_to_screen


class SpellDetailsDialog(QDialog):
    def __init__(self, title: str, text: str, original: str | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        fit_to_screen(self, 560, 620)
        layout = QVBoxLayout(self)
        view = QTextEdit()
        view.setReadOnly(True)
        view.setPlainText(text)
        layout.addWidget(view)
        if original and original != text:
            toggle = QCheckBox("Mostrar texto original (inglês)")
            toggle.toggled.connect(lambda on: view.setPlainText(original if on else text))
            layout.addWidget(toggle)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.clicked.connect(lambda _: self.accept())
        layout.addWidget(buttons)


class SpellPickerDialog(QDialog):
    def __init__(self, catalog: SpellCatalog, class_name: str | None, exclude: set[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Adicionar magias")
        fit_to_screen(self, 480, 520)
        self._catalog, self._class, self._exclude = catalog, class_name, exclude

        layout = QVBoxLayout(self)
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar por nome…")
        self.search.textChanged.connect(self._refill)
        self.level = QComboBox()
        self.level.addItem("Todos os níveis", None)
        self.level.addItem("Truques", 0)
        for n in range(1, 10):
            self.level.addItem(f"Nível {n}", n)
        self.level.currentIndexChanged.connect(self._refill)
        filters.addWidget(self.search, 1)
        filters.addWidget(self.level)
        layout.addLayout(filters)

        self.only_class = QCheckBox(f"Só magias de {class_name}" if class_name else "Só magias da minha classe")
        self.only_class.setChecked(bool(class_name))
        self.only_class.setEnabled(bool(class_name))
        self.only_class.toggled.connect(self._refill)
        layout.addWidget(self.only_class)

        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.list)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._refill()

    def _refill(self) -> None:
        self.list.clear()
        cls = self._class if self.only_class.isChecked() else None
        for spell in self._catalog.search(self.search.text(), self.level.currentData(), cls):
            if spell.id in self._exclude:
                continue
            tag = "Truque" if spell.level == 0 else f"Nv {spell.level}"
            item = QListWidgetItem(f"[{tag}] {spell.name}")
            item.setData(Qt.UserRole, spell.id)
            self.list.addItem(item)

    def selected_ids(self) -> list[str]:
        return [i.data(Qt.UserRole) for i in self.list.selectedItems()]


class SpellsWidget(SavedCharacterTab):
    warning_title = "Magias"

    def __init__(self, db: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db = db
        self._catalog = SpellCatalog(db.list_custom_spells())

        root = QVBoxLayout(self)
        self.stats = QLabel("")
        self.stats.setWordWrap(True)
        self.slots = QLabel("")
        self.slots.setWordWrap(True)
        self.slots.setTextFormat(Qt.RichText)
        root.addWidget(self.stats)
        root.addWidget(self.slots)

        rest = QHBoxLayout()
        spend = QPushButton("Gastar espaço…")
        spend.clicked.connect(self._spend)
        short = QPushButton("Descanso curto")
        short.clicked.connect(lambda: self._apply(rests.short_rest, "Descanso curto concluído (só o Bruxo recupera espaços de magia)"))
        long_ = QPushButton("Descanso longo")
        long_.clicked.connect(lambda: self._apply(rests.long_rest, "Descanso longo concluído: PV, espaços e recursos recuperados"))
        for b in (spend, short, long_):
            rest.addWidget(b)
        rest.addStretch(1)
        root.addLayout(rest)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda _: self._details())
        root.addWidget(self.list, 1)

        actions = QHBoxLayout()
        for text, slot in (
            ("Adicionar…", self._add),
            ("Remover", self._remove),
            ("Preparar/Despreparar", self._toggle_prepared),
            ("Conjurar", self._cast),
            ("Detalhes", self._details),
            ("Importar pacote…", self._import_pack),
        ):
            b = QPushButton(text)
            b.clicked.connect(slot)
            actions.addWidget(b)
        root.addLayout(actions)
        self.setEnabled(False)

    def reload_catalog(self) -> None:
        self._catalog = SpellCatalog(self._db.list_custom_spells())
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        ch = self._character
        if ch is None:
            self.stats.clear()
            self.slots.clear()
            return

        stats = spellcasting_stats(ch)
        if stats is None:
            self.stats.setText(f"{ch.character_class or 'Esta classe'} não conjura magias (baseado na ficha salva).")
        else:
            limit = max_prepared(ch)
            extra = f" · Preparadas: {len(ch.spells.prepared)}/{limit}" if limit is not None else ""
            cap = max_cantrips(ch)
            if cap is not None:
                extra += f" · Truques: {cantrip_count(ch, self._catalog)}/{cap}"
            self.stats.setText(
                f"Atributo: {ABILITY_LABELS[stats['ability']]} · CD de resistência {stats['save_dc']} · "
                f"Bônus de ataque +{stats['attack_bonus']}{extra}  (baseado na ficha salva)"
            )
        slots = remaining_slots(ch)
        self.slots.setText(
            "Espaços: " + (" &nbsp; ".join(f"<b>Nv {lvl}</b>: {left}/{total}" for lvl, (left, total) in slots.items()) or "—")
        )

        for spell_id in sorted(
            ch.spells.known,
            key=lambda i: ((self._catalog.get(i).level if self._catalog.get(i) else 99), i),
        ):
            spell = self._catalog.get(spell_id)
            if spell is None:
                text = f"[?] {spell_id} (magia não encontrada no catálogo)"
            else:
                tag = "Truque" if spell.level == 0 else f"Nv {spell.level}"
                mark = "★ " if spell_id in ch.spells.prepared else ""
                text = f"{mark}[{tag}] {spell.name}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, spell_id)
            self.list.addItem(item)

    def _selected_id(self) -> str | None:
        item = self.list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _add(self) -> None:
        if self._character is None:
            return
        dialog = SpellPickerDialog(
            self._catalog, self._character.character_class, set(self._character.spells.known), self
        )
        if dialog.exec() != QDialog.Accepted:
            return
        ids = dialog.selected_ids()
        if ids:
            self._apply(lambda ch: [add_spell(ch, self._catalog, i) for i in ids])

    def _remove(self) -> None:
        if (sid := self._selected_id()) is not None:
            self._apply(lambda ch: remove_spell(ch, sid))

    def _toggle_prepared(self) -> None:
        sid = self._selected_id()
        if sid is None or self._character is None:
            return
        now = sid in self._character.spells.prepared
        self._apply(lambda ch: set_prepared(ch, self._catalog, sid, not now))

    def _cast(self) -> None:
        sid = self._selected_id()
        if sid is None or self._character is None:
            return
        spell = self._catalog.get(sid)
        slot_level = None
        if spell and spell.level > 0 and (remaining := remaining_slots(self._character)):
            default = spell.level if spell.level in remaining else min(remaining)
            slot_level, ok = QInputDialog.getInt(
                self, "Conjurar", f"Nível do espaço para {spell.name}:", default, spell.level, 9
            )
            if not ok:
                return
        outcome: list[str] = []
        self._apply(lambda ch: outcome.append(cast_spell(ch, self._catalog, sid, slot_level)))
        if outcome:
            self.message.emit(outcome[0])

    def _spend(self) -> None:
        if self._character is None:
            return
        level, ok = QInputDialog.getInt(self, "Gastar espaço", "Nível do espaço:", 1, 1, 9)
        if ok:
            self._apply(lambda ch: spend_slot(ch, level))

    def _details(self) -> None:
        sid = self._selected_id()
        spell = self._catalog.get(sid) if sid else None
        if spell:
            SpellDetailsDialog(spell.name, format_spell(spell), format_spell(spell, original=True), self).exec()

    def _import_pack(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Importar pacote de magias", "", "JSON (*.json)")
        if not path:
            return
        try:
            spells = load_spell_pack(Path(path).read_text(encoding="utf-8"))
        except (ValueError, OSError, UnicodeDecodeError) as exc:
            QMessageBox.warning(self, "Falha ao importar", str(exc))
            return
        for spell in spells:
            self._db.save_custom_spell(spell)
        self.reload_catalog()
        self.message.emit(f"{len(spells)} magia(s) importada(s)")
