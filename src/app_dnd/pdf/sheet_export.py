from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path

from app_dnd.data.equipment import CLASS_WEAPON_PROFICIENCY, WEAPONS
from app_dnd.data.skills import CLASS_ARMOR, SKILLS
from app_dnd.data.srd import CLASS_BY_NAME
from app_dnd.models import Character
from app_dnd.pdf.fieldmap import (
    ABILITY_FIELDS,
    FONT_SIZES,
    PORTRAIT_FIELD,
    REQUIRED_FIELDS,
    SLOT_EXPENDED,
    SLOT_TOTAL,
    SPELL_LINES,
)
from app_dnd.services.equipment import armor_class, attack_bonus, damage_expression
from app_dnd.services.races import species_traits
from app_dnd.services.rests import class_resources
from app_dnd.services.sheet import ABILITY_LABELS
from app_dnd.services.skills import initiative, passive_perception, save_bonus, saves_for, skill_bonus, speed
from app_dnd.services.spells import PREPARED_CASTERS_2014, SpellCatalog, remaining_slots, spellcasting_stats
from app_dnd.services.subclass import class_feature_summary, unlocked_features

SHEET_PAGES = 3


def _signed(n: int) -> str:
    return f"{n:+d}" if n else "0"


@dataclass
class SheetValues:
    text: dict[str, str] = field(default_factory=dict)
    checks: set[str] = field(default_factory=set)
    warnings: list[str] = field(default_factory=list)


def _weapon_proficiency_text(class_name: str | None) -> str:
    categories, specific = CLASS_WEAPON_PROFICIENCY.get(class_name or "", (frozenset(), frozenset()))
    parts = [{"simples": "simples", "marcial": "marciais"}[c] for c in ("simples", "marcial") if c in categories]
    parts += [WEAPONS[w].name for w in sorted(specific)]
    return ", ".join(parts) or "Nenhuma"


def _fill_identity(ch: Character, v: SheetValues) -> None:
    t, p = v.text, ch.profile
    t["character-name"] = t["character-name-2"] = ch.name
    t["class-level"] = f"{ch.character_class} ({ch.level})" if ch.character_class else f"Nível {ch.level}"
    t["race"] = " ".join(x for x in (ch.species, f"({ch.subrace})" if ch.subrace else "") if x)
    t["player-name"] = ch.player_name or ""
    t["background"], t["alignment"] = p.background, p.alignment


def _fill_abilities_and_skills(ch: Character, v: SheetValues) -> None:
    t = v.text
    saves = saves_for(ch.character_class)
    for ability, short in ABILITY_FIELDS.items():
        t[short] = str(getattr(ch.abilities, ability))
        t[f"{short}-mod"] = _signed(ch.abilities.modifier(ability))
        t[f"{short}-save"] = _signed(save_bonus(ch, ability))
        if ability in saves:
            v.checks.add(f"{short}-save-check")
    for skill_id in SKILLS:
        t[skill_id] = _signed(skill_bonus(ch, skill_id))
        if skill_id in ch.skills.proficient:
            v.checks.add(f"{skill_id}-check")


def _fill_combat(ch: Character, v: SheetValues) -> None:
    t = v.text
    t["prof-bonus"] = _signed(ch.proficiency_bonus)
    t["passive"] = str(passive_perception(ch))
    t["ac"] = str(armor_class(ch))
    t["initiative"] = _signed(initiative(ch))
    t["speed"] = str(speed(ch))
    t["hp-max"] = str(ch.hit_points.maximum)
    t["hp-current"] = str(ch.hit_points.current)
    t["hp-temp"] = str(ch.hit_points.temporary) if ch.hit_points.temporary else ""
    info = CLASS_BY_NAME.get(ch.character_class or "")
    t["hd-total"] = f"{ch.level}d{info.hit_die}" if info else ""


def _fill_attacks(ch: Character, v: SheetValues) -> None:
    t = v.text
    for i, atk in enumerate(ch.attacks[:3], start=1):
        t[f"weapon-name-{i}"] = atk.name
        t[f"weapon-attack-bonus-{i}"] = _signed(attack_bonus(ch, atk))
        t[f"weapon-damage-{i}"] = f"{damage_expression(ch, atk)} {atk.damage_type}".strip()
    extra = [
        f"{a.name}: {_signed(attack_bonus(ch, a))}, {damage_expression(ch, a)} {a.damage_type}".strip()
        for a in ch.attacks[3:]
    ]
    t["attacks-and-spellcasting"] = "\n".join(extra)


def _fill_gear(ch: Character, v: SheetValues) -> None:
    t = v.text
    t["equipment"] = "\n".join(
        f"{i.name} x{i.quantity}" + (" (equipado)" if i.equipped else "") for i in ch.inventory
    )
    for coin in ("cp", "sp", "ep", "gp", "pp"):
        n = getattr(ch.coins, coin)
        t[coin] = str(n) if n else ""
    prof_lines = []
    if ch.character_class:
        prof_lines.append(f"Armas: {_weapon_proficiency_text(ch.character_class)}")
        prof_lines.append(f"Armaduras: {CLASS_ARMOR.get(ch.character_class, '-')}")
    t["other-profs"] = "\n".join(prof_lines)


