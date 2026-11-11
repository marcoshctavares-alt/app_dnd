from __future__ import annotations

import random
import re
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

ALLOWED_SIDES = (2, 3, 4, 6, 8, 10, 12, 20, 100)
MAX_DICE = 100

_PATTERN = re.compile(
    r"^\s*(?P<count>\d*)d(?P<sides>\d+)"
    r"(?:(?P<keep>k[hl])(?P<keep_n>\d+))?"
    r"\s*(?:(?P<sign>[+-])\s*(?P<mod>\d+))?\s*$",
    re.IGNORECASE,
)


class Rng(Protocol):
    def randint(self, a: int, b: int) -> int: ...


class Advantage(Enum):
    NONE = "none"
    ADVANTAGE = "advantage"
    DISADVANTAGE = "disadvantage"


@dataclass(frozen=True)
class RollResult:
    expression: str
    rolls: tuple[int, ...]
    kept: tuple[int, ...]
    modifier: int
    total: int

    def __str__(self) -> str:
        mod = f" {'+' if self.modifier >= 0 else '-'} {abs(self.modifier)}" if self.modifier else ""
        return f"{self.expression}: {list(self.rolls)} (mantidos {list(self.kept)}){mod} = {self.total}"


_default_rng: Rng = random.SystemRandom()


def roll(expression: str, rng: Rng | None = None) -> RollResult:
    rng = rng or _default_rng
    m = _PATTERN.match(expression)
    if not m:
        raise ValueError(f"Notação inválida: {expression!r}")

    count = int(m["count"] or 1)
    sides = int(m["sides"])
    if sides not in ALLOWED_SIDES:
        raise ValueError(f"d{sides} não é um dado suportado: {ALLOWED_SIDES}")
    if not 1 <= count <= MAX_DICE:
        raise ValueError(f"A quantidade de dados deve estar entre 1 e {MAX_DICE}")

    rolls = tuple(rng.randint(1, sides) for _ in range(count))

    kept = rolls
    if m["keep"]:
        n = int(m["keep_n"])
        if not 1 <= n <= count:
            raise ValueError("Quantidade a manter deve estar entre 1 e o total de dados")
        ordered = sorted(rolls, reverse=m["keep"].lower() == "kh")
        kept = tuple(ordered[:n])

    modifier = 0
    if m["mod"]:
        modifier = int(m["mod"]) * (-1 if m["sign"] == "-" else 1)

    return RollResult(expression.strip(), rolls, kept, modifier, sum(kept) + modifier)


def roll_d20(modifier: int = 0, advantage: Advantage = Advantage.NONE, rng: Rng | None = None) -> RollResult:
    expr = {Advantage.NONE: "1d20", Advantage.ADVANTAGE: "2d20kh1", Advantage.DISADVANTAGE: "2d20kl1"}[advantage]
    sign = "+" if modifier >= 0 else "-"
    return roll(f"{expr}{sign}{abs(modifier)}" if modifier else expr, rng)
