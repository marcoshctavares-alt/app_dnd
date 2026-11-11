import pytest

from app_dnd.data.spellcasting import SPELLCASTING_2024, cantrips_known, prepared_spells
from app_dnd.models import AbilityScores, Character, HitPoints
from app_dnd.services.spells import SpellCatalog, add_spell, max_cantrips, max_prepared, set_prepared, spell_slots

CLASSES = ["Bardo", "Clérigo", "Druida", "Paladino", "Patrulheiro", "Feiticeiro", "Bruxo", "Mago"]


def make(cls, level, ruleset="dnd-5e-2024"):
    return Character(
        name="T", ruleset=ruleset, character_class=cls, level=level,
        abilities=AbilityScores(intelligence=16, wisdom=16, charisma=16),
        hit_points=HitPoints(current=10, maximum=10),
    )


def test_all_classes_and_levels_present():
    assert sorted(SPELLCASTING_2024) == sorted(CLASSES)
    for cls in CLASSES:
        assert sorted(SPELLCASTING_2024[cls]) == list(range(1, 21))


@pytest.mark.parametrize("cls", CLASSES)
def test_values_never_decrease(cls):
    rows = SPELLCASTING_2024[cls]
    for lvl in range(2, 21):
        assert rows[lvl]["cantrips"] >= rows[lvl - 1]["cantrips"]
        assert rows[lvl]["prepared"] >= rows[lvl - 1]["prepared"]


@pytest.mark.parametrize("cls", [c for c in CLASSES if c != "Bruxo"])
def test_slots_match_service(cls):
    for lvl in range(1, 21):
        parsed = {i + 1: n for i, n in enumerate(SPELLCASTING_2024[cls][lvl]["slots"]) if n}
        assert parsed == dict(spell_slots(cls, lvl, "dnd-5e-2024"))


def test_spot_checks():
    assert (cantrips_known("Bardo", 1), prepared_spells("Bardo", 1)) == (2, 4)
    assert prepared_spells("Bardo", 20) == 22
    assert prepared_spells("Mago", 20) == 25
    assert cantrips_known("Clérigo", 1) == 3 and cantrips_known("Clérigo", 20) == 5
    assert prepared_spells("Paladino", 1) == 2 and prepared_spells("Patrulheiro", 20) == 15
    assert (cantrips_known("Feiticeiro", 1), prepared_spells("Feiticeiro", 1)) == (4, 2)
    assert prepared_spells("Bruxo", 20) == 15
    assert cantrips_known("Guerreiro", 1) is None


def test_service_limits_2024():
    assert max_prepared(make("Mago", 20)) == 25
    assert max_prepared(make("Bardo", 1)) == 4
    assert max_cantrips(make("Clérigo", 1)) == 3
    assert max_cantrips(make("Guerreiro", 5)) is None
    assert max_prepared(make("Guerreiro", 5)) is None


def test_2014_unchanged():
    assert max_cantrips(make("Mago", 5, "dnd-5e-2014")) is None
    assert max_prepared(make("Bardo", 5, "dnd-5e-2014")) is None
    assert max_prepared(make("Mago", 5, "dnd-5e-2014")) == 8


def test_prepared_limit_enforced_2024():
    catalog = SpellCatalog()
    ch = make("Paladino", 1)
    ids = [s.id for s in catalog.search("", 1, "Paladino")][:3]
    for sid in ids:
        ch = add_spell(ch, catalog, sid)
    ch = set_prepared(ch, catalog, ids[0], True)
    ch = set_prepared(ch, catalog, ids[1], True)
    with pytest.raises(ValueError):
        set_prepared(ch, catalog, ids[2], True)
