import importlib.util
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

REAL_QT = importlib.util.find_spec("PySide6") is not None
TEMPLATE = os.environ.get("APP_DND_TEMPLATE")

pytestmark = pytest.mark.skipif(REAL_QT, reason="PySide6 real instalado: rode o app para testar a interface")


@pytest.fixture()
def ui(tmp_path):
    import qt_stub

    qt_stub.install()
    from app_dnd.storage import Database
    from app_dnd.ui import attacks_widget, equipment_widget, main_window, sheet_widget, spells_widget

    qt_stub.QMessageBox.shown.clear()
    qt_stub.QSettings.store.clear()
    qt_stub.QDialog.exec_result = 0
    db = Database(tmp_path / "t.db")
    yield SimpleNamespace(
        qt=qt_stub, db=db, mw=main_window, sw=sheet_widget, ew=equipment_widget, aw=attacks_widget,
        spw=spells_widget, tmp=tmp_path,
    )
    db.close()
    qt_stub.uninstall()


def build_caster(ui):
    win = ui.mw.MainWindow(ui.db)
    win._new()
    sheet = win.sheet
    sheet.char_class.setCurrentIndex(sheet.char_class.findData("Mago"))
    sheet.level.setValue(5)
    for spin in sheet.ability_spins.values():
        spin.setValue(12)
    sheet.ability_spins["strength"].setValue(12)
    sheet._save()
    return win


def test_all_ui_modules_import(ui):
    assert ui.mw.MainWindow and ui.sw.SheetWidget and ui.ew.EquipmentWidget and ui.aw.AttacksWidget and ui.spw.SpellsWidget


def test_random_and_new_characters_load_without_warnings(ui):
    win = ui.mw.MainWindow(ui.db)
    for _ in range(5):
        win._random()
    assert len(ui.db.list_characters()) == 5
    for ruleset in ("dnd-5e-2014", "dnd-5e-2024"):
        win._new()
        win.sheet.ruleset.setCurrentIndex(win.sheet.ruleset.findData(ruleset))
        assert win.sheet.current_character() is not None
    assert not ui.qt.QMessageBox.shown, ui.qt.QMessageBox.shown


def test_sheet_edit_is_saved_and_other_tabs_follow(ui):
    win = build_caster(ui)
    saved = ui.db.list_characters()[0]
    assert (saved.character_class, saved.level) == ("Mago", 5)
    assert win.spells._character.level == 5 and win.attacks._character.level == 5 and win.equipment._character.level == 5
    assert not ui.qt.QMessageBox.shown, ui.qt.QMessageBox.shown


def test_equipment_armor_warning_and_speed(ui):
    win = build_caster(ui)
    ui.ew.CatalogPickerDialog.exec_result = 1
    ui.ew.CatalogPickerDialog.selected_id = lambda self: "plate"
    ui.qt.QDialog.exec_result = 1
    win.equipment._add_catalog()
    win.equipment.list.setCurrentRow(0)
    win.equipment._toggle_equipped()
    summary = win.equipment.summary.text()
    assert "Força 15" in summary and "Furtividade" in summary
    assert ui.db.list_characters()[0].inventory[0].equipped
    assert not ui.qt.QMessageBox.shown, ui.qt.QMessageBox.shown


def test_off_hand_attack_flow(ui):
    win = build_caster(ui)
    ui.qt.QDialog.exec_result = 1
    ui.aw.WeaponPickerDialog.selected = lambda self: ("handaxe", False, True, False)
    win.attacks._add_weapon()
    assert win.attacks.list.count() == 1
    assert "[ação bônus]" in win.attacks.list.item(0).text()
    win.attacks.list.setCurrentRow(0)
    messages = []
    win.attacks.message.connect(messages.append)
    win.attacks._attack()
    win.attacks._damage(False)
    win.attacks._damage(True)
    assert len(messages) == 3
    assert ui.db.list_characters()[0].attacks[0].off_hand
    assert not ui.qt.QMessageBox.shown, ui.qt.QMessageBox.shown


