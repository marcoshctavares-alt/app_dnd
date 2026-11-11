from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QInputDialog,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QPixmap
from pydantic import ValidationError

from app_dnd.dice import Advantage
from app_dnd.data.backgrounds import BACKGROUND_NAMES, find_background
from app_dnd.data.races import find_race, lineage_label, races_for
from app_dnd.data.skills import SKILLS
from app_dnd.data.srd import CLASS_BY_NAME, CLASSES
from app_dnd.models import AbilityScores, Character, HitPoints
from app_dnd.ui.layout_rules import use_wide_layout
from app_dnd.services.backgrounds import ability_choices, apply_background, is_applied
from app_dnd.services.races import describe_race, species_traits
from app_dnd.services.skills import roll_save, roll_skill, saves_for, skill_bonus_value
from app_dnd.services.sheet import (
    ABILITY_LABELS,
    RULESET_LABELS,
    ability_check,
    apply_damage,
    apply_healing,
    format_modifier,
)


class SheetWidget(QWidget):
    saved = Signal(object)
    rolled = Signal(str)
    portrait_choose_requested = Signal()
    portrait_clear_requested = Signal()

    def __init__(self, advantage_provider=lambda: Advantage.NONE, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._character: Character | None = None
        self._advantage_provider = advantage_provider

        root = QVBoxLayout(self)
        root.addLayout(self._build_portrait())
        self._groups = (
            self._build_identity(),
            self._build_attributes(),
            self._build_skills(),
            self._build_hit_points(),
        )
        self._wide: bool | None = None
        self._body = QGridLayout()
        root.addLayout(self._body)
        self._reflow(False)

        actions = QHBoxLayout()
        self.save_btn = QPushButton("Salvar ficha")
        self.save_btn.clicked.connect(self._save)
        actions.addStretch(1)
        actions.addWidget(self.save_btn)
        root.addLayout(actions)
        root.addStretch(1)

        self.setEnabled(False)


    def _build_portrait(self) -> QHBoxLayout:
        portrait_row = QHBoxLayout()
        self.portrait_label = QLabel("Sem imagem")
        self.portrait_label.setFixedSize(140, 140)
        self.portrait_label.setAlignment(Qt.AlignCenter)
        self.portrait_label.setStyleSheet("border: 1px solid #888;")
        choose = QPushButton("Escolher imagem…")
        choose.clicked.connect(self.portrait_choose_requested)
        remove = QPushButton("Remover imagem")
        remove.clicked.connect(self.portrait_clear_requested)
        side = QVBoxLayout()
        side.addWidget(choose)
        side.addWidget(remove)
        side.addStretch(1)
        portrait_row.addWidget(self.portrait_label)
        portrait_row.addLayout(side)
        portrait_row.addStretch(1)
        return portrait_row

    def _build_identity(self) -> QGroupBox:
        ident = QGroupBox("Personagem")
        form = QFormLayout(ident)
        self.name = QLineEdit()
        self.player = QLineEdit()
        self.ruleset = QComboBox()
        for key, label in RULESET_LABELS.items():
            self.ruleset.addItem(label, key)
        self.species = QComboBox()
        self.subrace = QComboBox()
        self.subrace_label = QLabel("Sub-raça")
        self.race_info = QLabel("")
        self.race_info.setWordWrap(True)
        self.char_class = QComboBox()
        self.subclass = QComboBox()
        self.char_class.currentIndexChanged.connect(self._on_class_changed)
        self.ruleset.currentIndexChanged.connect(self._on_ruleset_changed)
        self.species.currentIndexChanged.connect(self._on_species_changed)
        self.subrace.currentIndexChanged.connect(self._update_race_info)
        self.level = QSpinBox()
        self.level.setRange(1, 20)
        self.level.valueChanged.connect(self._refresh_derived)
        self.prof_label = QLabel("")
        form.addRow("Nome", self.name)
        form.addRow("Jogador", self.player)
        form.addRow("Regras", self.ruleset)
        form.addRow("Raça/Espécie", self.species)
        form.addRow(self.subrace_label, self.subrace)
        form.addRow("", self.race_info)
        form.addRow("Classe", self.char_class)
        form.addRow("Subclasse", self.subclass)
        form.addRow("Nível", self.level)
        self.background_btn = QPushButton("Aplicar antecedente (2024)…")
        self.background_btn.clicked.connect(self._choose_background)
        form.addRow("Antecedente", self.background_btn)
        form.addRow("Bônus de proficiência", self.prof_label)
        return ident

    def _build_attributes(self) -> QGroupBox:
        attrs = QGroupBox("Atributos e salvaguardas")
        grid = QGridLayout(attrs)
        self.ability_spins: dict[str, QSpinBox] = {}
        self.ability_mods: dict[str, QLabel] = {}
        self.save_labels: dict[str, QLabel] = {}
        grid.addWidget(QLabel("<i>Atributo</i>"), 0, 1)
        grid.addWidget(QLabel("<i>Mod.</i>"), 0, 2)
        grid.addWidget(QLabel("<i>Salvaguarda (● = proficiente)</i>"), 0, 4)
        for row, (key, label) in enumerate(ABILITY_LABELS.items(), start=1):
            spin = QSpinBox()
            spin.setRange(1, 30)
            spin.valueChanged.connect(self._refresh_derived)
            mod = QLabel("+0")
            btn = QPushButton("Testar")
            btn.clicked.connect(lambda _=False, k=key: self._roll_ability(k))
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(spin, row, 1)
            grid.addWidget(mod, row, 2)
            grid.addWidget(btn, row, 3)
            save_label = QLabel("+0")
            save_btn = QPushButton("Salvaguarda")
            save_btn.clicked.connect(lambda _=False, k=key: self._roll_save(k))
            grid.addWidget(save_label, row, 4)
            grid.addWidget(save_btn, row, 5)
            self.ability_spins[key] = spin
            self.ability_mods[key] = mod
            self.save_labels[key] = save_label
        return attrs

    def _build_skills(self) -> QGroupBox:
        skills_box = QGroupBox("Perícias (Prof. = proficiente, Esp. = especialização)")
        sg = QGridLayout(skills_box)
        self.skill_prof: dict[str, QCheckBox] = {}
        self.skill_exp: dict[str, QCheckBox] = {}
        self.skill_bonus_labels: dict[str, QLabel] = {}
        for col, title in enumerate(("Prof.", "Esp.", "Perícia", "Bônus", "")):
            sg.addWidget(QLabel(f"<i>{title}</i>"), 0, col)
        for row, (skill_id, (skill_name, ability)) in enumerate(SKILLS.items(), start=1):
            prof, exp = QCheckBox(), QCheckBox()
            prof.toggled.connect(lambda on, sid=skill_id: self._on_prof_toggled(sid, on))
            exp.toggled.connect(lambda on, sid=skill_id: self._on_exp_toggled(sid, on))
            bonus = QLabel("+0")
            roll_btn = QPushButton("Testar")
            roll_btn.clicked.connect(lambda _=False, sid=skill_id: self._roll_skill(sid))
            sg.addWidget(prof, row, 0)
            sg.addWidget(exp, row, 1)
            sg.addWidget(QLabel(f"{skill_name} ({ABILITY_LABELS[ability][:3]})"), row, 2)
            sg.addWidget(bonus, row, 3)
            sg.addWidget(roll_btn, row, 4)
            self.skill_prof[skill_id], self.skill_exp[skill_id] = prof, exp
            self.skill_bonus_labels[skill_id] = bonus
        return skills_box

    def _build_hit_points(self) -> QGroupBox:
        hp_box = QGroupBox("Pontos de vida")
        hp = QGridLayout(hp_box)
        self.hp_current = QSpinBox()
        self.hp_current.setRange(0, 9999)
        self.hp_max = QSpinBox()
        self.hp_max.setRange(1, 9999)
        self.hp_temp = QSpinBox()
        self.hp_temp.setRange(0, 9999)
        self.hp_amount = QSpinBox()
        self.hp_amount.setRange(0, 9999)
        damage = QPushButton("Dano")
        damage.clicked.connect(self._damage)
        heal = QPushButton("Cura")
        heal.clicked.connect(self._heal)
        hp.addWidget(QLabel("Atuais"), 0, 0)
        hp.addWidget(self.hp_current, 0, 1)
        hp.addWidget(QLabel("Máximo"), 0, 2)
        hp.addWidget(self.hp_max, 0, 3)
        hp.addWidget(QLabel("Temporários"), 0, 4)
        hp.addWidget(self.hp_temp, 0, 5)
        hp.addWidget(QLabel("Valor"), 1, 0)
        hp.addWidget(self.hp_amount, 1, 1)
        hp.addWidget(damage, 1, 2)
        hp.addWidget(heal, 1, 3)
        return hp_box

    def _reflow(self, wide: bool) -> None:
        if wide == self._wide:
            return
        self._wide = wide
        ident, attrs, skills_box, hp_box = self._groups
        for group in self._groups:
            self._body.removeWidget(group)
        for column in range(2):
            self._body.setColumnStretch(column, 0)
        for row in range(5):
            self._body.setRowStretch(row, 0)
        if wide:
            self._body.addWidget(ident, 0, 0)
            self._body.addWidget(attrs, 1, 0)
            self._body.addWidget(hp_box, 2, 0)
            self._body.addWidget(skills_box, 0, 1, 4, 1)
            self._body.setColumnStretch(0, 1)
            self._body.setColumnStretch(1, 1)
            self._body.setRowStretch(3, 1)
        else:
            for row, group in enumerate(self._groups):
                self._body.addWidget(group, row, 0)
            self._body.setColumnStretch(0, 1)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reflow(use_wide_layout(self.width()))

    def set_portrait(self, pixmap) -> None:
        if pixmap is None or pixmap.isNull():
            self.portrait_label.setPixmap(QPixmap())
            self.portrait_label.setText("Sem imagem")
            return
        self.portrait_label.setPixmap(
            pixmap.scaled(self.portrait_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def adopt_extras(self, saved: Character) -> None:
        if self._character is not None:
            self._character = self._character.model_copy(
                update={
                    "spells": saved.spells,
                    "inventory": saved.inventory,
                    "attacks": saved.attacks,
                    "coins": saved.coins,
                    "profile": saved.profile,
                    "feats": saved.feats,
                    "hit_dice_used": saved.hit_dice_used,
                    "resources_used": saved.resources_used,
                }
            )

    def adopt_hit_points(self, saved: Character) -> None:
        if self._character is None:
            return
        self._character = self._character.model_copy(update={"hit_points": saved.hit_points})
        self.hp_max.setValue(saved.hit_points.maximum)
        self.hp_current.setValue(saved.hit_points.current)
        self.hp_temp.setValue(saved.hit_points.temporary)

    def adopt_abilities(self, saved: Character) -> None:
        if self._character is None:
            return
        self._character = self._character.model_copy(update={"abilities": saved.abilities})
        for key, spin in self.ability_spins.items():
            spin.setValue(getattr(saved.abilities, key))
        self._refresh_derived()

    def current_character(self) -> Character | None:
        if self._character is None:
            return None
        try:
            return self._collect()
        except ValidationError as exc:
            self._show_error(exc)
            return None

    def load(self, character: Character | None, portrait=None) -> None:
        self._character = character
        self.setEnabled(character is not None)
        self.set_portrait(portrait)
        if character is None:
            return
        self.name.setText(character.name)
        self.player.setText(character.player_name or "")
        self.ruleset.setCurrentIndex(max(0, self.ruleset.findData(character.ruleset)))
        self._fill_species(character.species, character.subrace)
        self._fill_classes(character.character_class, character.subclass)
        self.level.setValue(character.level)
        for key, spin in self.ability_spins.items():
            spin.setValue(getattr(character.abilities, key))
        self.hp_max.setValue(character.hit_points.maximum)
        self.hp_current.setValue(character.hit_points.current)
        self.hp_temp.setValue(character.hit_points.temporary)
        for skill_id in SKILLS:
            self.skill_prof[skill_id].setChecked(skill_id in character.skills.proficient)
            self.skill_exp[skill_id].setChecked(skill_id in character.skills.expertise)
        self._refresh_derived()

    def _collect(self) -> Character:
        assert self._character is not None
        data = self._character.model_dump()
        data.update(
            name=self.name.text(),
            player_name=self.player.text().strip() or None,
            ruleset=self.ruleset.currentData(),
            species=self.species.currentData(),
            subrace=self.subrace.currentData(),
            character_class=self.char_class.currentData(),
            subclass=self.subclass.currentData(),
            level=self.level.value(),
            abilities={k: s.value() for k, s in self.ability_spins.items()},
            hit_points={
                "current": self.hp_current.value(),
                "maximum": self.hp_max.value(),
                "temporary": self.hp_temp.value(),
            },
            skills={
                "proficient": [k for k, b in self.skill_prof.items() if b.isChecked()],
                "expertise": [k for k, b in self.skill_exp.items() if b.isChecked() and self.skill_prof[k].isChecked()],
            },
        )
        return Character.model_validate(data)

    def _fill_species(self, species: str | None, subrace: str | None) -> None:
        ruleset = self.ruleset.currentData()
        self.species.blockSignals(True)
        self.species.clear()
        self.species.addItem("—", None)
        for race in races_for(ruleset):
            self.species.addItem(race.name, race.name)
        if species and self.species.findData(species) < 0:
            self.species.addItem(f"{species} (personalizada)", species)
        self.species.setCurrentIndex(max(0, self.species.findData(species)))
        self.species.blockSignals(False)
        self._fill_subrace(subrace)

    def _fill_subrace(self, subrace: str | None) -> None:
        race = find_race(self.ruleset.currentData(), self.species.currentData())
        self.subrace_label.setText(lineage_label(self.ruleset.currentData(), self.species.currentData()))
        self.subrace.blockSignals(True)
        self.subrace.clear()
        self.subrace.addItem("—", None)
        for sub in (race.subraces if race else ()):
            self.subrace.addItem(sub.name, sub.name)
        if subrace and self.subrace.findData(subrace) < 0:
            self.subrace.addItem(f"{subrace} (personalizada)", subrace)
        self.subrace.setCurrentIndex(max(0, self.subrace.findData(subrace)))
        self.subrace.blockSignals(False)
        self._update_race_info()

    def _on_ruleset_changed(self) -> None:
        self._fill_species(self.species.currentData(), self.subrace.currentData())
        self._fill_subclass(self.subclass.currentData())

    def _on_class_changed(self) -> None:
        self._fill_subclass(None)
        self._refresh_derived()

    def _fill_classes(self, character_class: str | None, subclass: str | None) -> None:
        self.char_class.blockSignals(True)
        self.char_class.clear()
        self.char_class.addItem("—", None)
        for info in CLASSES:
            self.char_class.addItem(info.name, info.name)
        if character_class and self.char_class.findData(character_class) < 0:
            self.char_class.addItem(f"{character_class} (personalizada)", character_class)
        self.char_class.setCurrentIndex(max(0, self.char_class.findData(character_class)))
        self.char_class.blockSignals(False)
        self._fill_subclass(subclass)

    def _fill_subclass(self, subclass: str | None) -> None:
        info = CLASS_BY_NAME.get(self.char_class.currentData() or "")
        self.subclass.blockSignals(True)
        self.subclass.clear()
        self.subclass.addItem("—", None)
        if info is not None:
            name, level = info.subclass_for(self.ruleset.currentData())
            self.subclass.addItem(f"{name} (nível {level})", name)
        if subclass and self.subclass.findData(subclass) < 0:
            self.subclass.addItem(f"{subclass} (personalizada)", subclass)
        self.subclass.setCurrentIndex(max(0, self.subclass.findData(subclass)))
        self.subclass.blockSignals(False)

    def _on_species_changed(self) -> None:
        self._fill_subrace(None)

    def _update_race_info(self) -> None:
        try:
            args = (self.ruleset.currentData(), self.species.currentData(), self.subrace.currentData())
            lines = [describe_race(*args), *("• " + t for t in species_traits(*args))]
            self.race_info.setText("\n".join(line for line in lines if line))
        except ValueError:
            self.race_info.setText("")

    def _refresh_derived(self) -> None:
        scores = AbilityScores(**{k: s.value() for k, s in self.ability_spins.items()})
        for key, label in self.ability_mods.items():
            label.setText(format_modifier(scores.modifier(key)))
        from app_dnd.models import proficiency_bonus

        pb = proficiency_bonus(self.level.value())
        self.prof_label.setText(format_modifier(pb))

        saves = saves_for(self.char_class.currentData() or "")
        for key, label in self.save_labels.items():
            proficient = key in saves
            value = skill_bonus_value(scores.modifier(key), pb, proficient)
            label.setText(f"{'● ' if proficient else ''}{format_modifier(value)}")
        for skill_id, (_, ability) in SKILLS.items():
            value = skill_bonus_value(
                scores.modifier(ability), pb, self.skill_prof[skill_id].isChecked(), self.skill_exp[skill_id].isChecked()
            )
            self.skill_bonus_labels[skill_id].setText(format_modifier(value))

    def _on_prof_toggled(self, skill_id: str, on: bool) -> None:
        if not on:
            self.skill_exp[skill_id].setChecked(False)
        self._refresh_derived()

    def _on_exp_toggled(self, skill_id: str, on: bool) -> None:
        if on:
            self.skill_prof[skill_id].setChecked(True)
        self._refresh_derived()

    def _roll_skill(self, skill_id: str) -> None:
        character = self.current_character()
        if character is not None:
            result = roll_skill(character, skill_id, self._advantage_provider())
            self.rolled.emit(f"{character.name} — {SKILLS[skill_id][0]}: {result}")

    def _roll_save(self, ability: str) -> None:
        character = self.current_character()
        if character is not None:
            result = roll_save(character, ability, self._advantage_provider())
            self.rolled.emit(f"{character.name} — Salvaguarda de {ABILITY_LABELS[ability]}: {result}")

    def _roll_ability(self, key: str) -> None:
        try:
            character = self._collect()
        except ValidationError as exc:
            self._show_error(exc)
            return
        result = ability_check(character, key, self._advantage_provider())
        self.rolled.emit(f"{character.name} — {ABILITY_LABELS[key]}: {result}")

    def _current_hp(self) -> HitPoints | None:
        try:
            return HitPoints(
                current=self.hp_current.value(),
                maximum=self.hp_max.value(),
                temporary=self.hp_temp.value(),
            )
        except ValidationError as exc:
            self._show_error(exc)
            return None

    def _apply_hp(self, hp: HitPoints) -> None:
        self.hp_current.setValue(hp.current)
        self.hp_temp.setValue(hp.temporary)

    def _damage(self) -> None:
        if (hp := self._current_hp()) is not None:
            self._apply_hp(apply_damage(hp, self.hp_amount.value()))

    def _heal(self) -> None:
        if (hp := self._current_hp()) is not None:
            self._apply_hp(apply_healing(hp, self.hp_amount.value()))

    def _choose_background(self) -> None:
        character = self.current_character()
        if character is None:
            return
        if character.ruleset != "dnd-5e-2024":
            QMessageBox.information(self, "Antecedente", "Os antecedentes do SRD 5.2.1 valem para as regras de 2024.")
            return
        if is_applied(character):
            QMessageBox.information(
                self, "Antecedente", f"Esta ficha já tem o antecedente {character.profile.background}."
            )
            return
        name, ok = QInputDialog.getItem(self, "Antecedente", "Escolha o antecedente:", list(BACKGROUND_NAMES), 0, False)
        if not ok:
            return
        choices = ability_choices(find_background(name))
        label, ok = QInputDialog.getItem(
            self, "Aumento de atributos", "Distribuição dos aumentos:", list(choices), 0, False
        )
        if not ok:
            return
        try:
            updated = apply_background(character, name, choices[label])
        except ValueError as exc:
            QMessageBox.warning(self, "Antecedente", str(exc))
            return
        self._character = updated
        self.saved.emit(updated)

    def _save(self) -> None:
        try:
            character = self._collect()
        except ValidationError as exc:
            self._show_error(exc)
            return
        self._character = character
        self.saved.emit(character)

    def _show_error(self, exc: ValidationError) -> None:
        lines = [f"• {'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()]
        QMessageBox.warning(self, "Dados inválidos", "\n".join(lines))
