from __future__ import annotations

from pathlib import Path
from uuid import UUID

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app_dnd.data.credits import ATTRIBUTION, CONTENT_NOTE, LICENSE_NOTE
from app_dnd.backup import BackupError, export_backup, import_backup
from app_dnd.models import Character
from app_dnd.services.generator import random_character
from app_dnd.services.portrait import clear_portrait, set_portrait
from app_dnd.services.sheet import new_character
from app_dnd.services.spells import SpellCatalog
from app_dnd.storage import Database
from app_dnd.ui import theme
from app_dnd.ui.attacks_widget import AttacksWidget
from app_dnd.ui.dice_panel import DicePanel
from app_dnd.ui.equipment_widget import EquipmentWidget
from app_dnd.ui.image_utils import load_and_shrink, pixmap_from_bytes
from app_dnd.ui.feats_widget import FeatsWidget
from app_dnd.ui.layout_rules import dice_dock_at_bottom, list_panel_width
from app_dnd.ui.sheet_widget import SheetWidget
from app_dnd.ui.rest_widget import RestWidget
from app_dnd.ui.sizing import available_geometry, center_on_screen, fit_to_screen, scrollable
from app_dnd.ui.spells_widget import SpellsWidget
from app_dnd.ui.features_widget import FeaturesWidget


