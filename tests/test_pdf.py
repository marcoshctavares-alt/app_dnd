import os

import pytest

pypdf = pytest.importorskip("pypdf")

from app_dnd.models import AbilityScores, Character, Coins, HitPoints, Profile, SkillProficiencies
from app_dnd.pdf.fieldmap import SPELL_LINES
from app_dnd.pdf.sheet_export import TemplateError, build_sheet_values, fill_pdf, fit_font_size
from app_dnd.services.equipment import add_catalog_item, attack_from_weapon, set_equipped
from app_dnd.services.spells import SpellCatalog, add_spell, cast_spell, set_prepared

CAT = SpellCatalog()
TEMPLATE = os.environ.get("APP_DND_TEMPLATE")


def reidoth(**kw):
    base = dict(
        name="Reidoth", ruleset="dnd-5e-2014", species="Humano", character_class="Druida", level=4,
        abilities=AbilityScores(strength=14, dexterity=11, constitution=13, intelligence=15, wisdom=12, charisma=11),
        hit_points=HitPoints(current=30, maximum=34),
        skills=SkillProficiencies(proficient=["animal-handling", "arcana", "athletics", "insight", "religion"]),
    )
    return Character(**{**base, **kw})


def test_core_numbers_match_official_example_sheet():
    t = build_sheet_values(reidoth()).text
    assert [t[f"{a}-save"] for a in ("str", "dex", "con", "int", "wis", "cha")] == ["+2", "0", "+1", "+4", "+3", "0"]
    assert [t[f"{a}-mod"] for a in ("str", "dex", "con", "int", "wis", "cha")] == ["+2", "0", "+1", "+2", "+1", "0"]
    assert (t["arcana"], t["athletics"], t["animal-handling"], t["history"], t["perception"]) == ("+4", "+4", "+3", "+2", "+1")
    assert (t["prof-bonus"], t["passive"], t["initiative"], t["hd-total"]) == ("+2", "11", "0", "4d8")
    assert t["class-level"] == "Druida (4)" and t["speed"] == "30" and t["hp-max"] == "34"


def test_proficiency_checkboxes():
    checks = build_sheet_values(reidoth()).checks
    assert {"int-save-check", "wis-save-check", "arcana-check", "athletics-check"} <= checks
    assert "str-save-check" not in checks and "history-check" not in checks


def test_empty_values_are_blank_not_zero():
    t = build_sheet_values(reidoth(hit_points=HitPoints(current=5, maximum=5, temporary=0))).text
    assert t["hp-temp"] == "" and t["gp"] == "" and t["attacks-and-spellcasting"] == ""


def test_attacks_overflow_to_free_text_box():
    ch = reidoth()
    for w in ("quarterstaff", "scimitar", "dagger", "sling"):
        attack_from_weapon(ch, w)
    t = build_sheet_values(ch).text
    assert t["weapon-name-3"] == "Adaga" and "weapon-name-4" not in t
    assert t["attacks-and-spellcasting"].startswith("Funda:")


def test_equipment_and_coins_and_ac():
    ch = reidoth(coins=Coins(gp=15))
    set_equipped(ch, add_catalog_item(ch, "leather").id, True)
    t = build_sheet_values(ch).text
    assert "Couro x1 (equipado)" in t["equipment"] and t["gp"] == "15" and t["ac"] == "11"


def test_spells_slots_and_prepared_marks():
    ch = reidoth()
    for sid in ("guidance", "cure-wounds", "healing-word", "hold-person"):
        add_spell(ch, CAT, sid)
    set_prepared(ch, CAT, "cure-wounds", True)
    cast_spell(ch, CAT, "cure-wounds")
    v = build_sheet_values(ch)
    t = v.text
    assert t["spellcasting-ability-1"] == "Sabedoria" and t["spell-save-dc-1"] == "11" and t["spell-attack-bonus-1"] == "+3"
    assert (t["spell-slots-1-1"], t["SlotsRemaining 19"]) == ("4", "1")
    assert (t["spell-slots-2-1"], t["SlotsRemaining 20"]) == ("3", "0")
    assert "spell-slots-3-1" not in t
    assert t[SPELL_LINES[1][0][0]] == "Curar Ferimentos" and t[SPELL_LINES[1][1][0]] == "Palavra Curativa"
    assert t[SPELL_LINES[0][0][0]] == "Orientação"
    assert v.checks & {b for _, b in SPELL_LINES[1] if b} == {SPELL_LINES[1][0][1]}


