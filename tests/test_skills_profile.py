import pytest
from pydantic import ValidationError

from app_dnd.data.skills import CLASS_SAVES, SKILLS
from app_dnd.dice import Advantage
from app_dnd.models import AbilityScores, Character, HitPoints, Profile, SkillProficiencies
from app_dnd.services.skills import (
    initiative,
    passive_perception,
    roll_save,
    roll_skill,
    save_bonus,
    saves_for,
    skill_bonus,
    skill_bonus_value,
    speed,
)
from tests.test_dice import FixedRng


def make(cls="Druida", level=4, **kw):
    ab = kw.pop("abilities", {})
    return Character(name="T", ruleset="dnd-5e-2014", character_class=cls, level=level,
                     abilities=AbilityScores(**ab), hit_points=HitPoints(current=5, maximum=5), **kw)


def test_data_integrity():
    assert len(SKILLS) == 18 and len(CLASS_SAVES) == 12
    assert all(len(set(v)) == 2 for v in CLASS_SAVES.values())


def test_reidoth_sheet_numbers_match_official_example():
    ch = make(abilities=dict(strength=14, dexterity=11, constitution=13, intelligence=15, wisdom=12, charisma=11),
              skills=SkillProficiencies(proficient=["animal-handling", "arcana", "athletics", "insight", "religion"]))
    assert [save_bonus(ch, a) for a in ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma")] == [2, 0, 1, 4, 3, 0]
    assert skill_bonus(ch, "animal-handling") == 3 and skill_bonus(ch, "arcana") == 4
    assert skill_bonus(ch, "athletics") == 4 and skill_bonus(ch, "history") == 2
    assert skill_bonus(ch, "perception") == 1 and passive_perception(ch) == 11
    assert initiative(ch) == 0


def test_expertise_doubles_proficiency():
    assert skill_bonus_value(3, 3, True, True) == 9
    assert skill_bonus_value(3, 3, False, False) == 3
    ch = make(abilities=dict(dexterity=16), skills=SkillProficiencies(proficient=["stealth"], expertise=["stealth"]))
    assert skill_bonus(ch, "stealth") == 3 + 2 * 2


def test_skill_model_validation():
    with pytest.raises(ValidationError):
        SkillProficiencies(proficient=["flying"])
    with pytest.raises(ValidationError):
        SkillProficiencies(proficient=["stealth", "stealth"])
    with pytest.raises(ValidationError):
        SkillProficiencies(expertise=["stealth"])


def test_saves_and_unknowns():
    assert saves_for("Mago") == ("intelligence", "wisdom") and saves_for(None) == ()
    with pytest.raises(ValueError):
        skill_bonus(make(), "flying")


def test_rolls():
    ch = make(abilities=dict(wisdom=14), skills=SkillProficiencies(proficient=["perception"]))
    assert roll_skill(ch, "perception", rng=FixedRng(10)).total == 14
    assert roll_save(ch, "wisdom", Advantage.ADVANTAGE, FixedRng(3, 9)).total == 13


def test_speed_from_race_with_fallback():
    assert speed(make(species="Anão")) == 25
    assert speed(make(species="Elfo")) == 30
    assert speed(make()) == 30


def test_profile_defaults_and_limits():
    assert Profile().backstory == ""
    with pytest.raises(ValidationError):
        Profile(alignment="x" * 101)


def test_old_json_loads_with_new_fields():
    ch = Character.model_validate_json('{"name":"V","ruleset":"dnd-5e-2014","hit_points":{"current":5,"maximum":5}}')
    assert ch.skills == SkillProficiencies() and ch.profile == Profile()
