from __future__ import annotations

from dataclasses import dataclass, field

CORTANTE, PERFURANTE, CONTUNDENTE = "cortante", "perfurante", "contundente"


@dataclass(frozen=True)
class Weapon:
    id: str
    name: str
    category: str
    ranged: bool
    dice: str
    damage_type: str
    weight: float
    properties: frozenset[str] = field(default_factory=frozenset)
    versatile_dice: str | None = None
    range: str | None = None


@dataclass(frozen=True)
class Armor:
    id: str
    name: str
    kind: str
    base_ac: int
    weight: float
    stealth_disadvantage: bool = False
    min_strength: int = 0


def _w(id, name, cat, ranged, dice, dtype, weight, props="", versatile=None, rng=None) -> Weapon:
    return Weapon(id, name, cat, ranged, dice, dtype, weight, frozenset(p for p in props.split(",") if p), versatile, rng)


_WEAPON_LIST = [
    _w("club", "Clava", "simples", False, "1d4", CONTUNDENTE, 2, "light"),
    _w("dagger", "Adaga", "simples", False, "1d4", PERFURANTE, 1, "finesse,light,thrown", rng="20/60"),
    _w("greatclub", "Clava Grande", "simples", False, "1d8", CONTUNDENTE, 10, "two_handed"),
    _w("handaxe", "Machadinha", "simples", False, "1d6", CORTANTE, 2, "light,thrown", rng="20/60"),
    _w("javelin", "Azagaia", "simples", False, "1d6", PERFURANTE, 2, "thrown", rng="30/120"),
    _w("light-hammer", "Martelo Leve", "simples", False, "1d4", CONTUNDENTE, 2, "light,thrown", rng="20/60"),
    _w("mace", "Maça", "simples", False, "1d6", CONTUNDENTE, 4),
    _w("quarterstaff", "Bordão", "simples", False, "1d6", CONTUNDENTE, 4, "versatile", "1d8"),
    _w("sickle", "Foice", "simples", False, "1d4", CORTANTE, 2, "light"),
    _w("spear", "Lança", "simples", False, "1d6", PERFURANTE, 3, "thrown,versatile", "1d8", "20/60"),
    _w("light-crossbow", "Besta Leve", "simples", True, "1d8", PERFURANTE, 5, "ammunition,loading,two_handed", rng="80/320"),
    _w("dart", "Dardo", "simples", True, "1d4", PERFURANTE, 0.25, "finesse,thrown", rng="20/60"),
    _w("shortbow", "Arco Curto", "simples", True, "1d6", PERFURANTE, 2, "ammunition,two_handed", rng="80/320"),
    _w("sling", "Funda", "simples", True, "1d4", CONTUNDENTE, 0, "ammunition", rng="30/120"),
    _w("battleaxe", "Machado de Batalha", "marcial", False, "1d8", CORTANTE, 4, "versatile", "1d10"),
    _w("flail", "Mangual", "marcial", False, "1d8", CONTUNDENTE, 2),
    _w("glaive", "Glaive", "marcial", False, "1d10", CORTANTE, 6, "heavy,reach,two_handed"),
    _w("greataxe", "Machado Grande", "marcial", False, "1d12", CORTANTE, 7, "heavy,two_handed"),
    _w("greatsword", "Espada Grande", "marcial", False, "2d6", CORTANTE, 6, "heavy,two_handed"),
    _w("halberd", "Alabarda", "marcial", False, "1d10", CORTANTE, 6, "heavy,reach,two_handed"),
    _w("longsword", "Espada Longa", "marcial", False, "1d8", CORTANTE, 3, "versatile", "1d10"),
    _w("maul", "Malho", "marcial", False, "2d6", CONTUNDENTE, 10, "heavy,two_handed"),
    _w("morningstar", "Maça Estrela", "marcial", False, "1d8", PERFURANTE, 4),
    _w("pike", "Pique", "marcial", False, "1d10", PERFURANTE, 18, "heavy,reach,two_handed"),
    _w("rapier", "Rapieira", "marcial", False, "1d8", PERFURANTE, 2, "finesse"),
    _w("scimitar", "Cimitarra", "marcial", False, "1d6", CORTANTE, 3, "finesse,light"),
    _w("shortsword", "Espada Curta", "marcial", False, "1d6", PERFURANTE, 2, "finesse,light"),
    _w("trident", "Tridente", "marcial", False, "1d6", PERFURANTE, 4, "thrown,versatile", "1d8", "20/60"),
    _w("war-pick", "Picareta de Guerra", "marcial", False, "1d8", PERFURANTE, 2),
    _w("warhammer", "Martelo de Guerra", "marcial", False, "1d8", CONTUNDENTE, 2, "versatile", "1d10"),
    _w("whip", "Chicote", "marcial", False, "1d4", CORTANTE, 3, "finesse,reach"),
    _w("hand-crossbow", "Besta de Mão", "marcial", True, "1d6", PERFURANTE, 3, "ammunition,light,loading", rng="30/120"),
    _w("heavy-crossbow", "Besta Pesada", "marcial", True, "1d10", PERFURANTE, 18, "ammunition,heavy,loading,two_handed", rng="100/400"),
    _w("longbow", "Arco Longo", "marcial", True, "1d8", PERFURANTE, 2, "ammunition,heavy,two_handed", rng="150/600"),
]