def test_spells_flow_and_rollback_on_error(ui):
    win = build_caster(ui)
    ui.qt.QDialog.exec_result = 1
    ui.spw.SpellPickerDialog.selected_ids = lambda self: ["magic-missile", "shield", "fire-bolt"]
    win.spells._add()
    assert len(ui.db.list_characters()[0].spells.known) == 3
    assert "Preparadas: 0/" in win.spells.stats.text() or "Preparadas" not in win.spells.stats.text()
    ui.spw.SpellPickerDialog.selected_ids = lambda self: ["detect-magic", "nao-existe"]
    before = list(win.spells._character.spells.known)
    win.spells._add()
    assert win.spells._character.spells.known == before
    assert ui.qt.QMessageBox.shown and ui.qt.QMessageBox.shown[-1][1] == "Magias"
    ui.qt.QMessageBox.shown.clear()
    win.spells.list.setCurrentRow(1)
    win.spells._toggle_prepared()
    win.spells._details()
    win.spells._spend()
    assert not ui.qt.QMessageBox.shown, ui.qt.QMessageBox.shown


def test_spell_details_dialog_offers_original_text(ui):
    ui.qt.QDialog.exec_result = 0
    dialog = ui.spw.SpellDetailsDialog("Bola de Fogo", "texto pt", "text en")
    assert dialog is not None


@pytest.mark.skipif(not TEMPLATE, reason="defina APP_DND_TEMPLATE para testar o PDF")
def test_export_pdf_from_window(ui):
    win = build_caster(ui)
    target = ui.tmp / "ficha.pdf"
    ui.qt.QSettings.store["pdf/template"] = TEMPLATE
    ui.qt.QFileDialog.next_save = (str(target), "")
    win._export_pdf()
    assert target.exists() and target.stat().st_size > 10000
    assert not [m for m in ui.qt.QMessageBox.shown if m[0] != "information"], ui.qt.QMessageBox.shown


@pytest.mark.parametrize("screen", [(800, 600), (1366, 768), (1920, 1080), (3840, 2160)])
def test_window_fits_any_screen(ui, screen):
    ui.qt.SCREEN[:] = [0, 0, *screen]
    win = ui.mw.MainWindow(ui.db)
    width, height = win.width(), win.height()
    assert width <= screen[0] * 0.9 and height <= screen[1] * 0.9
    assert win._min_size[0] <= width and win._min_size[1] <= height
    x, y = win._pos
    assert 0 <= x and x + width <= screen[0] and 0 <= y and y + height <= screen[1]
    ui.qt.SCREEN[:] = [0, 0, 1366, 768]


def test_every_tab_is_scrollable(ui):
    win = ui.mw.MainWindow(ui.db)
    inner = [win.tabs.widget(i).inner for i in range(win.tabs.count())]
    assert inner == [win.sheet, win.attacks, win.equipment, win.feats, win.features, win.rest, win.spells]


@pytest.mark.parametrize("screen,bottom", [(1024, True), (1366, False), (1920, False)])
def test_dice_dock_follows_screen_width(ui, screen, bottom):
    ui.qt.SCREEN[:] = [0, 0, screen, 768]
    win = ui.mw.MainWindow(ui.db)
    assert (win.dock_area == ui.qt.Namespace().BottomDockWidgetArea) is bottom
    ui.qt.SCREEN[:] = [0, 0, 1366, 768]


def test_sheet_reflows_between_one_and_two_columns(ui):
    win = ui.mw.MainWindow(ui.db)
    sheet = win.sheet
    assert sheet._wide is False
    sheet.resize(1400, 800)
    sheet.resizeEvent(None)
    assert sheet._wide is True
    sheet.resize(700, 800)
    sheet.resizeEvent(None)
    assert sheet._wide is False
    sheet.resize(900, 800)
    sheet.resizeEvent(None)
    assert sheet._wide is False


