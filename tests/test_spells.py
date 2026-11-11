import json

import pytest
from pydantic import ValidationError

from app_dnd.backup import export_backup, import_backup
from app_dnd.models import AbilityScores, Character, HitPoints, SpellBook
from app_dnd.services.spells import (
    SpellCatalog,
    add_spell,
    cast_spell,
    load_spell_pack,
    long_rest,
    max_prepared,
    remaining_slots,
    remove_spell,
    set_prepared,
    short_rest,
    spell_slots,
    spend_slot,
    format_spell,
    spellcasting_stats,
)
from app_dnd.storage import Database

R14, R24 = "dnd-5e-2014", "dnd-5e-2024"
CAT = SpellCatalog()


def make(cls="Mago", level=5, ruleset=R14, **abilities):
    return Character(
        name="T", ruleset=ruleset, character_class=cls, level=level,
        abilities=AbilityScores(**abilities), hit_points=HitPoints(current=5, maximum=5),
    )


@pytest.mark.parametrize(
    "level,expected",
    [(1, {1: 2}), (3, {1: 4, 2: 2}), (5, {1: 4, 2: 3, 3: 2}), (9, {1: 4, 2: 3, 3: 3, 4: 3, 5: 1}),
     (17, {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1, 9: 1}),
     (20, {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 2, 8: 1, 9: 1})],
)
def test_full_caster_slots(level, expected):
    assert spell_slots("Mago", level) == expected


def test_full_caster_totals_never_decrease():
    for lvl in range(1, 20):
        a, b = spell_slots("Clérigo", lvl), spell_slots("Clérigo", lvl + 1)
        assert all(b.get(k, 0) >= v for k, v in a.items())


def test_half_caster_slots_and_ruleset_difference():
    assert spell_slots("Paladino", 1, R14) == {}
    assert spell_slots("Paladino", 1, R24) == {1: 2}
    assert spell_slots("Patrulheiro", 5) == {1: 4, 2: 2}
    assert spell_slots("Paladino", 20) == {1: 4, 2: 3, 3: 3, 4: 3, 5: 2}


@pytest.mark.parametrize("level,expected", [(1, {1: 1}), (2, {1: 2}), (3, {2: 2}), (5, {3: 2}), (11, {5: 3}), (17, {5: 4})])
def test_pact_magic(level, expected):
    assert spell_slots("Bruxo", level) == expected


def test_non_casters():
    assert spell_slots("Guerreiro", 10) == {} and spell_slots(None, 5) == {}
    assert spell_slots("Mago", 0) == {}


def test_spellcasting_stats():
    ch = make("Mago", 5, intelligence=16)
    assert spellcasting_stats(ch) == {"ability": "intelligence", "save_dc": 14, "attack_bonus": 6}
    assert spellcasting_stats(make("Guerreiro")) is None


def test_max_prepared_2014_formula():
    assert max_prepared(make("Mago", 5, intelligence=16)) == 8
    assert max_prepared(make("Paladino", 5, charisma=14)) == 4
    assert max_prepared(make("Mago", 1, intelligence=3)) == 1
    assert max_prepared(make("Feiticeiro", 5)) is None
    assert max_prepared(make("Mago", 5, R24, intelligence=16)) == 9


def test_catalog_search_ignores_accents_and_case():
    assert [s.id for s in CAT.search("bencao")] == ["bless"]
    assert {"fireball", "delayed-blast-fireball"} <= {s.id for s in CAT.search("FIREBALL")}
    assert all(s.level == 0 for s in CAT.search(level=0))
    assert all("Bruxo" in s.classes for s in CAT.search(class_name="Bruxo"))


def test_pack_import_and_catalog_merge():
    raw = json.dumps({"spells": [{
        "id": "minha-magia", "name": "Minha Magia", "level": 2, "school": "Evocação",
        "casting_time": "1 ação", "range": "30 pés", "components": "V", "duration": "Instantânea",
    }]})
    spells = load_spell_pack(raw)
    cat = SpellCatalog(spells)
    assert cat.get("minha-magia").source == "custom"


@pytest.mark.parametrize("raw", ["xx", "5", json.dumps([{"id": "Bad Id!"}]),
                                  json.dumps([{"id": "fireball", "name": "x", "level": 3, "school": "s",
                                               "casting_time": "a", "range": "b", "components": "c", "duration": "d"}])])
def test_pack_rejects_bad_input(raw):
    with pytest.raises(ValueError):
        load_spell_pack(raw)


def test_custom_cannot_override_srd():
    from app_dnd.models import Spell
    fake = Spell(id="fireball", name="Falsa", level=1, school="x", casting_time="a", range="b", components="c", duration="d")
    assert SpellCatalog([fake]).get("fireball").name == "Bola de Fogo"


def test_add_remove_and_prepare():
    ch = make("Mago", 5, intelligence=16)
    add_spell(ch, CAT, "magic-missile")
    add_spell(ch, CAT, "fire-bolt")
    with pytest.raises(ValueError):
        add_spell(ch, CAT, "magic-missile")
    with pytest.raises(ValueError):
        add_spell(ch, CAT, "nao-existe")
    set_prepared(ch, CAT, "magic-missile", True)
    assert ch.spells.prepared == ["magic-missile"]
    with pytest.raises(ValueError):
        set_prepared(ch, CAT, "fire-bolt", True)
    remove_spell(ch, "magic-missile")
    assert ch.spells.known == ["fire-bolt"] and ch.spells.prepared == []