class MainWindow(QMainWindow):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self._db = db
        self.setWindowTitle("APP_DND")
        size = fit_to_screen(self, 1280, 820)
        center_on_screen(self, size)

        self.dice = DicePanel()
        self._build_tabs()
        self.setCentralWidget(self._build_splitter(self._build_list_panel(), size[0]))
        self._build_dice_dock()
        self._build_menu()
        self._reload_list()
        self._warn_invalid_characters()

    def _build_list_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._on_selection)
        buttons = QHBoxLayout()
        for label, handler in (("Novo", self._new), ("Aleatório", self._random), ("Excluir", self._delete)):
            button = QPushButton(label)
            button.clicked.connect(handler)
            buttons.addWidget(button)
        layout.addWidget(self.list)
        layout.addLayout(buttons)
        return panel

    def _build_tabs(self) -> None:
        self.sheet = SheetWidget(advantage_provider=self.dice.selected_advantage)
        self.sheet.saved.connect(self._on_saved)
        self.sheet.rolled.connect(self.dice.add_history)
        self.sheet.portrait_choose_requested.connect(self._choose_portrait)
        self.sheet.portrait_clear_requested.connect(self._clear_portrait)

        self.spells = SpellsWidget(self._db)
        self.attacks = AttacksWidget(advantage_provider=self.dice.selected_advantage)
        self.equipment = EquipmentWidget()
        self.feats = FeatsWidget()
        self.features = FeaturesWidget()
        self.rest = RestWidget()
        self._saved_tabs = [self.spells, self.attacks, self.equipment, self.feats, self.features, self.rest]
        for tab in self._saved_tabs:
            tab.changed.connect(lambda ch, t=tab: self._on_tab_changed(t, ch))
            tab.message.connect(self._on_spell_message)

        self.tabs = QTabWidget()
        for widget, title in (
            (self.sheet, "Ficha"),
            (self.attacks, "Ataques"),
            (self.equipment, "Equipamento"),
            (self.feats, "Talentos"),
            (self.features, "Características"),
            (self.rest, "Descanso"),
            (self.spells, "Magias"),
        ):
            self.tabs.addTab(scrollable(widget), title)

    def _build_splitter(self, left: QWidget, window_width: int) -> QSplitter:
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setCollapsible(1, False)
        list_width = list_panel_width(window_width)
        splitter.setSizes([list_width, window_width - list_width])
        return splitter

    def _build_dice_dock(self) -> None:
        dock = QDockWidget("Dados", self)
        dock.setWidget(self.dice)
        self.dice.setMinimumWidth(240)
        bottom = dice_dock_at_bottom(available_geometry(self)[2])
        self.addDockWidget(Qt.BottomDockWidgetArea if bottom else Qt.RightDockWidgetArea, dock)

    def _build_menu(self) -> None:
        menu = self.menuBar().addMenu("&Arquivo")
        export_action = QAction("Exportar backup…", self)
        export_action.triggered.connect(self._export)
        import_action = QAction("Importar backup…", self)
        import_action.triggered.connect(self._import)
        quit_action = QAction("Sair", self)
        quit_action.triggered.connect(self.close)
        pdf_action = QAction("Exportar ficha em PDF…", self)
        pdf_action.triggered.connect(self._export_pdf)
        template_action = QAction("Escolher modelo de PDF…", self)
        template_action.triggered.connect(lambda: self._choose_template(force=True))
        menu.addAction(pdf_action)
        menu.addAction(template_action)
        menu.addSeparator()
        menu.addAction(export_action)
        menu.addAction(import_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self._build_view_menu()
        help_menu = self.menuBar().addMenu("A&juda")
        credits_action = QAction("Licenças e créditos…", self)
        credits_action.triggered.connect(self._show_credits)
        help_menu.addAction(credits_action)

    def _build_view_menu(self) -> None:
        theme_menu = self.menuBar().addMenu("E&xibir").addMenu("Tema")
        group = QActionGroup(self)
        current = theme.saved_mode()
        self.theme_actions = {}
        for mode, label in theme.MODES:
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(mode == current)
            action.triggered.connect(lambda _checked=False, m=mode: self._set_theme(m))
            group.addAction(action)
            theme_menu.addAction(action)
            self.theme_actions[mode] = action

    def _set_theme(self, mode: str) -> None:
        theme.save_mode(theme.apply_theme(QApplication.instance(), mode))

    def _warn_invalid_characters(self, prefix: str = "Ignoradas") -> None:
        invalid = self._db.invalid_character_ids()
        if invalid:
            QMessageBox.warning(
                self,
                "Fichas inválidas",
                f"{prefix} {len(invalid)} ficha(s) com dados inválidos no banco. Elas continuam salvas, "
                "mas não aparecem na lista.",
            )

    def _reload_list(self, select: UUID | None = None) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        target_row = -1
        for row, ch in enumerate(self._db.list_characters()):
            item = QListWidgetItem(f"{ch.name} — nível {ch.level}")
            item.setData(Qt.UserRole, str(ch.id))
            self.list.addItem(item)
            if select is not None and ch.id == select:
                target_row = row
        self.list.blockSignals(False)
        if target_row >= 0:
            self.list.setCurrentRow(target_row)
        else:
            self._show(None)

    def _selected_id(self) -> UUID | None:
        item = self.list.currentItem()
        return UUID(item.data(Qt.UserRole)) if item else None

    def _on_selection(self, *_: object) -> None:
        char_id = self._selected_id()
        self._show(self._db.get_character(char_id) if char_id else None)

    def _show(self, character: Character | None) -> None:
        pixmap = None
        if character and character.portrait_id and (asset := self._db.get_asset(character.portrait_id)):
            pixmap = pixmap_from_bytes(asset[0])
        self.sheet.load(character, pixmap)
        for tab in self._saved_tabs:
            tab.load(character.model_copy(deep=True) if character else None)

    def _new(self) -> None:
        ch = self._db.save_character(new_character())
        self._reload_list(select=ch.id)

    def _random(self) -> None:
        level, ok = QInputDialog.getInt(self, "Ficha aleatória", "Nível (1–20):", 1, 1, 20)
        if not ok:
            return
        ch = self._db.save_character(random_character(level=level))
        self._reload_list(select=ch.id)

    def _choose_portrait(self) -> None:
        character = self.sheet.current_character()
        if character is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Escolher imagem", "", "Imagens (*.png *.jpg *.jpeg *.webp *.bmp *.gif)"
        )
        if not path:
            return
        try:
            saved = set_portrait(self._db, character, load_and_shrink(path))
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Imagem inválida", str(exc))
            return
        self._reload_list(select=saved.id)

    def _clear_portrait(self) -> None:
        character = self.sheet.current_character()
        if character is None:
            return
        saved = clear_portrait(self._db, character)
        self._reload_list(select=saved.id)

    def _delete(self) -> None:
        char_id = self._selected_id()
        if char_id is None:
            return
        answer = QMessageBox.question(self, "Excluir", "Excluir esta ficha? Não dá para desfazer.")
        if answer == QMessageBox.Yes:
            self._db.delete_character(char_id)
            self._reload_list()

    def _on_saved(self, character: Character) -> None:
        self._db.save_character(character)
        self._reload_list(select=character.id)
        self.statusBar().showMessage("Ficha salva", 3000)

    def _on_tab_changed(self, source, character: Character) -> None:
        saved = self._db.save_character(character)
        self.sheet.adopt_extras(saved)
        if source is self.feats:
            self.sheet.adopt_abilities(saved)
        if source in (self.rest, self.spells):
            self.sheet.adopt_hit_points(saved)
        for tab in self._saved_tabs:
            if tab is not source:
                tab.load(saved.model_copy(deep=True))

    def _on_spell_message(self, text: str) -> None:
        self.statusBar().showMessage(text, 5000)
        self.dice.add_history(text)

    def _show_credits(self) -> None:
        QMessageBox.information(self, "Licenças e créditos", f"{ATTRIBUTION}\n\n{CONTENT_NOTE}\n\n{LICENSE_NOTE}")

    def _choose_template(self, force: bool = False) -> str | None:
        settings = QSettings("APP_DND", "APP_DND")
        saved = settings.value("pdf/template", "")
        if saved and Path(saved).is_file() and not force:
            return saved
        QMessageBox.information(
            self,
            "Modelo de ficha em PDF",
            "Escolha o PDF da ficha oficial de D&D 5e com campos de formulário (6 páginas, versão 2014).\n\n"
            "O arquivo é da Wizards of the Coast e de uso pessoal: o app não o inclui nem o redistribui; "
            "ele apenas preenche uma cópia sua.",
        )
        path, _ = QFileDialog.getOpenFileName(self, "Escolher modelo de ficha (PDF)", "", "PDF (*.pdf)")
        if not path:
            return None
        settings.setValue("pdf/template", path)
        return path

    def _export_pdf(self) -> None:
        character = self.sheet.current_character()
        if character is None:
            QMessageBox.information(self, "Exportar PDF", "Selecione uma ficha primeiro.")
            return
        template = self._choose_template()
        if not template:
            return
        target, _ = QFileDialog.getSaveFileName(self, "Salvar ficha em PDF", f"{character.name}.pdf", "PDF (*.pdf)")
        if not target:
            return
        portrait = None
        if character.portrait_id and (asset := self._db.get_asset(character.portrait_id)):
            portrait = asset[0]
        try:
            from app_dnd.pdf.sheet_export import TemplateError, fill_pdf

            warnings = fill_pdf(
                template, target, character, SpellCatalog(self._db.list_custom_spells()), portrait
            )
        except ImportError:
            QMessageBox.warning(self, "Exportar PDF", 'Faltam bibliotecas. Rode:  pip install -e ".[pdf]"')
            return
        except TemplateError as exc:
            QSettings("APP_DND", "APP_DND").remove("pdf/template")
            QMessageBox.warning(self, "Modelo incompatível", str(exc))
            return
        except Exception as exc:
            QMessageBox.warning(self, "Falha ao exportar", str(exc))
            return
        self.statusBar().showMessage(f"Ficha exportada para {target}", 5000)
        if warnings:
            QMessageBox.information(self, "Avisos da exportação", "\n".join(f"• {w}" for w in warnings))

    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Exportar backup", "backup_app_dnd.json", "JSON (*.json)")
        if not path:
            return
        try:
            Path(path).write_text(export_backup(self._db), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "Falha ao exportar", str(exc))
            return
        self.statusBar().showMessage(f"Backup salvo em {path}", 5000)
        self._warn_invalid_characters("O backup não inclui")

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Importar backup", "", "JSON (*.json)")
        if not path:
            return
        try:
            raw = Path(path).read_text(encoding="utf-8")
            result = import_backup(self._db, raw)
            if result.skipped_newer and QMessageBox.question(
                self,
                "Fichas mais novas",
                f"{result.skipped_newer} ficha(s) do arquivo são mais antigas que as salvas e não foram importadas. "
                "Sobrescrever mesmo assim?",
            ) == QMessageBox.Yes:
                result = import_backup(self._db, raw, overwrite_newer=True)
        except (BackupError, OSError, UnicodeDecodeError) as exc:
            QMessageBox.warning(self, "Falha ao importar", str(exc))
            return
        self.spells.reload_catalog()
        self._reload_list()
        self.statusBar().showMessage(f"{result.imported} ficha(s) importada(s)", 5000)
