from __future__ import annotations

from dataclasses import dataclass

from app_dnd.data.class_resources import ALL, ONE, RULES_2024, ResourceRule, maximum
from app_dnd.data.srd import CLASS_BY_NAME
from app_dnd.dice import roll
from app_dnd.models import Character
from app_dnd.services import spells

RULESET_2024 = "dnd-5e-2024"


@dataclass(frozen=True)
class ResourceState:
    rule: ResourceRule
    maximum: int
    used: int

    @property
    def remaining(self) -> int:
        return self.maximum - self.used


def class_resources(character: Character) -> list[ResourceState]:
    if character.ruleset != RULESET_2024:
        return []
    states = []
    for rule in RULES_2024.get(character.character_class or "", ()):
        if character.level < rule.first_level:
            continue
        top = maximum(rule.key, character.level, character.abilities.modifier("charisma"))
        states.append(ResourceState(rule, top, min(top, character.resources_used.get(rule.key, 0))))
    return states


def _state(character: Character, key: str) -> ResourceState:
    state = next((s for s in class_resources(character) if s.rule.key == key), None)
    if state is None:
        raise ValueError("Recurso indisponível para esta ficha")
    return state


def _set_used(character: Character, key: str, used: int) -> None:
    updated = dict(character.resources_used)
    if used > 0:
        updated[key] = used
    else:
        updated.pop(key, None)
    character.resources_used = updated


def use_resource(character: Character, key: str, amount: int = 1) -> None:
    state = _state(character, key)
    if amount < 1 or state.remaining < amount:
        raise ValueError(f"{state.rule.name}: sem usos suficientes (restam {state.remaining})")
    _set_used(character, key, state.used + amount)


def restore_resource(character: Character, key: str, amount: int = 1) -> None:
    state = _state(character, key)
    if amount < 1 or state.used < amount:
        raise ValueError(f"{state.rule.name}: nada para recuperar")
    _set_used(character, key, state.used - amount)


def hit_dice_total(character: Character) -> int:
    return character.level


def hit_dice_remaining(character: Character) -> int:
    return max(0, character.level - character.hit_dice_used)


def hit_die_sides(character: Character) -> int | None:
    info = CLASS_BY_NAME.get(character.character_class or "")
    return info.hit_die if info else None


def spend_hit_die(character: Character) -> int:
    sides = hit_die_sides(character)
    if sides is None:
        raise ValueError("Escolha uma classe para usar Dados de Vida")
    if hit_dice_remaining(character) == 0:
        raise ValueError("Sem Dados de Vida restantes")
    hp = character.hit_points
    healed = min(hp.maximum - hp.current, max(0, roll(f"1d{sides}").total + character.abilities.modifier("constitution")))
    character.hit_dice_used += 1
    character.hit_points = hp.model_copy(update={"current": hp.current + healed})
    return healed


def short_rest(character: Character) -> None:
    spells.short_rest(character)
    for state in class_resources(character):
        policy = state.rule.short_rest
        if state.rule.key == "bardic-inspiration" and character.level >= 5:
            policy = ALL
        if policy == ALL:
            _set_used(character, state.rule.key, 0)
        elif policy == ONE:
            _set_used(character, state.rule.key, max(0, state.used - 1))


def long_rest(character: Character) -> None:
    spells.long_rest(character)
    hp = character.hit_points
    character.hit_points = hp.model_copy(update={"current": hp.maximum, "temporary": 0})
    character.hit_dice_used = max(0, character.hit_dice_used - max(1, character.level // 2))
    character.resources_used = {}
