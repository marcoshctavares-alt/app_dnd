from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app_dnd.models import AbilityScores, Character, HitPoints, ability_modifier, proficiency_bonus


def make(**kw):
    base = dict(name="Thalia", ruleset="dnd-5e-2024", hit_points=HitPoints(current=8, maximum=8))
    return Character(**{**base, **kw})


def test_valid_character_defaults():
    c = make()
    assert c.level == 1 and c.abilities.strength == 10 and c.created_at.tzinfo is not None


def test_name_is_trimmed_and_cannot_be_blank():
    assert make(name="  Thalia  ").name == "Thalia"
    with pytest.raises(ValidationError):
        make(name="   ")


@pytest.mark.parametrize("level", [0, 21])
def test_level_bounds(level):
    with pytest.raises(ValidationError):
        make(level=level)


def test_ability_bounds_and_ruleset():
    with pytest.raises(ValidationError):
        make(abilities=AbilityScores(strength=31))
    with pytest.raises(ValidationError):
        make(ruleset="dnd-3.5")


def test_naive_datetime_rejected():
    with pytest.raises(ValidationError):
        make(created_at=datetime(2026, 1, 1))


def test_validate_assignment():
    c = make()
    with pytest.raises(ValidationError):
        c.level = 25


@pytest.mark.parametrize("score,mod", [(1, -5), (8, -1), (9, -1), (10, 0), (11, 0), (15, 2), (20, 5), (30, 10)])
def test_modifier(score, mod):
    assert ability_modifier(score) == mod


@pytest.mark.parametrize("level,pb", [(1, 2), (4, 2), (5, 3), (9, 4), (13, 5), (17, 6), (20, 6)])
def test_proficiency_bonus(level, pb):
    assert proficiency_bonus(level) == pb
    assert make(level=level).proficiency_bonus == pb