def test_always_prepared_classes_check_every_spell():
    ch = Character(name="F", ruleset="dnd-5e-2014", character_class="Feiticeiro", level=3,
                   hit_points=HitPoints(current=5, maximum=5))
    add_spell(ch, CAT, "magic-missile")
    add_spell(ch, CAT, "shield")
    v = build_sheet_values(ch)
    assert {SPELL_LINES[1][0][1], SPELL_LINES[1][1][1]} <= v.checks


def test_non_caster_has_no_spell_fields():
    t = build_sheet_values(reidoth(character_class="Guerreiro")).text
    assert "spellcasting-ability-1" not in t and "spell-slots-1-1" not in t


def test_warnings_for_unknown_spell_and_overflow():
    ch = reidoth()
    ch.spells = ch.spells.model_copy(update={"known": ["nao-existe"]})
    assert any("fora do catálogo" in w for w in build_sheet_values(ch).warnings)


def test_fit_font_size_shrinks_for_long_text_and_respects_limits():
    box = (150, 60)
    assert fit_font_size("curto", *box, max_size=10) == 10
    long = "linha de texto bem comprida " * 40
    assert 5 <= fit_font_size(long, *box, max_size=10) < 10


def test_rejects_pdf_that_is_not_the_official_sheet(tmp_path):
    blank = tmp_path / "branco.pdf"
    writer = pypdf.PdfWriter()
    writer.add_blank_page(612, 792)
    writer.write(blank)
    with pytest.raises(TemplateError):
        fill_pdf(blank, tmp_path / "out.pdf", reidoth())


@pytest.mark.skipif(not TEMPLATE or not os.path.isfile(TEMPLATE or ""), reason="defina APP_DND_TEMPLATE com o PDF oficial")
def test_fill_real_template_clears_sample_data_and_keeps_ours(tmp_path):
    out = tmp_path / "ficha.pdf"
    ch = reidoth(name="Aldric Ção", profile=Profile(backstory="História", alignment="Neutro"))
    set_equipped(ch, add_catalog_item(ch, "shield").id, True)
    assert fill_pdf(TEMPLATE, out, ch, CAT) == []

    reader = pypdf.PdfReader(out)
    assert len(reader.pages) == 3
    values = {}
    for page in reader.pages:
        for ref in page.get("/Annots") or []:
            node = ref.get_object()
            while "/T" not in node and "/Parent" in node:
                node = node["/Parent"].get_object()
            if "/T" in node and "/V" in node:
                values[str(node["/T"])] = str(node["/V"])
    assert values["character-name"] == "Aldric Ção" and values["character-name-2"] == "Aldric Ção"
    assert values["alignment"] == "Neutro" and values["class-level"] == "Druida (4)"
    leftovers = [k for k, v in values.items() if "Reidoth" in v or "Illuskan" in v or "Dancing Sword" in v]
    assert leftovers == []
    assert values["weapon-name-1"] == ""


def test_2024_caster_marks_only_prepared_spells():
    ch = Character(name="F", ruleset="dnd-5e-2024", character_class="Feiticeiro", level=3,
                   hit_points=HitPoints(current=5, maximum=5))
    add_spell(ch, CAT, "magic-missile")
    add_spell(ch, CAT, "shield")
    set_prepared(ch, CAT, "magic-missile", True)
    v = build_sheet_values(ch)
    marked = v.checks & {SPELL_LINES[1][0][1], SPELL_LINES[1][1][1]}
    assert len(marked) == 1


def test_species_traits_go_to_features_field():
    ch = Character(name="E", ruleset="dnd-5e-2024", species="Elfo", subrace="Drow", character_class="Guerreiro",
                   hit_points=HitPoints(current=5, maximum=5))
    ch.profile.features = "Nota do jogador"
    text = build_sheet_values(ch).text["features-and-traits"]
    assert "Transe" in text and "Drow:" in text and text.endswith("Nota do jogador")
    ch.subrace = "Inexistente"
    v = build_sheet_values(ch)
    assert any("Inexistente" in w for w in v.warnings)
    assert "Transe" not in v.text["features-and-traits"]
