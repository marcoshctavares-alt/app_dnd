from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from app_dnd.data.equipment import ARMORS, CLASS_WEAPON_PROFICIENCY, WEAPONS, Armor, Weapon
from app_dnd.dice import Advantage, RollResult, roll, roll_d20
from app_dnd.dice.roller import Rng
from app_dnd.models import Attack, Character, Item

COINS_PER_POUND = 50


def _find_item(character: Character, item_id: UUID) -> Item:
    for item in character.inventory:
        if item.id == item_id:
            return item
    raise ValueError("Item não encontrado")


def add_catalog_item(character: Character, catalog_id: str, quantity: int = 1) -> Item:
    if catalog_id in WEAPONS:
        w = WEAPONS[catalog_id]
        item = Item(name=w.name, kind="weapon", catalog_id=w.id, quantity=quantity, weight=w.weight)
    elif catalog_id in ARMORS:
        a = ARMORS[catalog_id]
        kind = "shield" if a.kind == "escudo" else "armor"
        item = Item(name=a.name, kind=kind, catalog_id=a.id, quantity=quantity, weight=a.weight)
    else:
        raise ValueError(f"Item de catálogo desconhecido: {catalog_id!r}")
    character.inventory = [*character.inventory, item]
    return item


def add_custom_item(character: Character, name: str, quantity: int = 1, weight: float = 0, notes: str | None = None) -> Item:
    item = Item(name=name, kind="gear", quantity=quantity, weight=weight, notes=notes)
    character.inventory = [*character.inventory, item]
    return item


def remove_item(character: Character, item_id: UUID) -> None:
    _find_item(character, item_id)
    character.inventory = [i for i in character.inventory if i.id != item_id]


def set_quantity(character: Character, item_id: UUID, quantity: int) -> None:
    item = _find_item(character, item_id)
    updated = Item.model_validate({**item.model_dump(), "quantity": quantity})
    character.inventory = [updated if i.id == item.id else i for i in character.inventory]


def set_equipped(character: Character, item_id: UUID, equipped: bool) -> None:
    target = _find_item(character, item_id)
    items = []
    for item in character.inventory:
        if item.id == target.id:
            items.append(item.model_copy(update={"equipped": equipped}))
        elif equipped and target.kind in ("armor", "shield") and item.kind == target.kind and item.equipped:
            items.append(item.model_copy(update={"equipped": False}))
        else:
            items.append(item)
    character.inventory = items


def total_weight(character: Character) -> float:
    gear = sum(i.weight * i.quantity for i in character.inventory)
    return round(gear + character.coins.count / COINS_PER_POUND, 2)


def carrying_capacity(character: Character) -> int:
    return character.abilities.strength * 15


STRENGTH_SPEED_PENALTY = 10


def equipped_armor(character: Character) -> Armor | None:
    return next(
        (ARMORS[i.catalog_id] for i in character.inventory if i.equipped and i.kind == "armor" and i.catalog_id in ARMORS),
        None,
    )


def armor_speed_penalty(character: Character) -> int:
    armor = equipped_armor(character)
    if armor is not None and character.abilities.strength < armor.min_strength:
        return STRENGTH_SPEED_PENALTY
    return 0


def armor_warnings(character: Character) -> list[str]:
    armor = equipped_armor(character)
    if armor is None:
        return []
    warnings = []
    if character.abilities.strength < armor.min_strength:
        warnings.append(
            f"{armor.name} exige Força {armor.min_strength} (você tem {character.abilities.strength}): "
            f"deslocamento reduzido em {STRENGTH_SPEED_PENALTY} pés"
        )
    if armor.stealth_disadvantage:
        warnings.append(f"{armor.name} impõe desvantagem em testes de Furtividade")
    return warnings


def armor_class(character: Character) -> int:
    dex = character.abilities.modifier("dexterity")
    equipped = [i for i in character.inventory if i.equipped]
    armor = equipped_armor(character)
    shield = any(i.kind == "shield" for i in equipped)

    if armor is None:
        base = 10 + dex
        if character.character_class == "Bárbaro":
            base += character.abilities.modifier("constitution")
        elif character.character_class == "Monge" and not shield:
            base += character.abilities.modifier("wisdom")
    elif armor.kind == "leve":
        base = armor.base_ac + dex
    elif armor.kind == "media":
        base = armor.base_ac + min(dex, 2)
    else:
        base = armor.base_ac
    return base + (2 if shield else 0)


