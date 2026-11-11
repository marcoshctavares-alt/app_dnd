from __future__ import annotations

from typing import Sequence

from app_dnd.data.races import find_race
from app_dnd.models import AbilityScores
from app_dnd.services.sheet import ABILITY_LABELS

ABILITY_CAP = 20


def racial_bonuses(
    ruleset: str,
    species: str | None,
    subrace: str | None = None,
    free_choices: Sequence[str] = (),
) -> dict[str, int]:
    if ruleset != "dnd-5e-2014":
        return {}
    race = find_race(ruleset, species)
    if race is None:
        return {}

    bonuses = dict(race.bonuses)
    if subrace:
        for ability, value in race.subrace(subrace).bonuses.items():
            bonuses[ability] = bonuses.get(ability, 0) + value

    if race.free_choices:
        chosen = list(free_choices)
        if len(chosen) != race.free_choices or len(set(chosen)) != len(chosen):
            raise ValueError(f"Escolha {race.free_choices} atributos diferentes para {race.name}")
        for ability in chosen:
            if ability not in ABILITY_LABELS:
                raise ValueError(f"Atributo desconhecido: {ability!r}")
            if ability in race.free_choice_excludes:
                raise ValueError(f"{ABILITY_LABELS[ability]} não pode ser escolhido para {race.name}")
            bonuses[ability] = bonuses.get(ability, 0) + 1
    elif free_choices:
        raise ValueError(f"{race.name} não tem bônus à escolha")
    return bonuses


def apply_racial_bonuses(base: AbilityScores, bonuses: dict[str, int]) -> AbilityScores:
    data = base.model_dump()
    for ability, value in bonuses.items():
        data[ability] = max(data[ability], min(ABILITY_CAP, data[ability] + value))
    return AbilityScores(**data)


def describe_race(ruleset: str, species: str | None, subrace: str | None = None) -> str:
    race = find_race(ruleset, species)
    if race is None:
        return ""
    speed = race.speed
    if subrace:
        speed = race.subrace(subrace).speed or speed
    parts = [f"Tamanho {race.size}", f"deslocamento {speed} pés"]
    if ruleset == "dnd-5e-2014":
        bonuses = dict(race.bonuses)
        if subrace:
            for ability, value in race.subrace(subrace).bonuses.items():
                bonuses[ability] = bonuses.get(ability, 0) + value
        text = ", ".join(f"{ABILITY_LABELS[a]} +{v}" for a, v in bonuses.items())
        if race.free_choices:
            text += f"; +1 em {race.free_choices} outros atributos à escolha"
        parts.append(f"bônus: {text}")
    else:
        parts.append("sem bônus de atributo (vêm do antecedente)")
    return " · ".join(parts)


def species_traits(ruleset: str, species: str | None, subrace: str | None = None) -> list[str]:
    race = find_race(ruleset, species)
    if race is None:
        return []
    traits = list(race.traits)
    if subrace:
        sub = race.subrace(subrace)
        traits.extend(f"{sub.name}: {t}" for t in sub.traits)
    return traits