def test_dialogs_fit_small_screens(ui):
    ui.qt.SCREEN[:] = [0, 0, 800, 600]
    dialog = ui.spw.SpellDetailsDialog("t", "a", "b")
    assert dialog.width() <= 800 * 0.9 and dialog.height() <= 600 * 0.9
    picker = ui.spw.SpellPickerDialog(ui.spw.SpellCatalog(), "Mago", set())
    assert picker.height() <= 600 * 0.9
    ui.qt.SCREEN[:] = [0, 0, 1366, 768]


def test_class_and_subclass_are_dropdowns_like_species(ui):
    win = ui.mw.MainWindow(ui.db)
    win._new()
    sheet = win.sheet
    assert sheet.char_class.count() == 13
    assert sheet.char_class.itemData(0) is None
    sheet.ruleset.setCurrentIndex(sheet.ruleset.findData("dnd-5e-2014"))
    sheet.char_class.setCurrentIndex(sheet.char_class.findData("Feiticeiro"))
    assert sheet.subclass.count() == 2
    assert sheet.subclass.itemText(1) == "Linhagem Dracônica (nível 1)"
    sheet.ruleset.setCurrentIndex(sheet.ruleset.findData("dnd-5e-2024"))
    assert sheet.subclass.itemText(1) == "Feitiçaria Dracônica (nível 3)"
    sheet.subclass.setCurrentIndex(1)
    assert sheet.current_character().subclass == "Feitiçaria Dracônica"
    sheet.char_class.setCurrentIndex(sheet.char_class.findData("Guerreiro"))
    assert sheet.subclass.currentData() is None
    assert sheet.current_character().character_class == "Guerreiro"
    assert not ui.qt.QMessageBox.shown, ui.qt.QMessageBox.shown


def test_saved_custom_class_and_subclass_are_preserved(ui):
    win = ui.mw.MainWindow(ui.db)
    win._new()
    ch = win.sheet.current_character().model_copy(update={"character_class": "Artífice", "subclass": "Alquimista"})
    win.sheet.load(ch)
    assert win.sheet.char_class.currentText() == "Artífice (personalizada)"
    assert win.sheet.subclass.currentText() == "Alquimista (personalizada)"
    out = win.sheet.current_character()
    assert (out.character_class, out.subclass) == ("Artífice", "Alquimista")


def test_loading_a_character_selects_its_class_and_subclass(ui):
    win = ui.mw.MainWindow(ui.db)
    win._new()
    ch = win.sheet.current_character().model_copy(update={"character_class": "Clérigo", "subclass": "Domínio da Vida"})
    win.sheet.load(ch)
    assert win.sheet.char_class.currentData() == "Clérigo"
    assert win.sheet.subclass.currentData() == "Domínio da Vida"
    assert win.sheet.save_labels["wisdom"].text().startswith("●")


def test_startup_warns_about_invalid_characters_and_still_lists_the_rest(ui):
    from uuid import uuid4

    win = ui.mw.MainWindow(ui.db)
    win._new()
    ui.db._conn.execute(
        "INSERT INTO characters VALUES (?,?,?,?,?)", (str(uuid4()), "X", "dnd-5e-2024", "2026-01-01T00:00:00+00:00", "{}")
    )
    ui.db._conn.commit()
    ui.qt.QMessageBox.shown.clear()
    win2 = ui.mw.MainWindow(ui.db)
    assert win2.list.count() == 1
    assert any(kind == "warning" and title == "Fichas inválidas" for kind, title, _ in ui.qt.QMessageBox.shown)


def test_import_backup_asks_before_overwriting_newer_characters(ui):
    win = build_caster(ui)
    target = ui.tmp / "backup.json"
    ui.qt.QFileDialog.next_save = (str(target), "")
    win._export()
    assert target.exists()
    saved = ui.db.list_characters()[0]
    saved.name = "Editada depois"
    ui.db.save_character(saved)
    ui.qt.QMessageBox.shown.clear()
    ui.qt.QFileDialog.next_open = (str(target), "")
    win._import()
    assert [k for k, t, _ in ui.qt.QMessageBox.shown] == ["question"]
    assert ui.db.list_characters()[0].name != "Editada depois"


