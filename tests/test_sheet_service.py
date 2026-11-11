import pytest
from pydantic import ValidationError

from app_dnd.dice import Advantage
from app_dnd.models import AbilityScores, HitPoints
from app_dnd.services.sheet import (
    ability_check,
    apply_damage,
    apply_healing,
    format_modifier,
    new_character,
)
from tests.test_dice import FixedRng


def test_temp_hp_absorbs_damage_first():
    hp = apply_damage(HitPoints(current=10, maximum=10, temporary=5), 8)
    assert (hp.current, hp.temporary) == (7, 0)


def test_damage_fully_absorbed_by_temp_hp():
    hp = apply_damage(HitPoints(current=10, maximum=10, temporary=5), 3)
    assert (hp.current, hp.temporary) == (10, 2)


def test_damage_never_below_zero():
    assert apply_damage(HitPoints(current=4, maximum=10), 99).current == 0


def test_healing_capped_and_keeps_temp():
    hp = apply_healing(HitPoints(current=4, maximum=10, temporary=3), 99)
    assert (hp.current, hp.temporary) == (10, 3)


def test_negative_amounts_rejected():
    hp = HitPoints(current=5, maximum=10)
    with pytest.raises(ValueError):
        apply_damage(hp, -1)
    with pytest.raises(ValueError):
        apply_healing(hp, -1)


def test_current_hp_cannot_exceed_max():
    with pytest.raises(ValidationError):
        HitPoints(current=11, maximum=10)


def test_ability_check_uses_modifier_and_advantage():
    ch = new_character()
    ch.abilities = AbilityScores(dexterity=16)
    assert ability_check(ch, "dexterity", Advantage.NONE, FixedRng(10)).total == 13
    assert ability_check(ch, "dexterity", Advantage.ADVANTAGE, FixedRng(4, 18)).total == 21
    assert ability_check(ch, "dexterity", Advantage.DISADVANTAGE, FixedRng(4, 18)).total == 7


def test_unknown_ability_rejected():
    with pytest.raises(ValueError):
        ability_check(new_character(), "luck")


def test_format_modifier():
    assert format_modifier(3) == "+3" and format_modifier(0) == "+0" and format_modifier(-2) == "−2"


def test_new_character_is_valid_and_default_ruleset_2024():
    ch = new_character()
    assert ch.ruleset == "dnd-5e-2024" and ch.level == 1