def test_prepared_limit_enforced():
    ch = make("Mago", 1, intelligence=10)
    for sid in ("magic-missile", "shield"):
        add_spell(ch, CAT, sid)
    set_prepared(ch, CAT, "magic-missile", True)
    with pytest.raises(ValueError, match="Limite"):
        set_prepared(ch, CAT, "shield", True)


def test_spellbook_model_rules():
    with pytest.raises(ValidationError):
        SpellBook(known=["a"], prepared=["b"])
    with pytest.raises(ValidationError):
        SpellBook(known=["a", "a"])
    with pytest.raises(ValidationError):
        SpellBook(slots_used={10: 1})
    with pytest.raises(ValidationError):
        SpellBook(slots_used={1: -1})


def test_cast_spends_slots_and_runs_out():
    ch = make("Mago", 1)
    add_spell(ch, CAT, "magic-missile")
    add_spell(ch, CAT, "fire-bolt")
    assert "truque" in cast_spell(ch, CAT, "fire-bolt")
    assert remaining_slots(ch) == {1: (2, 2)}
    cast_spell(ch, CAT, "magic-missile")
    cast_spell(ch, CAT, "magic-missile")
    assert remaining_slots(ch) == {1: (0, 2)}
    with pytest.raises(ValueError, match="Sem espaços"):
        cast_spell(ch, CAT, "magic-missile")


def test_upcast_and_invalid_levels():
    ch = make("Mago", 5)
    add_spell(ch, CAT, "magic-missile")
    cast_spell(ch, CAT, "magic-missile", slot_level=3)
    assert remaining_slots(ch)[3] == (1, 2) and remaining_slots(ch)[1] == (4, 4)
    with pytest.raises(ValueError):
        cast_spell(ch, CAT, "fireball")
    add_spell(ch, CAT, "fireball")
    with pytest.raises(ValueError):
        cast_spell(ch, CAT, "fireball", slot_level=2)
    with pytest.raises(ValueError):
        cast_spell(ch, CAT, "magic-missile", slot_level=7)


def test_non_caster_cannot_cast_leveled_spell():
    ch = make("Guerreiro")
    add_spell(ch, CAT, "magic-missile")
    with pytest.raises(ValueError):
        cast_spell(ch, CAT, "magic-missile")


def test_warlock_pact_slots_and_short_rest():
    ch = make("Bruxo", 3)
    for sid in ("hex", "hold-person", "fireball"):
        add_spell(ch, CAT, sid)
    cast_spell(ch, CAT, "hex")
    cast_spell(ch, CAT, "hold-person")
    assert remaining_slots(ch) == {2: (0, 2)}
    with pytest.raises(ValueError):
        cast_spell(ch, CAT, "fireball")
    short_rest(ch)
    assert remaining_slots(ch) == {2: (2, 2)}


def test_short_rest_does_not_restore_other_casters_but_long_does():
    ch = make("Mago", 3)
    add_spell(ch, CAT, "magic-missile")
    cast_spell(ch, CAT, "magic-missile")
    short_rest(ch)
    assert remaining_slots(ch)[1] == (3, 4)
    long_rest(ch)
    assert remaining_slots(ch)[1] == (4, 4)


def test_level_up_changes_totals_and_keeps_used():
    ch = make("Mago", 1)
    add_spell(ch, CAT, "magic-missile")
    cast_spell(ch, CAT, "magic-missile")
    ch.level = 3
    assert remaining_slots(ch) == {1: (3, 4), 2: (2, 2)}


def test_spells_persist_and_roundtrip_json_keys():
    db = Database(":memory:")
    ch = make("Mago", 3)
    add_spell(ch, CAT, "magic-missile")
    cast_spell(ch, CAT, "magic-missile")
    db.save_character(ch)
    loaded = db.get_character(ch.id)
    assert loaded.spells == ch.spells and loaded.spells.slots_used == {1: 1}


def test_backup_includes_custom_spells():
    src = Database(":memory:")
    pack = load_spell_pack(json.dumps([{
        "id": "x-magia", "name": "X", "level": 1, "school": "s",
        "casting_time": "a", "range": "b", "components": "c", "duration": "d"}]))
    src.save_custom_spell(pack[0])
    dst = Database(":memory:")
    import_backup(dst, export_backup(src))
    assert [s.id for s in dst.list_custom_spells()] == ["x-magia"]
    src.delete_custom_spell("x-magia")
    assert src.list_custom_spells() == []


def test_old_character_json_without_spells_loads():
    ch = Character.model_validate_json('{"name":"V","ruleset":"dnd-5e-2014","hit_points":{"current":5,"maximum":5}}')
    assert ch.spells == SpellBook()


def test_manual_spend_slot():
    ch = make("Mago", 1)
    spend_slot(ch, 1)
    spend_slot(ch, 1)
    with pytest.raises(ValueError):
        spend_slot(ch, 1)
    with pytest.raises(ValueError):
        spend_slot(ch, 5)


def test_format_spell_contains_key_facts():
    text = format_spell(CAT.get("detect-magic"))
    assert "ritual" in text and "concentração" in text and "Alcance: Pessoal" in text
    assert "1º nível de Adivinhação" in text
    assert "Truque" in format_spell(CAT.get("fire-bolt"))
