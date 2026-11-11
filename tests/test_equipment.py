import json

import pytest
from pydantic import ValidationError

from app_dnd.backup import export_backup, import_backup
from app_dnd.data.equipment import ARMORS, WEAPONS
from app_dnd.dice import Advantage
from app_dnd.models import AbilityScores, Attack, Character, Coins, HitPoints
from app_dnd.services.equipment import (
    add_catalog_item,
    add_custom_attack,
    add_custom_item,
    armor_class,
    attack_bonus,
    attack_from_weapon,
    carrying_capacity,
    damage_expression,
    default_proficiency,
    remove_attack,
    remove_item,
    roll_attack,
    roll_damage,
    set_equipped,
    set_quantity,
    total_weight,
)
from app_dnd.storage import Database
from tests.test_dice import FixedRng


def make(cls="Guerreiro", level=1, **ab):
    return Character(name="T", ruleset="dnd-5e-2024", character_class=cls, level=level,
                     abilities=AbilityScores(**ab), hit_points=HitPoints(current=5, maximum=5))


def test_catalog_sizes_and_integrity():
    assert len(WEAPONS) == 34 and len(ARMORS) == 13
    for w in WEAPONS.values():
        assert w.id and w.dice.count("d") == 1
        assert ("versatile" in w.properties) == bool(w.versatile_dice)
        assert (w.range is not None) == bool({"thrown", "ammunition"} & w.properties)
    assert ARMORS["plate"].base_ac == 18 and ARMORS["chain-mail"].min_strength == 13


def test_unarmored_and_class_defenses():
    assert armor_class(make(dexterity=14)) == 12
    assert armor_class(make("Bárbaro", dexterity=14, constitution=16)) == 15
    assert armor_class(make("Monge", dexterity=16, wisdom=14)) == 15


def _equip(ch, catalog_id):
    item = add_catalog_item(ch, catalog_id)
    set_equipped(ch, item.id, True)
    return item


@pytest.mark.parametrize(
    "armor,dex,expected",
    [("leather", 16, 14), ("studded-leather", 14, 14), ("chain-shirt", 18, 15),
     ("breastplate", 12, 15), ("chain-mail", 18, 16), ("plate", 8, 18)],
)
def test_armor_ac_rules(armor, dex, expected):
    ch = make(dexterity=dex)
    _equip(ch, armor)
    assert armor_class(ch) == expected


def test_shield_adds_two_and_monk_loses_unarmored_defense():
    ch = make("Guerreiro", dexterity=12)
    _equip(ch, "chain-mail")
    _equip(ch, "shield")
    assert armor_class(ch) == 18
    monk = make("Monge", dexterity=16, wisdom=14)
    _equip(monk, "shield")
    assert armor_class(monk) == 15
    barb = make("Bárbaro", dexterity=14, constitution=16)
    _equip(barb, "shield")
    assert armor_class(barb) == 17


def test_only_one_armor_and_one_shield_equipped():
    ch = make()
    a = _equip(ch, "leather")
    b = _equip(ch, "plate")
    equipped = {i.id for i in ch.inventory if i.equipped}
    assert equipped == {b.id} and a.id not in equipped
    set_equipped(ch, b.id, False)
    assert armor_class(ch) == 10


def test_inventory_ops_and_weight():
    ch = make(strength=15)
    item = add_catalog_item(ch, "greatsword")
    add_custom_item(ch, "Corda", quantity=2, weight=10)
    ch.coins = Coins(gp=100)
    assert total_weight(ch) == 6 + 20 + 2
    assert carrying_capacity(ch) == 225
    set_quantity(ch, item.id, 3)
    assert total_weight(ch) == 18 + 20 + 2
    with pytest.raises(ValueError):
        set_quantity(ch, item.id, 0)
    remove_item(ch, item.id)
    with pytest.raises(ValueError):
        remove_item(ch, item.id)
    with pytest.raises(ValueError):
        add_catalog_item(ch, "banana")