def test_import_backup_with_bad_image_shows_a_message_instead_of_crashing(ui):
    import base64
    import json

    win = build_caster(ui)
    payload = json.loads(ui.mw.export_backup(ui.db))
    payload["assets"] = [{"id": "00000000-0000-0000-0000-000000000001", "mime_type": "text/html",
                          "data_b64": base64.b64encode(b"<b>").decode()}]
    bad = ui.tmp / "ruim.json"
    bad.write_text(json.dumps(payload), encoding="utf-8")
    ui.qt.QMessageBox.shown.clear()
    ui.qt.QFileDialog.next_open = (str(bad), "")
    win._import()
    assert [(k, t) for k, t, _ in ui.qt.QMessageBox.shown] == [("warning", "Falha ao importar")]


def test_export_backup_reports_write_errors(ui):
    win = build_caster(ui)
    ui.qt.QFileDialog.next_save = (str(ui.tmp / "nao_existe" / "b.json"), "")
    ui.qt.QMessageBox.shown.clear()
    win._export()
    assert [(k, t) for k, t, _ in ui.qt.QMessageBox.shown] == [("warning", "Falha ao exportar")]


def test_theme_menu_applies_and_persists_choice(ui):
    from app_dnd.ui import theme

    app = ui.qt.QApplication([])
    win = ui.mw.MainWindow(ui.db)
    assert set(win.theme_actions) == {theme.SYSTEM, theme.LIGHT, theme.DARK}
    assert win.theme_actions[theme.SYSTEM].isChecked()
    win.theme_actions[theme.DARK].trigger()
    assert app.style_name == "Fusion" and app.palette() != "default-palette"
    assert theme.saved_mode() == theme.DARK
    win.theme_actions[theme.SYSTEM].trigger()
    assert app.style_name == "windowsvista" and app.palette() == "default-palette"
    assert theme.saved_mode() == theme.SYSTEM


def _luminance(color):
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a, b):
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_theme_palettes_are_readable(ui):
    from app_dnd.ui import theme

    for mode in (theme.LIGHT, theme.DARK):
        colors, _ = theme.palette_colors(mode)
        assert all(len(v) == 7 and v.startswith("#") for v in colors.values())
        for fg, bg in (("WindowText", "Window"), ("Text", "Base"), ("ButtonText", "Button"),
                       ("HighlightedText", "Highlight"), ("Link", "Base")):
            assert _contrast(colors[fg], colors[bg]) >= 4.5, (mode, fg, bg)
        assert _contrast(theme.ERROR_COLOR, colors["Base"]) >= 3.5, mode
    assert theme.palette_colors(theme.SYSTEM) is None
    assert theme.normalize("lixo") == theme.SYSTEM


def test_apply_background_from_sheet(ui):
    win = ui.mw.MainWindow(ui.db)
    win._new()
    sheet = win.sheet
    before = sheet.current_character()
    ui.qt.QInputDialog.answers[:] = ["Sábio", "+2 Inteligência, +1 Sabedoria"]
    sheet._choose_background()
    saved = ui.db.list_characters()[0]
    assert saved.profile.background == "Sábio"
    assert saved.abilities.intelligence == min(20, before.abilities.intelligence + 2)
    assert {"arcana", "history"} <= set(saved.skills.proficient)
    sheet._choose_background()
    assert "já tem o antecedente" in str(ui.qt.QMessageBox.shown[-1])


def test_apply_background_refused_for_2014(ui):
    win = ui.mw.MainWindow(ui.db)
    win._new()
    win.sheet.ruleset.setCurrentIndex(win.sheet.ruleset.findData("dnd-5e-2014"))
    ui.qt.QInputDialog.answers[:] = ["Sábio"]
    win.sheet._choose_background()
    assert ui.qt.QInputDialog.answers == ["Sábio"]
    assert not ui.db.list_characters()[0].profile.background


