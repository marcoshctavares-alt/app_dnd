from __future__ import annotations

from app_dnd.data.backgrounds import Background, find_background
from app_dnd.data.skills import SKILLS
from app_dnd.models import Character
from app_dnd.services.races import ABILITY_CAP, ABILITY_LABELS

MARKER = "Antecedente: "
SPREAD = "+1 em cada"


def ability_choices(background: Background) -> dict[str, dict[str, int]]:
    choices: dict[str, dict[str, int]] = {}
    for major in background.abilities:
        for minor in background.abilities:
            if major != minor:
                label = f"+2 {ABILITY_LABELS[major]}, +1 {ABILITY_LABELS[minor]}"
                choices[label] = {major: 2, minor: 1}
    choices[SPREAD] = dict.fromkeys(background.abilities, 1)
    return choices


def is_applied(character: Character) -> bool:
    return MARKER in character.profile.features


def apply_background(character: Character, name: str, increases: dict[str, int]) -> Character:
    if character.ruleset != "dnd-5e-2024":
        raise ValueError("Os antecedentes do SRD 5.2.1 valem apenas para as regras de 2024")
    background = find_background(name)
    if background is None:
        raise ValueError(f"Antecedente desconhecido: {name!r}")
    if is_applied(character):
        raise ValueError("Esta ficha já recebeu um antecedente")
    if sorted(increases.values()) not in ([1, 1, 1], [1, 2]) or not set(increases) <= set(background.abilities):
        raise ValueError("Aumentos de atributo inválidos para este antecedente")

    abilities = character.abilities.model_dump()
    for ability, value in increases.items():
        abilities[ability] = max(abilities[ability], min(ABILITY_CAP, abilities[ability] + value))
    proficient = list(character.skills.proficient)
    proficient += [s for s in background.skills if s not in proficient and s in SKILLS]
    skill_names = " e ".join(SKILLS[s][0] for s in background.skills)
    notes = (
        f"{MARKER}{background.name}\n"
        f"- Talento: {background.feat}\n- Perícias: {skill_names}\n- Ferramenta: {background.tool}"
    )
    features = f"{character.profile.features}\n{notes}".strip()
    feats = list(character.feats)
    if background.feat not in feats:
        feats.append(background.feat)
    return character.model_copy(
        update={
            "feats": feats,
            "abilities": type(character.abilities)(**abilities),
            "skills": character.skills.model_copy(update={"proficient": proficient}),
            "profile": character.profile.model_copy(update={"background": background.name, "features": features}),
        }
    )
