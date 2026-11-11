from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClassInfo:
    name: str
    hit_die: int
    priority: tuple[str, ...]
    subclass: str
    subclass_level: int
    subclass_2024: str = ""

    def subclass_for(self, ruleset: str) -> tuple[str, int]:
        if ruleset == "dnd-5e-2024":
            return self.subclass_2024 or self.subclass, SUBCLASS_LEVEL_2024
        return self.subclass, self.subclass_level


SUBCLASS_LEVEL_2024 = 3

_ALL = ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma")


def _prio(*first: str) -> tuple[str, ...]:
    return first + tuple(a for a in _ALL if a not in first)


CLASSES: tuple[ClassInfo, ...] = (
    ClassInfo("Bárbaro", 12, _prio("strength", "constitution", "dexterity"), "Trilha do Berserker", 3),
    ClassInfo("Bardo", 8, _prio("charisma", "dexterity", "constitution"), "Colégio do Conhecimento", 3),
    ClassInfo("Clérigo", 8, _prio("wisdom", "constitution", "strength"), "Domínio da Vida", 1),
    ClassInfo("Druida", 8, _prio("wisdom", "constitution", "dexterity"), "Círculo da Terra", 2),
    ClassInfo("Guerreiro", 10, _prio("strength", "constitution", "dexterity"), "Campeão", 3),
    ClassInfo("Monge", 8, _prio("dexterity", "wisdom", "constitution"), "Caminho da Mão Aberta", 3, "Guerreiro da Mão Aberta"),
    ClassInfo("Paladino", 10, _prio("strength", "charisma", "constitution"), "Juramento da Devoção", 3),
    ClassInfo("Patrulheiro", 10, _prio("dexterity", "wisdom", "constitution"), "Caçador", 3),
    ClassInfo("Ladino", 8, _prio("dexterity", "constitution", "charisma"), "Ladrão", 3),
    ClassInfo("Feiticeiro", 6, _prio("charisma", "constitution", "dexterity"), "Linhagem Dracônica", 1, "Feitiçaria Dracônica"),
    ClassInfo("Bruxo", 8, _prio("charisma", "constitution", "dexterity"), "Patrono Ínfero", 1),
    ClassInfo("Mago", 6, _prio("intelligence", "constitution", "dexterity"), "Escola de Evocação", 2, "Evocador"),
)

NAMES: tuple[str, ...] = (
    "Thalia", "Borin", "Elara", "Garrick", "Mirela", "Dorian", "Sylwen", "Kael",
    "Brunhild", "Tobias", "Ysolde", "Fenwick", "Nadia", "Orin", "Lyra", "Haldor",
    "Isolde", "Ragnar", "Selene", "Barnabé",
)

CLASS_BY_NAME = {c.name: c for c in CLASSES}
