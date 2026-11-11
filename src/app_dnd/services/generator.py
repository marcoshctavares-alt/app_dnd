from __future__ import annotations

import random
from typing import Sequence

from app_dnd.data.backgrounds import BACKGROUNDS_2024
from app_dnd.data.races import races_for
from app_dnd.data.srd import CLASSES, NAMES, ClassInfo
from app_dnd.dice import roll
from app_dnd.dice.roller import Rng
from app_dnd.models import AbilityScores, Character, HitPoints, ability_modifier
from app_dnd.services.backgrounds import ability_choices, apply_background
from app_dnd.services.races import apply_racial_bonuses, racial_bonuses
from app_dnd.services.sheet import ABILITY_LABELS


_default: random.SystemRandom = random.SystemRandom()


def roll_ability_scores(rng: Rng | None = None) -> list[int]:
    return sorted((roll("4d6kh3", rng).total for _ in range(6)), reverse=True)


def assign_scores(scores: Sequence[int], class_info: ClassInfo) -> AbilityScores:
    ordered = sorted(scores, reverse=True)
    return AbilityScores(**{ability: value for ability, value in zip(class_info.priority, ordered)})


def hit_points_for(class_info: ClassInfo, level: int, constitution: int) -> int:
    con = ability_modifier(constitution)
    total = max(1, class_info.hit_die + con)
    per_level = max(1, class_info.hit_die // 2 + 1 + con)
    return total + per_level * (level - 1)


def random_character(
    level: int | None = None,
    ruleset: str = "dnd-5e-2024",
    rng: random.Random | None = None,
) -> Character:
    rng = rng or _default
    level = level if level is not None else rng.randint(1, 20)
    if not 1 <= level <= 20:
        raise ValueError("Nível deve estar entre 1 e 20")

    class_info = rng.choice(CLASSES)
    race = rng.choice(races_for(ruleset))
    subrace = rng.choice(race.subraces).name if race.subraces else None
    free: list[str] = []
    if race.free_choices:
        options = [a for a in ABILITY_LABELS if a not in race.free_choice_excludes]
        free = rng.sample(options, race.free_choices)

    subclass_name, subclass_level = class_info.subclass_for(ruleset)
    base = assign_scores(roll_ability_scores(rng), class_info)
    abilities = apply_racial_bonuses(base, racial_bonuses(ruleset, race.name, subrace, free))
    max_hp = hit_points_for(class_info, level, abilities.constitution)

    character = Character(
        name=rng.choice(NAMES),
        ruleset=ruleset,
        species=race.name,
        subrace=subrace,
        character_class=class_info.name,
        subclass=subclass_name if level >= subclass_level else None,
        level=level,
        abilities=abilities,
        hit_points=HitPoints(current=max_hp, maximum=max_hp),
    )
    if ruleset != "dnd-5e-2024":
        return character
    background = rng.choice(BACKGROUNDS_2024)
    increases = rng.choice(list(ability_choices(background).values()))
    character = apply_background(character, background.name, increases)
    max_hp = hit_points_for(class_info, level, character.abilities.constitution)
    return character.model_copy(update={"hit_points": HitPoints(current=max_hp, maximum=max_hp)})