def test_feats_tab_add_remove_and_sheet_keeps_feats(ui):
    win = ui.mw.MainWindow(ui.db)
    win._new()
    ui.qt.QInputDialog.answers[:] = ["Alerta [Origem]"]
    win.feats._add()
    assert ui.db.list_characters()[0].feats == ["Alerta"]
    win.sheet._save()
    assert ui.db.list_characters()[0].feats == ["Alerta"]
    win.feats.list.setCurrentRow(0)
    win.feats._remove()
    assert ui.db.list_characters()[0].feats == []


def test_feats_tab_blocks_2014(ui):
    win = ui.mw.MainWindow(ui.db)
    win._new()
    win.sheet.ruleset.setCurrentIndex(win.sheet.ruleset.findData("dnd-5e-2014"))
    win.sheet._save()
    ui.qt.QInputDialog.answers[:] = ["Alerta [Origem]"]
    win.feats._add()
    assert ui.qt.QInputDialog.answers == ["Alerta [Origem]"]
    assert not ui.db.list_characters()[0].feats


def test_feat_increase_updates_sheet_and_survives_save(ui):
    win = ui.mw.MainWindow(ui.db)
    win._new()
    win.sheet.level.setValue(4)
    win.sheet._save()
    before = ui.db.list_characters()[0].abilities.strength
    ui.qt.QInputDialog.answers[:] = ["Aumento de Atributo [Geral]", "+2 Força"]
    win.feats._add()
    assert ui.db.list_characters()[0].abilities.strength == before + 2
    assert win.sheet.ability_spins["strength"].value() == before + 2
    win.sheet._save()
    assert ui.db.list_characters()[0].abilities.strength == before + 2


def test_features_tab_lists_class_and_subclass_features_with_locks(ui):
    win = ui.mw.MainWindow(ui.db)
    win._new()
    win.sheet.level.setValue(3)
    win.sheet.char_class.setCurrentIndex(win.sheet.char_class.findData("Guerreiro"))
    win.sheet.subclass.setCurrentIndex(win.sheet.subclass.findData("Campeão"))
    win.sheet._save()
    texts = [win.features.list.item(i).text() for i in range(win.features.list.count())]
    assert texts[0] == "Nível 1 — Estilo de Luta"
    assert "Nível 3 — Subclasse: Crítico Aprimorado" in texts
    assert "Nível 5 — Ataque Extra  (bloqueada)" in texts
    assert texts[-1].endswith("Sobrevivente  (bloqueada)") or "(bloqueada)" in texts[-1]
    win.features.list.setCurrentRow(texts.index("Nível 3 — Subclasse: Crítico Aprimorado"))
    assert "19 ou 20" in win.features.details.text()
    win.features.list.setCurrentRow(0)
    assert "Fighting Style" in win.features.details.text() and "talento de Estilo de Luta" in win.features.details.text()


def test_rest_tab_uses_resources_and_long_rest_updates_sheet_hp(ui):
    win = ui.mw.MainWindow(ui.db)
    win._new()
    win.sheet.char_class.setCurrentIndex(win.sheet.char_class.findData("Guerreiro"))
    win.sheet.hp_current.setValue(1)
    win.sheet._save()
    assert "Retomar o Fôlego: 2/2" in win.rest.list.item(0).text()
    win.rest.list.setCurrentRow(0)
    win.rest._use()
    assert ui.db.list_characters()[0].resources_used == {"second-wind": 1}
    assert "1/2" in win.rest.list.item(0).text()
    win.rest._spend_die()
    assert ui.db.list_characters()[0].hit_dice_used == 1
    win.rest._long()
    saved = ui.db.list_characters()[0]
    assert saved.hit_points.current == saved.hit_points.maximum and saved.resources_used == {}
    assert win.sheet.hp_current.value() == saved.hit_points.maximum
    win.sheet._save()
    assert ui.db.list_characters()[0].hit_points.current == saved.hit_points.maximum
