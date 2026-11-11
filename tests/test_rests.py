import random

import pytest

from app_dnd.data.class_resources import RAGES, RULES_2024, maximum
from app_dnd.data.srd import CLASSES
from app_dnd.models import AbilityScores, Character, HitPoints
from app_dnd.services import rests


def make(cls="Guerreiro", level=1, hp=(10, 10), ruleset="dnd-5e-2024", **abilities):
    return Character(
        name="T", ruleset=ruleset, character_class=cls, level=level, abilities=AbilityScores(**abilities),
        hit_points=HitPoints(current=hp[0], maximum=hp[1], temporary=3),
    )


def levels(key, **kw):
    return [maximum(key, lv, **kw) for lv in range(1, 21)]


def test_maxima_match_srd_tables():
    assert list(RAGES) == [2, 2, 3, 3, 3, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 6, 6, 6, 6]
    assert levels("channel-divinity")[1:] == [2] * 4 + [3] * 12 + [4] * 3
    assert levels("paladin-channel-divinity")[2:] == [2] * 8 + [3] * 10
    assert levels("wild-shape")[1:] == [2] * 4 + [3] * 11 + [4] * 4
    assert levels("second-wind") == [2] * 3 + [3] * 6 + [4] * 11
    assert levels("action-surge") == [0] + [1] * 15 + [2] * 4
    assert levels("indomitable") == [0] * 8 + [1] * 4 + [2] * 4 + [3] * 4
    assert levels("favored-enemy") == [2] * 4 + [3] * 4 + [4] * 4 + [5] * 4 + [6] * 4
    assert levels("lay-on-hands")[:3] == [5, 10, 15] and maximum("focus", 7) == 7
    assert maximum("bardic-inspiration", 3, charisma_modifier=-1) == 1
    assert maximum("bardic-inspiration", 3, charisma_modifier=4) == 4


def test_every_rule_class_exists_and_has_a_maximum():
    names = {c.name for c in CLASSES}
    assert set(RULES_2024) <= names
    for rules in RULES_2024.values():
        for rule in rules:
            assert all(maximum(rule.key, lv) >= 0 for lv in range(1, 21))


def test_resources_hidden_below_first_level_and_for_2014():
    assert [s.rule.key for s in rests.class_resources(make("Guerreiro", 1))] == ["second-wind"]
    assert {s.rule.key for s in rests.class_resources(make("Guerreiro", 9))} == {
        "second-wind", "action-surge", "indomitable"
    }
    assert rests.class_resources(make("Guerreiro", 9, ruleset="dnd-5e-2014")) == []
    assert rests.class_resources(make("Ladino", 5)) == []


def test_use_and_restore_resource_with_limits():
    ch = make("Bárbaro", 1)
    rests.use_resource(ch, "rage")
    rests.use_resource(ch, "rage")
    with pytest.raises(ValueError):
        rests.use_resource(ch, "rage")
    assert ch.resources_used == {"rage": 2}
    rests.restore_resource(ch, "rage")
    assert rests.class_resources(ch)[0].remaining == 1
    with pytest.raises(ValueError):
        rests.use_resource(ch, "focus")
    with pytest.raises(ValueError):
        rests.restore_resource(make("Bárbaro"), "rage")


def test_short_rest_follows_each_resources_policy():
    ch = make("Guerreiro", 9)
    for key, times in (("second-wind", 3), ("action-surge", 1), ("indomitable", 1)):
        for _ in range(times):
            rests.use_resource(ch, key)
    rests.short_rest(ch)
    assert ch.resources_used == {"second-wind": 2, "indomitable": 1}
    barb = make("Bárbaro", 3)
    for _ in range(3):
        rests.use_resource(barb, "rage")
    rests.short_rest(barb)
    assert barb.resources_used == {"rage": 2}


def test_bardic_inspiration_short_rest_from_level_5():
    low, high = make("Bardo", 4, charisma=16), make("Bardo", 5, charisma=16)
    for ch in (low, high):
        rests.use_resource(ch, "bardic-inspiration", 3)
        rests.short_rest(ch)
    assert low.resources_used == {"bardic-inspiration": 3}
    assert high.resources_used == {}


def test_long_rest_restores_everything():
    ch = make("Clérigo", 6, hp=(2, 40))
    ch.hit_dice_used = 5
    rests.use_resource(ch, "channel-divinity", 2)
    ch.spells = ch.spells.model_copy(update={"slots_used": {1: 2}})
    rests.long_rest(ch)
    assert (ch.hit_points.current, ch.hit_points.temporary) == (40, 0)
    assert ch.hit_dice_used == 2 and ch.resources_used == {} and ch.spells.slots_used == {}


def test_long_rest_recovers_at_least_one_hit_die():
    ch = make(level=1)
    ch.hit_dice_used = 1
    rests.long_rest(ch)
    assert ch.hit_dice_used == 0


def test_spend_hit_die_heals_with_con_and_caps_at_max():
    ch = make("Guerreiro", 3, hp=(1, 30), constitution=14)
    healed = rests.spend_hit_die(ch)
    assert 3 <= healed <= 12 and ch.hit_points.current == 1 + healed and ch.hit_dice_used == 1
    full = make("Guerreiro", 3, hp=(29, 30), constitution=20)
    assert rests.spend_hit_die(full) <= 1 and full.hit_points.current <= 30


def test_spend_hit_die_negative_modifier_never_damages():
    ch = make("Mago", 2, hp=(5, 10), constitution=3)
    for _ in range(2):
        before = ch.hit_points.current
        assert rests.spend_hit_die(ch) >= 0 and ch.hit_points.current >= before


def test_spend_hit_die_errors():
    ch = make("Guerreiro", 1)
    rests.spend_hit_die(ch)
    with pytest.raises(ValueError):
        rests.spend_hit_die(ch)
    with pytest.raises(ValueError):
        rests.spend_hit_die(make(None))


def test_resource_state_clamps_after_level_loss_and_roundtrips():
    ch = make("Bárbaro", 3)
    ch.resources_used = {"rage": 3}
    ch.level = 1
    assert rests.class_resources(ch)[0].remaining == 0
    assert Character.model_validate(ch.model_dump(mode="json")).resources_used == {"rage": 3}
    with pytest.raises(ValueError):
        ch.resources_used = {"rage": -1}


def test_random_characters_survive_full_rest_cycle():
    from app_dnd.services.generator import random_character

    for seed in range(60):
        r = random.Random(seed)
        ch = random_character(level=r.randint(1, 20), rng=r)
        for state in rests.class_resources(ch):
            rests.use_resource(ch, state.rule.key, state.maximum) if state.maximum else None
        rests.short_rest(ch)
        rests.long_rest(ch)
        assert ch.resources_used == {} and ch.hit_points.current == ch.hit_points.maximum
