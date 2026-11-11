from __future__ import annotations

from app_dnd.data.races import find_race
from app_dnd.data.skills import CLASS_SAVES, SKILLS
from app_dnd.dice import Advantage, RollResult, roll_d20
from app_dnd.dice.roller import Rng
from app_dnd.models import Character
from app_dnd.services.equipment import armor_speed_penalty

DEFAULT_SPEED = 30


def skill_bonus_value(ability_mod: int, proficiency: int, proficient: bool = False, expertise: bool = False) -> int:
    if not proficient:
        return ability_mod
    return ability_mod + proficiency * (2 if expertise else 1)


def saves_for(class_name: str | None) -> tuple[str, ...]:
    return CLASS_SAVES.get(class_name or "", ())


def skill_bonus(character: Character, skill_id: str) -> int:
    if skill_id not in SKILLS:
        raise ValueError(f"Perícia desconhecida: {skill_id!r}")
    return skill_bonus_value(
        character.abilities.modifier(SKILLS[skill_id][1]),
        character.proficiency_bonus,
        skill_id in character.skills.proficient,
        skill_id in character.skills.expertise,
    )


def save_bonus(character: Character, ability: str) -> int:
    return skill_bonus_value(
        character.abilities.modifier(ability),
        character.proficiency_bonus,
        ability in saves_for(character.character_class),
    )


def initiative(character: Character) -> int:
    return character.abilities.modifier("dexterity")


def passive_perception(character: Character) -> int:
    return 10 + skill_bonus(character, "perception")


def base_speed(character: Character) -> int:
    race = find_race(character.ruleset, character.species)
    if race is None:
        return DEFAULT_SPEED
    if character.subrace:
        for sub in race.subraces:
            if sub.name == character.subrace and sub.speed:
                return sub.speed
    return race.speed


def speed(character: Character) -> int:
    return max(0, base_speed(character) - armor_speed_penalty(character))


def roll_skill(character: Character, skill_id: str, advantage: Advantage = Advantage.NONE, rng: Rng | None = None) -> RollResult:
    return roll_d20(skill_bonus(character, skill_id), advantage, rng)


def roll_save(character: Character, ability: str, advantage: Advantage = Advantage.NONE, rng: Rng | None = None) -> RollResult:
    return roll_d20(save_bonus(character, ability), advantage, rng)