def test_coins_value():
    assert Coins(cp=100, sp=10, ep=2, gp=1, pp=1).total_gp == 1 + 1 + 1 + 1 + 10


def test_attack_ability_choice():
    ch = make(strength=10, dexterity=16)
    assert attack_from_weapon(ch, "rapier").ability == "dexterity"
    assert attack_from_weapon(ch, "longbow").ability == "dexterity"
    assert attack_from_weapon(ch, "greatsword").ability == "strength"
    strong = make(strength=16, dexterity=12)
    assert attack_from_weapon(strong, "dagger").ability == "strength"


def test_versatile_two_handed():
    ch = make()
    a = attack_from_weapon(ch, "longsword", two_handed=True)
    assert a.damage_dice == "1d10" and "duas mãos" in a.name
    with pytest.raises(ValueError):
        attack_from_weapon(ch, "dagger", two_handed=True)


def test_default_proficiency_by_class():
    assert default_proficiency("Guerreiro", WEAPONS["greataxe"])
    assert not default_proficiency("Mago", WEAPONS["longsword"])
    assert default_proficiency("Mago", WEAPONS["dagger"])
    assert default_proficiency("Ladino", WEAPONS["rapier"]) and not default_proficiency("Ladino", WEAPONS["greatsword"])
    assert default_proficiency("Clérigo", WEAPONS["mace"]) and not default_proficiency("Clérigo", WEAPONS["longsword"])
    assert not default_proficiency(None, WEAPONS["club"])


def test_attack_bonus_and_damage_expression():
    ch = make(level=5, strength=16)
    a = add_custom_attack(ch, name="Espada +1", ability="strength", damage_dice="1d8", to_hit_bonus=1, damage_bonus=1)
    assert attack_bonus(ch, a) == 7
    assert damage_expression(ch, a) == "1d8+4"
    assert damage_expression(ch, a, critical=True) == "2d8+4"
    unproficient = add_custom_attack(ch, name="X", damage_dice="2d6")
    unproficient.proficient = False
    assert attack_bonus(ch, unproficient) == 3
    negative = make(strength=8)
    n = add_custom_attack(negative, name="Y", damage_dice="d6")
    assert damage_expression(negative, n) == "1d6-1"
    zero = add_custom_attack(make(), name="Z", damage_dice="1d4")
    assert damage_expression(make(), zero) == "1d4"


def test_roll_attack_with_crit_and_fumble_and_advantage():
    ch = make(strength=16)
    a = add_custom_attack(ch, name="Espada", damage_dice="1d8")
    r = roll_attack(ch, a, rng=FixedRng(20))
    assert r.critical and not r.fumble and r.result.total == 25 and "CRÍTICO" in str(r)
    r = roll_attack(ch, a, rng=FixedRng(1))
    assert r.fumble and not r.critical
    r = roll_attack(ch, a, Advantage.ADVANTAGE, FixedRng(1, 20))
    assert r.critical and r.natural == 20
    r = roll_attack(ch, a, Advantage.DISADVANTAGE, FixedRng(1, 20))
    assert r.fumble


def test_roll_damage_normal_and_critical():
    ch = make(strength=16)
    a = add_custom_attack(ch, name="Espada", damage_dice="1d8")
    assert roll_damage(ch, a, rng=FixedRng(5)).total == 8
    assert roll_damage(ch, a, critical=True, rng=FixedRng(5, 6)).total == 14


def test_attack_validation_and_removal():
    ch = make()
    for bad in ({"damage_dice": "1d7"}, {"damage_dice": "abc"}, {"to_hit_bonus": 99}, {"ability": "luck"}):
        with pytest.raises(ValidationError):
            Attack(name="x", **bad)
    a = add_custom_attack(ch, name="Soco", damage_dice="1d4")
    remove_attack(ch, a.id)
    with pytest.raises(ValueError):
        remove_attack(ch, a.id)


