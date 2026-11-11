from __future__ import annotations

from dataclasses import dataclass

ALL, ONE = "all", "one"


@dataclass(frozen=True)
class ResourceRule:
    key: str
    name: str
    short_rest: str | None
    first_level: int = 1


RULES_2024: dict[str, tuple[ResourceRule, ...]] = {
    "Bárbaro": (ResourceRule("rage", "Fúrias", ONE),),
    "Bardo": (ResourceRule("bardic-inspiration", "Inspiração de Bardo", None),),
    "Clérigo": (ResourceRule("channel-divinity", "Canalizar Divindade", ONE, 2),),
    "Druida": (ResourceRule("wild-shape", "Forma Selvagem", ONE, 2),),
    "Guerreiro": (
        ResourceRule("second-wind", "Retomar o Fôlego", ONE),
        ResourceRule("action-surge", "Surto de Ação", ALL, 2),
        ResourceRule("indomitable", "Indomável", None, 9),
    ),
    "Monge": (ResourceRule("focus", "Pontos de Foco", ALL, 2),),
    "Paladino": (
        ResourceRule("lay-on-hands", "Mãos Consagradas (PV)", None),
        ResourceRule("paladin-channel-divinity", "Canalizar Divindade", ONE, 3),
    ),
    "Patrulheiro": (ResourceRule("favored-enemy", "Inimigo Favorito (Marca do Caçador)", None),),
    "Feiticeiro": (
        ResourceRule("sorcery-points", "Pontos de Feitiçaria", None, 2),
        ResourceRule("innate-sorcery", "Feitiçaria Inata", None),
    ),
    "Bruxo": (ResourceRule("magical-cunning", "Astúcia Mágica", None, 2),),
    "Mago": (ResourceRule("arcane-recovery", "Recuperação Arcana", None),),
}

RAGES = (2, 2, 3, 3, 3, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 6, 6, 6, 6)


def _by_threshold(level: int, steps: tuple[tuple[int, int], ...]) -> int:
    return max((value for start, value in steps if level >= start), default=0)


def maximum(key: str, level: int, charisma_modifier: int = 0) -> int:
    match key:
        case "rage":
            return RAGES[level - 1]
        case "bardic-inspiration":
            return max(1, charisma_modifier)
        case "channel-divinity":
            return _by_threshold(level, ((2, 2), (6, 3), (18, 4)))
        case "paladin-channel-divinity":
            return _by_threshold(level, ((3, 2), (11, 3)))
        case "wild-shape":
            return _by_threshold(level, ((2, 2), (6, 3), (17, 4)))
        case "second-wind":
            return _by_threshold(level, ((1, 2), (4, 3), (10, 4)))
        case "action-surge":
            return _by_threshold(level, ((2, 1), (17, 2)))
        case "indomitable":
            return _by_threshold(level, ((9, 1), (13, 2), (17, 3)))
        case "focus" | "sorcery-points":
            return level
        case "lay-on-hands":
            return 5 * level
        case "favored-enemy":
            return _by_threshold(level, ((1, 2), (5, 3), (9, 4), (13, 5), (17, 6)))
        case "innate-sorcery":
            return 2
        case "magical-cunning" | "arcane-recovery":
            return 1
    raise KeyError(key)
