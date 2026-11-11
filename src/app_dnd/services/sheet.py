from __future__ import annotations

import os
import sys
from pathlib import Path

from app_dnd.dice import Advantage, RollResult, roll_d20
from app_dnd.dice.roller import Rng
from app_dnd.models import AbilityScores, Character, HitPoints

ABILITY_LABELS: dict[str, str] = {
    "strength": "Força",
    "dexterity": "Destreza",
    "constitution": "Constituição",
    "intelligence": "Inteligência",
    "wisdom": "Sabedoria",
    "charisma": "Carisma",
}

RULESET_LABELS: dict[str, str] = {
    "dnd-5e-2014": "D&D 5e (2014)",
    "dnd-5e-2024": "D&D 5e (2024)",
}


def new_character(name: str = "Novo personagem", ruleset: str = "dnd-5e-2024") -> Character:
    return Character(
        name=name,
        ruleset=ruleset,
        abilities=AbilityScores(),
        hit_points=HitPoints(current=10, maximum=10),
    )


def apply_damage(hp: HitPoints, amount: int) -> HitPoints:
    if amount < 0:
        raise ValueError("Dano não pode ser negativo")
    absorbed = min(hp.temporary, amount)
    remaining = amount - absorbed
    return HitPoints(
        current=max(0, hp.current - remaining),
        maximum=hp.maximum,
        temporary=hp.temporary - absorbed,
    )


def apply_healing(hp: HitPoints, amount: int) -> HitPoints:
    if amount < 0:
        raise ValueError("Cura não pode ser negativa")
    return HitPoints(
        current=min(hp.maximum, hp.current + amount),
        maximum=hp.maximum,
        temporary=hp.temporary,
    )


def ability_check(
    character: Character,
    ability: str,
    advantage: Advantage = Advantage.NONE,
    rng: Rng | None = None,
) -> RollResult:
    if ability not in ABILITY_LABELS:
        raise ValueError(f"Atributo desconhecido: {ability!r}")
    return roll_d20(character.abilities.modifier(ability), advantage, rng)


def format_modifier(value: int) -> str:
    return f"+{value}" if value >= 0 else f"−{abs(value)}"


def default_db_path() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    folder = base / "APP_DND"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "app_dnd.db"