def default_proficiency(class_name: str | None, weapon: Weapon) -> bool:
    categories, specific = CLASS_WEAPON_PROFICIENCY.get(class_name or "", (frozenset(), frozenset()))
    return weapon.category in categories or weapon.id in specific


def attack_from_weapon(
    character: Character, weapon_id: str, two_handed: bool = False, off_hand: bool = False, off_hand_modifier: bool = False
) -> Attack:
    weapon = WEAPONS.get(weapon_id)
    if weapon is None:
        raise ValueError(f"Arma desconhecida: {weapon_id!r}")
    if two_handed and not weapon.versatile_dice:
        raise ValueError(f"{weapon.name} não tem a propriedade versátil")
    if off_hand and two_handed:
        raise ValueError("Ataque com a mão secundária não pode ser com duas mãos")
    if off_hand and "light" not in weapon.properties:
        raise ValueError(f"{weapon.name} não tem a propriedade leve")

    if weapon.ranged:
        ability = "dexterity"
    elif "finesse" in weapon.properties:
        a = character.abilities
        ability = "dexterity" if a.dexterity >= a.strength else "strength"
    else:
        ability = "strength"

    attack = Attack(
        name=f"{weapon.name} (duas mãos)" if two_handed else f"{weapon.name} (mão secundária)" if off_hand else weapon.name,
        ability=ability,
        proficient=default_proficiency(character.character_class, weapon),
        damage_dice=weapon.versatile_dice if two_handed else weapon.dice,
        damage_type=weapon.damage_type,
        weapon_id=weapon.id,
        off_hand=off_hand,
        off_hand_modifier=off_hand and off_hand_modifier,
    )
    character.attacks = [*character.attacks, attack]
    return attack


def add_custom_attack(character: Character, **fields) -> Attack:
    attack = Attack(**fields)
    character.attacks = [*character.attacks, attack]
    return attack


def remove_attack(character: Character, attack_id: UUID) -> None:
    if not any(a.id == attack_id for a in character.attacks):
        raise ValueError("Ataque não encontrado")
    character.attacks = [a for a in character.attacks if a.id != attack_id]


def attack_bonus(character: Character, attack: Attack) -> int:
    prof = character.proficiency_bonus if attack.proficient else 0
    return character.abilities.modifier(attack.ability) + prof + attack.to_hit_bonus


def damage_modifier(character: Character, attack: Attack) -> int:
    ability = character.abilities.modifier(attack.ability)
    if attack.off_hand and not attack.off_hand_modifier:
        ability = min(0, ability)
    return ability + attack.damage_bonus


def damage_expression(character: Character, attack: Attack, critical: bool = False) -> str:
    m = re.fullmatch(r"(\d*)d(\d+)", attack.damage_dice)
    count = int(m[1] or 1) * (2 if critical else 1)
    mod = damage_modifier(character, attack)
    base = f"{count}d{m[2]}"
    return f"{base}{'+' if mod >= 0 else '-'}{abs(mod)}" if mod else base


@dataclass(frozen=True)
class AttackRoll:
    result: RollResult
    natural: int
    critical: bool
    fumble: bool

    def __str__(self) -> str:
        tag = " — ACERTO CRÍTICO!" if self.critical else " — falha crítica" if self.fumble else ""
        return f"{self.result}{tag}"


def roll_attack(
    character: Character, attack: Attack, advantage: Advantage = Advantage.NONE, rng: Rng | None = None
) -> AttackRoll:
    result = roll_d20(attack_bonus(character, attack), advantage, rng)
    natural = result.kept[0]
    return AttackRoll(result, natural, natural == 20, natural == 1)


def roll_damage(character: Character, attack: Attack, critical: bool = False, rng: Rng | None = None) -> RollResult:
    return roll(damage_expression(character, attack, critical), rng)
