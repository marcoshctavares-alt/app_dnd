import random

import pytest

from app_dnd.data.races import RACES_2014, SPECIES_2024, find_race, races_for
from app_dnd.models import AbilityScores
from app_dnd.services.generator import random_character
from app_dnd.services.races import apply_racial_bonuses, describe_race, racial_bonuses

R14, R24 = "dnd-5e-2014", "dnd-5e-2024"


def test_srd_2014_has_nine_races_and_four_subraces():
    assert len(RACES_2014) == 9
    assert sum(len(r.subraces) for r in RACES_2014) == 4
    assert len(SPECIES_2024) == 9


def test_bonuses_race_plus_subrace():
    assert racial_bonuses(R14, "Anão", "Anão da Colina") == {"constitution": 2, "wisdom": 1}
    assert racial_bonuses(R14, "Elfo", "Elfo Alto") == {"dexterity": 2, "intelligence": 1}


def test_human_gets_plus_one_everywhere():
    assert sorted(racial_bonuses(R14, "Humano").values()) == [1] * 6


def test_half_elf_free_choices():
    b = racial_bonuses(R14, "Meio-elfo", None, ["strength", "wisdom"])
    assert b == {"charisma": 2, "strength": 1, "wisdom": 1}


@pytest.mark.parametrize(
    "choices", [[], ["strength"], ["strength", "strength"], ["charisma", "wisdom"], ["luck", "wisdom"]]
)
def test_half_elf_invalid_choices(choices):
    with pytest.raises(ValueError):
        racial_bonuses(R14, "Meio-elfo", None, choices)


def test_free_choices_rejected_for_other_races():
    with pytest.raises(ValueError):
        racial_bonuses(R14, "Anão", None, ["strength", "wisdom"])


def test_no_racial_bonus_in_2024_or_unknown_species():
    assert racial_bonuses(R24, "Anão") == {}
    assert racial_bonuses(R14, "Aarakocra") == {}
    assert racial_bonuses(R14, None) == {}


def test_subrace_must_belong_to_race():
    with pytest.raises(ValueError):
        racial_bonuses(R14, "Anão", "Elfo Alto")


def test_apply_bonuses_caps_at_20():
    base = AbilityScores(constitution=19, wisdom=10)
    result = apply_racial_bonuses(base, {"constitution": 2, "wisdom": 1})
    assert result.constitution == 20 and result.wisdom == 11


def test_describe_race():
    assert "Constituição +2" in describe_race(R14, "Anão", "Anão da Colina")
    assert "Sabedoria +1" in describe_race(R14, "Anão", "Anão da Colina")
    assert "antecedente" in describe_race(R24, "Anão")
    assert describe_race(R14, None) == ""


def test_find_and_list():
    assert find_race(R14, "Gnomo").size == "Pequeno"
    assert find_race(R14, "Golias") is None and find_race(R24, "Golias") is not None
    assert races_for(R14) is RACES_2014


def test_generated_2014_characters_are_consistent():
    for seed in range(300):
        ch = random_character(ruleset=R14, rng=random.Random(seed))
        race = find_race(R14, ch.species)
        assert race is not None
        assert (ch.subrace is not None) == bool(race.subraces)
        if ch.subrace:
            race.subrace(ch.subrace)
        assert all(1 <= v <= 20 for v in ch.abilities.model_dump().values())


def test_generated_2014_applies_bonuses():
    higher = 0
    for seed in range(100):
        ch = random_character(level=1, ruleset=R14, rng=random.Random(seed))
        if ch.species == "Humano":
            assert min(ch.abilities.model_dump().values()) >= 4
            higher += 1
    assert higher > 0


def test_generated_2024_subrace_matches_species():
    for seed in range(100):
        ch = random_character(ruleset=R24, rng=random.Random(seed))
        race = find_race(R24, ch.species)
        assert (ch.subrace is None) == (not race.subraces)
        if ch.subrace:
            race.subrace(ch.subrace)


def test_old_backup_without_subrace_still_loads():
    from app_dnd.models import Character

    ch = Character.model_validate_json(
        '{"name":"Velho","ruleset":"dnd-5e-2014","hit_points":{"current":5,"maximum":5}}'
    )
    assert ch.subrace is None


def test_2024_lineages_from_srd():
    names = {r.name: [s.name for s in r.subraces] for r in SPECIES_2024}
    assert len(names["Draconato"]) == 10 and len(names["Golias"]) == 6
    assert names["Elfo"] == ["Drow", "Alto Elfo", "Elfo da Floresta"]
    assert names["Gnomo"] == ["Gnomo da Floresta", "Gnomo das Rochas"]
    assert names["Tiefling"] == ["Abissal", "Ctônico", "Infernal"]
    for plain in ("Anão", "Halfling", "Humano", "Orc"):
        assert names[plain] == []
    assert all(r.traits for r in SPECIES_2024)


def test_wood_elf_speed_and_labels():
    from app_dnd.data.races import lineage_label
    from app_dnd.models import Character, HitPoints
    from app_dnd.services.skills import speed

    def make(sub):
        return Character(name="E", ruleset=R24, species="Elfo", subrace=sub, hit_points=HitPoints(current=5, maximum=5))

    assert speed(make("Elfo da Floresta")) == 35
    assert speed(make("Drow")) == 30 and speed(make(None)) == 30
    assert lineage_label(R24, "Elfo") == "Linhagem élfica"
    assert lineage_label(R24, "Humano") == "Sub-raça"
    assert lineage_label("dnd-5e-2014", "Elfo") == "Sub-raça"


def test_species_traits_include_lineage():
    from app_dnd.services.races import describe_race, species_traits

    lines = species_traits(R24, "Tiefling", "Infernal")
    assert any("Presença Sobrenatural" in t for t in lines) and any(t.startswith("Infernal:") for t in lines)
    assert species_traits("dnd-5e-2014", "Anão") == []
    assert "35 pés" in describe_race(R24, "Elfo", "Elfo da Floresta")
