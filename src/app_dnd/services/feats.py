from __future__ import annotations

from itertools import combinations, permutations

from app_dnd.data.feats import (
    FEAT_BY_NAME,
    FEATS_2024,
    FIGHTING_STYLE_CLASSES,
    NEEDS_FIGHTING_STYLE,
    NEEDS_SPELLCASTING,
    Feat,
)
from app_dnd.models import Character
from app_dnd.services.sheet import ABILITY_LABELS
from app_dnd.services.spells import caster_info

RULESET_2024 = "dnd-5e-2024"


def prerequisite_text(feat: Feat) -> str:
    parts = []
    if feat.min_level > 1:
        parts.append(f"nível {feat.min_level}+")
    if feat.abilities_any:
        parts.append(" ou ".join(ABILITY_LABELS[a] for a in feat.abilities_any) + f" {feat.ability_min}+")
    if feat.needs == NEEDS_FIGHTING_STYLE:
        parts.append("característica Estilo de Luta")
    if feat.needs == NEEDS_SPELLCASTING:
        parts.append("característica Conjuração")
    return ", ".join(parts)


def unmet_prerequisites(character: Character, feat: Feat) -> list[str]:
    problems = []
    if character.level < feat.min_level:
        problems.append(f"exige nível {feat.min_level}+")
    if feat.abilities_any and max(getattr(character.abilities, a) for a in feat.abilities_any) < feat.ability_min:
        problems.append("exige " + " ou ".join(ABILITY_LABELS[a] for a in feat.abilities_any) + f" {feat.ability_min}+")
    if feat.needs == NEEDS_FIGHTING_STYLE:
        first = FIGHTING_STYLE_CLASSES.get(character.character_class or "")
        if first is None or character.level < first:
            problems.append("exige a característica Estilo de Luta (Guerreiro, Paladino ou Patrulheiro)")
    if feat.needs == NEEDS_SPELLCASTING and caster_info(character.character_class) is None:
        problems.append("exige a característica Conjuração")
    return problems


def increase_options(feat: Feat) -> dict[str, dict[str, int]]:
    options: dict[str, dict[str, int]] = {}
    for shape in feat.asi_shapes:
        for combo in combinations(feat.asi, len(shape)) if len(set(shape)) == 1 else permutations(feat.asi, len(shape)):
            label = ", ".join(f"+{v} {ABILITY_LABELS[a]}" for a, v in zip(combo, shape, strict=True))
            options[label] = dict(zip(combo, shape, strict=True))
    return options


def has_feat(character: Character, name: str) -> bool:
    return name in character.feats


def available_feats(character: Character) -> list[Feat]:
    if character.ruleset != RULESET_2024:
        return []
    return [
        f
        for f in FEATS_2024
        if (f.repeatable or not has_feat(character, f.name)) and not unmet_prerequisites(character, f)
    ]


def add_feat(character: Character, name: str, increases: dict[str, int] | None = None) -> None:
    if character.ruleset != RULESET_2024:
        raise ValueError("Os talentos do SRD 5.2.1 valem apenas para as regras de 2024")
    feat = FEAT_BY_NAME.get(name)
    if feat is None:
        raise ValueError(f"Talento desconhecido: {name!r}")
    if has_feat(character, name) and not feat.repeatable:
        raise ValueError(f"{name} já foi escolhido e não pode ser repetido")
    if problems := unmet_prerequisites(character, feat):
        raise ValueError(f"{name}: " + "; ".join(problems))
    options = increase_options(feat)
    if options:
        if increases not in options.values():
            raise ValueError(f"{name}: escolha como distribuir o aumento de atributo")
        abilities = character.abilities.model_dump()
        for ability, value in increases.items():
            abilities[ability] = max(abilities[ability], min(feat.asi_cap, abilities[ability] + value))
        character.abilities = type(character.abilities)(**abilities)
    elif increases:
        raise ValueError(f"{name} não concede aumento de atributo")
    character.feats = [*character.feats, name]


def remove_feat(character: Character, name: str) -> None:
    if name not in character.feats:
        raise ValueError(f"{name} não está na ficha")
    feats = list(character.feats)
    feats.remove(name)
    character.feats = feats
