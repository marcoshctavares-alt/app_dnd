import random

import pytest

from app_dnd.data.backgrounds import BACKGROUNDS_2024, find_background
from app_dnd.data.skills import SKILLS
from app_dnd.data.srd import CLASSES
from app_dnd.models import AbilityScores, Character, HitPoints
from app_dnd.services.backgrounds import SPREAD, ability_choices, apply_background, is_applied
from app_dnd.services.generator import hit_points_for, random_character


def make(ruleset="dnd-5e-2024", **abilities):
    return Character(
        name="Teste", ruleset=ruleset, abilities=AbilityScores(**abilities), hit_points=HitPoints(current=8, maximum=8)
    )


def test_srd_backgrounds_data():
    assert [b.name for b in BACKGROUNDS_2024] == ["Acólito", "Criminoso", "Sábio", "Soldado"]
    for b in BACKGROUNDS_2024:
        assert len(set(b.abilities)) == 3 and all(s in SKILLS for s in b.skills)
    assert find_background("Sábio").skills == ("arcana", "history")
    assert find_background("nada") is None


def test_ability_choices_cover_all_distributions():
    choices = ability_choices(find_background("Soldado"))
    assert len(choices) == 7
    assert choices[SPREAD] == {"strength": 1, "dexterity": 1, "constitution": 1}
    assert choices["+2 Força, +1 Destreza"] == {"strength": 2, "dexterity": 1}


def test_apply_background_changes_scores_skills_and_notes():
    ch = make(strength=14, dexterity=10, constitution=12)
    out = apply_background(ch, "Soldado", {"strength": 2, "constitution": 1})
    assert (out.abilities.strength, out.abilities.constitution, out.abilities.dexterity) == (16, 13, 10)
    assert set(out.skills.proficient) == {"athletics", "intimidation"}
    assert out.profile.background == "Soldado" and "Atacante Selvagem" in out.profile.features
    assert is_applied(out) and not is_applied(ch)
    assert ch.abilities.strength == 14


def test_apply_background_caps_at_20_and_keeps_existing_skills():
    ch = make(strength=19)
    ch = ch.model_copy(update={"skills": ch.skills.model_copy(update={"proficient": ["athletics", "arcana"]})})
    out = apply_background(ch, "Soldado", {"strength": 2, "dexterity": 1})
    assert out.abilities.strength == 20
    assert out.skills.proficient.count("athletics") == 1 and "arcana" in out.skills.proficient


@pytest.mark.parametrize(
    "name,increases,ruleset",
    [
        ("Soldado", {"strength": 2, "dexterity": 1}, "dnd-5e-2014"),
        ("Xamã", {"strength": 1}, "dnd-5e-2024"),
        ("Soldado", {"intelligence": 2, "dexterity": 1}, "dnd-5e-2024"),
        ("Soldado", {"strength": 2, "dexterity": 2}, "dnd-5e-2024"),
        ("Soldado", {"strength": 1}, "dnd-5e-2024"),
    ],
)
def test_apply_background_rejects_invalid(name, increases, ruleset):
    with pytest.raises(ValueError):
        apply_background(make(ruleset), name, increases)


def test_apply_background_twice_is_rejected():
    out = apply_background(make(), "Sábio", {"intelligence": 2, "wisdom": 1})
    with pytest.raises(ValueError):
        apply_background(out, "Sábio", {"intelligence": 2, "wisdom": 1})


def test_random_2024_character_gets_background_and_consistent_hp():
    classes = {c.name: c for c in CLASSES}
    for seed in range(200):
        ch = random_character(rng=random.Random(seed))
        assert find_background(ch.profile.background) and is_applied(ch)
        assert len(ch.skills.proficient) == 2
        expected = hit_points_for(classes[ch.character_class], ch.level, ch.abilities.constitution)
        assert ch.hit_points.maximum == ch.hit_points.current == expected
        assert max(ch.abilities.model_dump().values()) <= 20


def test_random_2014_character_has_no_background():
    ch = random_character(ruleset="dnd-5e-2014", rng=random.Random(1))
    assert ch.profile.background == "" and not ch.skills.proficient
