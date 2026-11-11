from __future__ import annotations

import json
import unicodedata
from typing import Iterable

from pydantic import ValidationError

from app_dnd.data.spellcasting import cantrips_known, prepared_spells
from app_dnd.data.spells import SRD_SPELLS
from app_dnd.models import Character, Spell, ability_modifier, proficiency_bonus

CASTERS: dict[str, tuple[str, str]] = {
    "Bardo": ("full", "charisma"),
    "Clérigo": ("full", "wisdom"),
    "Druida": ("full", "wisdom"),
    "Feiticeiro": ("full", "charisma"),
    "Mago": ("full", "intelligence"),
    "Paladino": ("half", "charisma"),
    "Patrulheiro": ("half", "wisdom"),
    "Bruxo": ("pact", "charisma"),
}

_FULL = [
    (2,), (3,), (4, 2), (4, 3), (4, 3, 2), (4, 3, 3), (4, 3, 3, 1), (4, 3, 3, 2), (4, 3, 3, 3, 1),
    (4, 3, 3, 3, 2), (4, 3, 3, 3, 2, 1), (4, 3, 3, 3, 2, 1), (4, 3, 3, 3, 2, 1, 1), (4, 3, 3, 3, 2, 1, 1),
    (4, 3, 3, 3, 2, 1, 1, 1), (4, 3, 3, 3, 2, 1, 1, 1), (4, 3, 3, 3, 2, 1, 1, 1, 1),
    (4, 3, 3, 3, 3, 1, 1, 1, 1), (4, 3, 3, 3, 3, 2, 1, 1, 1), (4, 3, 3, 3, 3, 2, 2, 1, 1),
]
_HALF = [
    (), (2,), (3,), (3,), (4, 2), (4, 2), (4, 3), (4, 3), (4, 3, 2), (4, 3, 2),
    (4, 3, 3), (4, 3, 3), (4, 3, 3, 1), (4, 3, 3, 1), (4, 3, 3, 2), (4, 3, 3, 2),
    (4, 3, 3, 3, 1), (4, 3, 3, 3, 1), (4, 3, 3, 3, 2), (4, 3, 3, 3, 2),
]
_PACT = [
    (1, 1), (2, 1), (2, 2), (2, 2), (2, 3), (2, 3), (2, 4), (2, 4), (2, 5), (2, 5),
    (3, 5), (3, 5), (3, 5), (3, 5), (3, 5), (3, 5), (4, 5), (4, 5), (4, 5), (4, 5),
]


def caster_info(class_name: str | None) -> tuple[str, str] | None:
    return CASTERS.get(class_name or "")


def spell_slots(class_name: str | None, level: int, ruleset: str = "dnd-5e-2024") -> dict[int, int]:
    info = caster_info(class_name)
    if info is None or not 1 <= level <= 20:
        return {}
    kind = info[0]
    if kind == "full":
        row = _FULL[level - 1]
    elif kind == "half":
        row = (2,) if (level == 1 and ruleset == "dnd-5e-2024") else _HALF[level - 1]
    else:
        count, slot_level = _PACT[level - 1]
        return {slot_level: count}
    return {i + 1: n for i, n in enumerate(row)}


def pact_slot_level(character: Character) -> int | None:
    info = caster_info(character.character_class)
    if info and info[0] == "pact":
        return next(iter(spell_slots(character.character_class, character.level, character.ruleset)))
    return None


def remaining_slots(character: Character) -> dict[int, tuple[int, int]]:
    totals = spell_slots(character.character_class, character.level, character.ruleset)
    used = character.spells.slots_used
    return {lvl: (max(0, total - used.get(lvl, 0)), total) for lvl, total in totals.items()}


def spellcasting_stats(character: Character) -> dict[str, int | str] | None:
    info = caster_info(character.character_class)
    if info is None:
        return None
    ability = info[1]
    mod = character.abilities.modifier(ability)
    prof = proficiency_bonus(character.level)
    return {"ability": ability, "save_dc": 8 + prof + mod, "attack_bonus": prof + mod}


PREPARED_CASTERS_2014 = frozenset({"Clérigo", "Druida", "Mago", "Paladino"})


def max_prepared(character: Character) -> int | None:
    if character.ruleset == "dnd-5e-2024":
        return prepared_spells(character.character_class, character.level)
    cls = character.character_class
    if cls not in PREPARED_CASTERS_2014:
        return None
    mod = ability_modifier(getattr(character.abilities, CASTERS[cls][1]))
    base = character.level // 2 if cls == "Paladino" else character.level
    return max(1, mod + base)


def max_cantrips(character: Character) -> int | None:
    if character.ruleset != "dnd-5e-2024":
        return None
    value = cantrips_known(character.character_class, character.level)
    return value if value else None


def cantrip_count(character: Character, catalog: SpellCatalog) -> int:
    return sum(1 for sid in character.spells.known if (sp := catalog.get(sid)) is not None and sp.level == 0)


def _norm(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if not unicodedata.combining(c))