_ARMOR_LIST = [
    Armor("padded", "Acolchoada", "leve", 11, 8, True),
    Armor("leather", "Couro", "leve", 11, 10),
    Armor("studded-leather", "Couro Batido", "leve", 12, 13),
    Armor("hide", "Gibão de Peles", "media", 12, 12),
    Armor("chain-shirt", "Camisa de Malha", "media", 13, 20),
    Armor("scale-mail", "Brunea", "media", 14, 45, True),
    Armor("breastplate", "Peitoral", "media", 14, 20),
    Armor("half-plate", "Meia-armadura", "media", 15, 40, True),
    Armor("ring-mail", "Cota de Anéis", "pesada", 14, 40, True),
    Armor("chain-mail", "Cota de Malha", "pesada", 16, 55, True, 13),
    Armor("splint", "Cota de Talas", "pesada", 17, 60, True, 15),
    Armor("plate", "Armadura de Placas", "pesada", 18, 65, True, 15),
    Armor("shield", "Escudo", "escudo", 2, 6),
]

WEAPONS: dict[str, Weapon] = {w.id: w for w in _WEAPON_LIST}
ARMORS: dict[str, Armor] = {a.id: a for a in _ARMOR_LIST}

CLASS_WEAPON_PROFICIENCY: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "Bárbaro": (frozenset({"simples", "marcial"}), frozenset()),
    "Bardo": (frozenset({"simples"}), frozenset({"hand-crossbow", "longsword", "rapier", "shortsword"})),
    "Clérigo": (frozenset({"simples"}), frozenset()),
    "Druida": (frozenset(), frozenset({"club", "dagger", "dart", "javelin", "mace", "quarterstaff", "scimitar", "sickle", "sling", "spear"})),
    "Guerreiro": (frozenset({"simples", "marcial"}), frozenset()),
    "Monge": (frozenset({"simples"}), frozenset({"shortsword"})),
    "Paladino": (frozenset({"simples", "marcial"}), frozenset()),
    "Patrulheiro": (frozenset({"simples", "marcial"}), frozenset()),
    "Ladino": (frozenset({"simples"}), frozenset({"hand-crossbow", "longsword", "rapier", "shortsword"})),
    "Feiticeiro": (frozenset(), frozenset({"dagger", "dart", "sling", "quarterstaff", "light-crossbow"})),
    "Bruxo": (frozenset({"simples"}), frozenset()),
    "Mago": (frozenset(), frozenset({"dagger", "dart", "sling", "quarterstaff", "light-crossbow"})),
}