def _fill_features_and_profile(ch: Character, v: SheetValues) -> None:
    t, p = v.text, ch.profile
    features = [f"Subclasse: {ch.subclass}"] if ch.subclass else []
    if states := class_resources(ch):
        features.append("Recursos: " + ", ".join(f"{s.rule.name} {s.remaining}/{s.maximum}" for s in states))
    if summary := class_feature_summary(ch):
        features.append("Características de classe: " + ", ".join(summary))
    if unlocked := unlocked_features(ch):
        features.append("Características da subclasse: " + ", ".join(f"{f.name} ({f.level})" for f in unlocked))
    try:
        features.extend(f"- {line}" for line in species_traits(ch.ruleset, ch.species, ch.subrace))
    except ValueError:
        v.warnings.append(f"Linhagem {ch.subrace!r} desconhecida: características da espécie não incluídas no PDF")
    if ch.feats:
        features.append("Talentos: " + ", ".join(ch.feats))
    if p.features:
        features.append(p.features)
    t["features-and-traits"] = "\n".join(features)
    t["personality-traits"], t["ideals"], t["bonds"], t["flaws"] = p.personality_traits, p.ideals, p.bonds, p.flaws
    t["age"], t["height"], t["weight"] = p.age, p.height, p.weight
    t["eyes"], t["skin"], t["hair"] = p.eyes, p.skin, p.hair
    t["backstory"], t["allies"], t["treasure"] = p.backstory, p.allies, p.treasure


def _fill_spellcasting(ch: Character, v: SheetValues, catalog: SpellCatalog) -> None:
    t = v.text
    stats = spellcasting_stats(ch)
    if stats is not None:
        t["spellcasting-class-1"] = ch.character_class or ""
        t["spellcasting-ability-1"] = ABILITY_LABELS[stats["ability"]]
        t["spell-save-dc-1"] = str(stats["save_dc"])
        t["spell-attack-bonus-1"] = _signed(int(stats["attack_bonus"]))
        for lvl, (left, total) in remaining_slots(ch).items():
            t[SLOT_TOTAL[lvl]] = str(total)
            t[SLOT_EXPENDED[lvl]] = str(total - left)

    by_level: dict[int, list[tuple[str, bool]]] = {}
    always_prepared = ch.ruleset != "dnd-5e-2024" and ch.character_class not in PREPARED_CASTERS_2014
    for spell_id in ch.spells.known:
        spell = catalog.get(spell_id)
        if spell is None:
            v.warnings.append(f"Magia {spell_id!r} fora do catálogo: não incluída no PDF")
            continue
        prepared = always_prepared or spell_id in ch.spells.prepared
        by_level.setdefault(spell.level, []).append((spell.name, prepared))

    for level, items in by_level.items():
        items.sort(key=lambda it: it[0].lower())
        lines = SPELL_LINES[level]
        if len(items) > len(lines):
            v.warnings.append(f"Nível {level}: {len(items) - len(lines)} magia(s) não couberam na ficha")
        for (name, prepared), (name_field, box_field) in zip(items, lines):
            t[name_field] = name
            if prepared and box_field:
                v.checks.add(box_field)


def build_sheet_values(character: Character, catalog: SpellCatalog | None = None) -> SheetValues:
    values = SheetValues()
    _fill_identity(character, values)
    _fill_abilities_and_skills(character, values)
    _fill_combat(character, values)
    _fill_attacks(character, values)
    _fill_gear(character, values)
    _fill_features_and_profile(character, values)
    _fill_spellcasting(character, values, catalog or SpellCatalog())
    return values


class TemplateError(ValueError):
    pass


def _widget_name(annot) -> str | None:
    node = annot
    while node is not None:
        node = node.get_object()
        if "/T" in node:
            return str(node["/T"])
        node = node.get("/Parent")
    return None


def _is_checkbox(annot) -> bool:
    node = annot.get_object()
    ft = node.get("/FT") or (node["/Parent"].get_object().get("/FT") if "/Parent" in node else None)
    ff = int(node.get("/Ff", 0))
    return ft == "/Btn" and not (ff & 65536)


def _on_state(annot) -> str:
    states = [k for k in annot.get_object().get("/AP", {}).get("/N", {}).keys() if k != "/Off"]
    return states[0] if states else "/Yes"


def _field_node(annot):
    node = annot.get_object()
    while "/T" not in node and "/Parent" in node:
        node = node["/Parent"].get_object()
    return node


def _inherited(node, key):
    while node is not None:
        if key in node:
            return node[key]
        node = node["/Parent"].get_object() if "/Parent" in node else None
    return None