class SpellCatalog:
    def __init__(self, custom: Iterable[Spell] = ()) -> None:
        spells: dict[str, Spell] = {s.id: s for s in SRD_SPELLS}
        for spell in custom:
            if spell.id in spells and spells[spell.id].source == "srd":
                continue
            spells[spell.id] = spell
        self._spells = spells
        self._ordered = sorted(spells.values(), key=lambda s: (s.level, _norm(s.name)))
        self._keys = {s.id: (_norm(s.name), _norm(s.name_en or "")) for s in self._ordered}

    def get(self, spell_id: str) -> Spell | None:
        return self._spells.get(spell_id)

    def all(self) -> list[Spell]:
        return list(self._ordered)

    def search(self, text: str = "", level: int | None = None, class_name: str | None = None) -> list[Spell]:
        needle = _norm(text.strip())
        result = []
        for spell in self._ordered:
            if level is not None and spell.level != level:
                continue
            if class_name and class_name not in spell.classes:
                continue
            if needle:
                name, name_en = self._keys[spell.id]
                if needle not in name and needle not in name_en:
                    continue
            result.append(spell)
        return result


def load_spell_pack(raw: str) -> list[Spell]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON inválido: {exc}") from exc
    items = data.get("spells") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError('Esperado uma lista de magias ou {"spells": [...]}')
    srd_ids = {s.id for s in SRD_SPELLS}
    spells: list[Spell] = []
    try:
        for item in items:
            spell = Spell.model_validate({**item, "source": "custom"})
            if spell.id in srd_ids:
                raise ValueError(f"O id {spell.id!r} já existe no SRD")
            spells.append(spell)
    except (ValidationError, TypeError, AttributeError) as exc:
        raise ValueError(f"Magia inválida: {exc}") from exc
    if len({s.id for s in spells}) != len(spells):
        raise ValueError("Ids de magia repetidos no pacote")
    return spells


def _with_book(character: Character, **changes) -> Character:
    character.spells = character.spells.model_copy(update=changes)
    return character


def add_spell(character: Character, catalog: SpellCatalog, spell_id: str) -> Character:
    if catalog.get(spell_id) is None:
        raise ValueError(f"Magia desconhecida: {spell_id!r}")
    if spell_id in character.spells.known:
        raise ValueError("A magia já está na ficha")
    return _with_book(character, known=[*character.spells.known, spell_id])


def remove_spell(character: Character, spell_id: str) -> Character:
    book = character.spells
    return _with_book(
        character,
        known=[s for s in book.known if s != spell_id],
        prepared=[s for s in book.prepared if s != spell_id],
    )


def set_prepared(character: Character, catalog: SpellCatalog, spell_id: str, prepared: bool) -> Character:
    book = character.spells
    spell = catalog.get(spell_id)
    if spell is None or spell_id not in book.known:
        raise ValueError("A magia precisa estar na ficha")
    if spell.level == 0:
        raise ValueError("Truques não são preparados")
    current = [s for s in book.prepared if s != spell_id]
    if prepared:
        limit = max_prepared(character)
        if limit is not None and len(current) + 1 > limit:
            raise ValueError(f"Limite de {limit} magias preparadas atingido")
        current.append(spell_id)
    return _with_book(character, prepared=current)


def cast_spell(character: Character, catalog: SpellCatalog, spell_id: str, slot_level: int | None = None) -> str:
    spell = catalog.get(spell_id)
    if spell is None or spell_id not in character.spells.known:
        raise ValueError("A magia precisa estar na ficha")
    if spell.level == 0:
        return f"{spell.name} (truque) conjurado"

    totals = spell_slots(character.character_class, character.level, character.ruleset)
    if not totals:
        raise ValueError("Esta classe não tem espaços de magia")

    pact = pact_slot_level(character)
    if pact is not None:
        if spell.level > pact:
            raise ValueError(f"{spell.name} exige nível {spell.level}; seus espaços de pacto são de nível {pact}")
        level = pact
    else:
        level = slot_level if slot_level is not None else spell.level
        if level < spell.level:
            raise ValueError("O espaço usado não pode ser menor que o nível da magia")
        if level not in totals:
            raise ValueError(f"Você não tem espaços de nível {level}")

    left, _ = remaining_slots(character)[level]
    if left <= 0:
        raise ValueError(f"Sem espaços de nível {level} restantes")
    used = dict(character.spells.slots_used)
    used[level] = used.get(level, 0) + 1
    _with_book(character, slots_used=used)
    return f"{spell.name} conjurada com espaço de nível {level}"


def long_rest(character: Character) -> Character:
    return _with_book(character, slots_used={})


def short_rest(character: Character) -> Character:
    return _with_book(character, slots_used={}) if pact_slot_level(character) else character


def spend_slot(character: Character, level: int) -> Character:
    left = remaining_slots(character)
    if level not in left:
        raise ValueError(f"Você não tem espaços de nível {level}")
    if left[level][0] <= 0:
        raise ValueError(f"Sem espaços de nível {level} restantes")
    used = dict(character.spells.slots_used)
    used[level] = used.get(level, 0) + 1
    return _with_book(character, slots_used=used)


def format_spell(spell: Spell, original: bool = False) -> str:
    kind = "Truque" if spell.level == 0 else f"{spell.level}º nível"
    tags = [t for t, on in (("ritual", spell.ritual), ("concentração", spell.concentration)) if on]
    lines = [
        f"{spell.name}" + (f" ({spell.name_en})" if spell.name_en else ""),
        f"{kind} de {spell.school}" + (f" — {', '.join(tags)}" if tags else ""),
        f"Tempo de conjuração: {spell.casting_time}",
        f"Alcance: {spell.range}",
        f"Componentes: {spell.components}",
        f"Duração: {spell.duration}",
    ]
    if spell.classes:
        lines.append(f"Classes: {', '.join(spell.classes)}")
    lines.append("")
    body = spell.description if original else spell.description_pt or spell.description
    lines.append(body or "(sem descrição — importe um pacote de magias para incluir o texto)")
    return "\n".join(lines)