def test_persist_and_backup_roundtrip():
    db = Database(":memory:")
    ch = make(strength=14)
    _equip(ch, "chain-mail")
    attack_from_weapon(ch, "longsword")
    ch.coins = Coins(gp=15)
    db.save_character(ch)
    assert db.get_character(ch.id).inventory == ch.inventory

    dst = Database(":memory:")
    import_backup(dst, export_backup(db))
    restored = dst.get_character(ch.id)
    assert restored.attacks == ch.attacks and restored.coins.gp == 15 and armor_class(restored) == armor_class(ch)


def test_old_character_json_loads_with_empty_equipment():
    ch = Character.model_validate_json('{"name":"V","ruleset":"dnd-5e-2014","hit_points":{"current":5,"maximum":5}}')
    assert ch.inventory == [] and ch.attacks == [] and ch.coins.count == 0


def test_heavy_armor_strength_requirement():
    from app_dnd.models import AbilityScores, Character, HitPoints
    from app_dnd.services.equipment import add_catalog_item, armor_speed_penalty, armor_warnings, set_equipped
    from app_dnd.services.skills import speed

    ch = Character(name="A", ruleset="dnd-5e-2024", species="Humano", character_class="Guerreiro",
                   abilities=AbilityScores(strength=12), hit_points=HitPoints(current=5, maximum=5))
    assert armor_warnings(ch) == [] and speed(ch) == 30
    plate = add_catalog_item(ch, "plate")
    assert speed(ch) == 30
    set_equipped(ch, plate.id, True)
    assert armor_speed_penalty(ch) == 10 and speed(ch) == 20
    assert len(armor_warnings(ch)) == 2 and "Força 15" in armor_warnings(ch)[0]
    ch.abilities = AbilityScores(strength=15)
    assert speed(ch) == 30 and len(armor_warnings(ch)) == 1
    chain = add_catalog_item(ch, "chain-mail")
    set_equipped(ch, chain.id, True)
    ch.abilities = AbilityScores(strength=12)
    assert speed(ch) == 20
    ch.abilities = AbilityScores(strength=13)
    assert speed(ch) == 30
    leather = add_catalog_item(ch, "leather")
    set_equipped(ch, leather.id, True)
    assert armor_warnings(ch) == []


def test_off_hand_attack_damage_rules():
    import pytest

    from app_dnd.models import AbilityScores, Character, HitPoints
    from app_dnd.services.equipment import attack_from_weapon, damage_expression

    def make(strength, dexterity=10):
        return Character(name="D", ruleset="dnd-5e-2024", character_class="Guerreiro",
                         abilities=AbilityScores(strength=strength, dexterity=dexterity),
                         hit_points=HitPoints(current=5, maximum=5))

    ch = make(16)
    main = attack_from_weapon(ch, "handaxe")
    off = attack_from_weapon(ch, "handaxe", off_hand=True)
    styled = attack_from_weapon(ch, "handaxe", off_hand=True, off_hand_modifier=True)
    assert damage_expression(ch, main) == "1d6+3"
    assert damage_expression(ch, off) == "1d6" and damage_expression(ch, off, critical=True) == "2d6"
    assert damage_expression(ch, styled) == "1d6+3"
    assert off.name == "Machadinha (mão secundária)" and off.off_hand and not off.off_hand_modifier
    weak = make(6)
    penalized = attack_from_weapon(weak, "handaxe", off_hand=True)
    assert penalized.ability == "strength" and damage_expression(weak, penalized) == "1d6-2"
    finesse = attack_from_weapon(make(10, 16), "dagger", off_hand=True)
    assert finesse.ability == "dexterity" and damage_expression(make(10, 16), finesse) == "1d4"
    bonus = attack_from_weapon(ch, "handaxe", off_hand=True)
    bonus = bonus.model_copy(update={"damage_bonus": 1})
    assert damage_expression(ch, bonus) == "1d6+1"
    with pytest.raises(ValueError):
        attack_from_weapon(ch, "longsword", off_hand=True)
    with pytest.raises(ValueError):
        attack_from_weapon(ch, "handaxe", two_handed=True, off_hand=True)
    from app_dnd.services.equipment import attack_bonus
    assert attack_bonus(ch, off) == attack_bonus(ch, main)