def fit_font_size(text: str, width: float, height: float, max_size: float = 10, min_size: float = 5) -> float:
    width, height = max(width - 6, 1), max(height - 4, 1)
    size = max_size
    while size > min_size:
        chars_per_line = max(1, int(width / (size * 0.52)))
        lines = sum(max(1, -(-len(line) // chars_per_line)) for line in text.split("\n"))
        if lines * size * 1.2 <= height:
            return size
        size -= 0.5
    return min_size


def _portrait_overlay(image_bytes: bytes, box_w: float, box_h: float) -> tuple[bytes, float, float]:
    from PIL import Image

    image = Image.open(io.BytesIO(image_bytes))
    image.load()
    if image.mode not in ("RGB", "L"):
        background = Image.new("RGB", image.size, "white")
        background.paste(image.convert("RGBA"), mask=image.convert("RGBA").split()[-1])
        image = background
    scale = min(box_w / image.width, box_h / image.height)
    w, h = image.width * scale, image.height * scale
    buf = io.BytesIO()
    image.save(buf, format="PDF", resolution=72 * image.width / w)
    return buf.getvalue(), w, h


def _check_template(reader) -> None:
    fields = reader.get_fields() or {}
    missing = [f for f in REQUIRED_FIELDS if f not in fields]
    if missing:
        raise TemplateError(
            "Este PDF não parece ser a ficha oficial de D&D 5e com campos de formulário "
            f"(campos ausentes: {', '.join(missing[:4])}…)."
        )


def _fill_page(writer, page, values: SheetValues) -> None:
    from pypdf.generic import NameObject, TextStringObject

    text_values: dict[str, str] = {}
    for ref in page.get("/Annots") or []:
        annot = ref.get_object()
        if annot.get("/Subtype") != "/Widget":
            continue
        field = _field_node(annot)
        name = str(field["/T"]) if "/T" in field else None
        if name is None or name == PORTRAIT_FIELD:
            continue
        if _is_checkbox(annot):
            state = NameObject(_on_state(annot) if name in values.checks else "/Off")
            annot[NameObject("/AS")] = state
            field[NameObject("/V")] = state
            if annot is not field and "/V" in annot:
                del annot["/V"]
        elif (annot.get("/FT") or _inherited(field, "/FT")) == "/Tx":
            value = values.text.get(name, "")
            text_values[name] = value
            field[NameObject("/V")] = TextStringObject(value)
            if not value and "/AP" in annot:
                del annot["/AP"]
            if int(annot.get("/Ff") or _inherited(field, "/Ff") or 0) & 4096 and value:
                x0, y0, x1, y1 = (float(n) for n in annot["/Rect"])
                size = fit_font_size(value, x1 - x0, y1 - y0, FONT_SIZES.get(name, 10))
                annot[NameObject("/DA")] = TextStringObject(f"/Helvetica {size:g} Tf 0 0 0 rg")

    if not text_values:
        return
    writer.update_page_form_field_values(page, text_values, auto_regenerate=False)
    for ref in page.get("/Annots") or []:
        annot = ref.get_object()
        if annot.get("/Subtype") != "/Widget" or _is_checkbox(annot):
            continue
        field = _field_node(annot)
        name = str(field["/T"]) if "/T" in field else None
        if name in text_values:
            field[NameObject("/V")] = TextStringObject(text_values[name])
            if annot is not field and "/V" in annot:
                del annot["/V"]


def _apply_portrait(writer, portrait: bytes, values: SheetValues) -> None:
    from pypdf import PdfReader, Transformation
    from pypdf.generic import NameObject, NumberObject

    page = writer.pages[1]
    for ref in page.get("/Annots") or []:
        annot = ref.get_object()
        if annot.get("/Subtype") != "/Widget" or _widget_name(annot) != PORTRAIT_FIELD:
            continue
        x0, y0, x1, y1 = (float(n) for n in annot["/Rect"])
        try:
            pdf_bytes, w, h = _portrait_overlay(portrait, x1 - x0, y1 - y0)
        except Exception as exc:
            values.warnings.append(f"Imagem do personagem ignorada: {exc}")
            return
        overlay = PdfReader(io.BytesIO(pdf_bytes)).pages[0]
        ow, oh = float(overlay.mediabox.width), float(overlay.mediabox.height)
        tx = x0 + ((x1 - x0) - w) / 2
        ty = y0 + ((y1 - y0) - h) / 2
        page.merge_transformed_page(overlay, Transformation().scale(w / ow, h / oh).translate(tx, ty))
        annot[NameObject("/F")] = NumberObject(2)
        return


def fill_pdf(
    template_path: str | Path,
    output_path: str | Path,
    character: Character,
    catalog: SpellCatalog | None = None,
    portrait: bytes | None = None,
) -> list[str]:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import BooleanObject, NameObject

    reader = PdfReader(str(template_path))
    _check_template(reader)
    values = build_sheet_values(character, catalog)
    writer = PdfWriter()
    writer.append(reader, pages=(0, SHEET_PAGES))
    for page in writer.pages:
        _fill_page(writer, page, values)
    if portrait:
        _apply_portrait(writer, portrait, values)
    writer._root_object["/AcroForm"][NameObject("/NeedAppearances")] = BooleanObject(True)
    with open(output_path, "wb") as fh:
        writer.write(fh)
    return values.warnings
