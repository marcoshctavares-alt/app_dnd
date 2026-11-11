import json
import re
import sys
from pathlib import Path

SCHOOLS = {
    "Abjuration": "Abjuração", "Conjuration": "Conjuração", "Divination": "Adivinhação",
    "Enchantment": "Encantamento", "Evocation": "Evocação", "Illusion": "Ilusão",
    "Necromancy": "Necromancia", "Transmutation": "Transmutação",
}
CLASSES = {
    "Bard": "Bardo", "Cleric": "Clérigo", "Druid": "Druida", "Paladin": "Paladino",
    "Ranger": "Patrulheiro", "Sorcerer": "Feiticeiro", "Warlock": "Bruxo", "Wizard": "Mago",
}
PT_NAMES = {
    "fire-bolt": "Raio de Fogo", "light": "Luz", "mage-hand": "Mão Mágica", "sacred-flame": "Chama Sagrada",
    "eldritch-blast": "Rajada Mística", "vicious-mockery": "Zombaria Viciosa", "prestidigitation": "Prestidigitação",
    "guidance": "Orientação", "magic-missile": "Mísseis Mágicos", "cure-wounds": "Curar Ferimentos",
    "bless": "Bênção", "shield": "Escudo Arcano", "sleep": "Sono", "healing-word": "Palavra Curativa",
    "burning-hands": "Mãos Flamejantes", "detect-magic": "Detectar Magia", "thunderwave": "Onda Trovejante",
    "hunters-mark": "Marca do Caçador", "hex": "Maldição", "misty-step": "Passo Nebuloso",
    "hold-person": "Imobilizar Pessoa", "invisibility": "Invisibilidade", "lesser-restoration": "Restauração Menor",
    "fireball": "Bola de Fogo", "counterspell": "Contramágica", "fly": "Voo", "revivify": "Revivificar",
    "dispel-magic": "Dissipar Magia", "polymorph": "Polimorfia", "cone-of-cold": "Cone de Frio", "wish": "Desejo",
}
UNITS = {
    "round": "rodada", "rounds": "rodadas", "minute": "minuto", "minutes": "minutos", "hour": "hora",
    "hours": "horas", "day": "dia", "days": "dias", "feet": "pés", "foot": "pé", "mile": "milha", "miles": "milhas",
}
SCH_RE = "|".join(SCHOOLS)
HEADER = re.compile(rf"^(?:Level (\d) ({SCH_RE})|({SCH_RE}) Cantrip) \(")
FOOTER = re.compile(r"^\d+ System Reference Document 5\.2\.1\s*$")
STAT_START = re.compile(r"^(Tiny|Small|Medium|Large|Huge|Gargantuan)\b[^\n]*,\s*(Lawful|Neutral|Chaotic|Unaligned|Any|Neutral Good|Neutral Evil)", re.I)


def slug(name):
    s = name.lower().replace("’", "").replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def pt_units(text):
    text = re.sub(r"\b(\d+)-foot\b", r"\1 pés", text)
    text = re.sub(r"\b(\d+)-mile\b", r"\1 milhas", text)
    return re.sub(r"\b(" + "|".join(UNITS) + r")\b", lambda m: UNITS[m.group(1)], text)


def tr_casting_time(raw):
    trigger = None
    base = raw
    ritual = False
    if re.search(r"\bor Ritual\b", base):
        ritual = True
        base = re.sub(r"\s*or Ritual\b", "", base)
    m = re.match(r"^(Bonus Action|Reaction|Action)(?:,\s*(.*))?$", base)
    if m:
        kind = {"Action": "1 ação", "Bonus Action": "1 ação bônus", "Reaction": "1 reação"}[m.group(1)]
        trigger = m.group(2)
        return kind, ritual, trigger
    base = base.replace("Bonus Action", "1 ação bônus").replace("Action", "1 ação").replace("Reaction", "1 reação")
    return pt_units(base.replace(" or ", " ou ")), ritual, None


def tr_range(raw):
    simple = {"Self": "Pessoal", "Touch": "Toque", "Sight": "Visão", "Unlimited": "Ilimitado", "Special": "Especial"}
    if raw in simple:
        return simple[raw]
    return pt_units(raw.replace("Self", "Pessoal").replace("Touch", "Toque"))


def tr_duration(raw):
    concentration = raw.startswith("Concentration")
    text = re.sub(r"^Concentration,?\s*", "", raw)
    text = text.replace("Instantaneous", "Instantânea").replace("Until dispelled or triggered", "Até ser dissipada ou ativada")
    text = text.replace("Until dispelled", "Até ser dissipada").replace("Special", "Especial")
    text = re.sub(r"\bup to\b", "até", text)
    text = re.sub(r"\bUp to\b", "Até", text)
    return pt_units(text), concentration


LABELS = (
    ("Casting Time", re.compile(r"^Casting Time:")),
    ("Range", re.compile(r"^Range:")),
    ("Components", re.compile(r"^Components?:")),
    ("Duration", re.compile(r"^Duration:")),
)


def extract_fields(body, name, diagnostics):
    starts = []
    pos = 0
    for label, pattern in LABELS:
        while pos < len(body) and not pattern.match(body[pos]):
            pos += 1
        if pos >= len(body):
            diagnostics.append(f"{name}: campo {label} ausente")
            return {}, 0
        starts.append(pos)
        pos += 1
    fields = {}
    for n, (label, _) in enumerate(LABELS):
        stop = starts[n + 1] if n + 1 < len(LABELS) else starts[n] + 1
        parts = [body[starts[n]].split(":", 1)[1].strip()] + [l.strip() for l in body[starts[n] + 1:stop]]
        fields[label] = " ".join(p for p in parts if p)
    return fields, starts[-1] + 1


def clean_lines(lines):
    out = []
    for line in lines:
        line = line.replace("\x02", "")
        if FOOTER.match(line) or line.strip() in ("System Reference Document 5.2.1", "Spell Descriptions"):
            continue
        out.append(line)
    return out


def paragraphs(lines):
    paras, buf = [], ""
    for line in lines:
        if not line.strip():
            if buf:
                paras.append(buf.strip())
                buf = ""
            continue
        buf += line if line.endswith(" ") else line + "\n"
        if not line.endswith(" "):
            paras.append(buf.strip().replace("\n", " "))
            buf = ""
    if buf:
        paras.append(buf.strip())
    return "\n".join(p for p in paras if p)


BROKEN_HYPHEN = re.compile(r"-\n(?=[a-z])")
BROKEN_LINE = re.compile(r"\n(?=[a-z])")


def join_broken_lines(text):
    return BROKEN_LINE.sub(" ", BROKEN_HYPHEN.sub("-", text))


ORPHAN_FRAGMENT = "face a choice of paths along the way there, you know which path is the most direct."
TRUNCATED_NOTE = "\n\n[Texto incompleto no arquivo-fonte do SRD usado na importação; consulte o SRD para o trecho final.]"
TRUNCATED_IN_SOURCE = ("antipathy-sympathy", "telekinesis")


def apply_source_fixes(spells):
    by_id = {sp["id"]: sp for sp in spells}
    steed, path = by_id["find-steed"], by_id["find-the-path"]
    if steed["description"].count("\n" + ORPHAN_FRAGMENT) != 1 or not path["description"].endswith("Whenever you"):
        raise SystemExit("O texto-fonte não tem o defeito conhecido de Find Steed / Find the Path; revise apply_source_fixes")
    steed["description"] = steed["description"].replace("\n" + ORPHAN_FRAGMENT, "", 1)
    path["description"] += " " + ORPHAN_FRAGMENT
    for sid in TRUNCATED_IN_SOURCE:
        by_id[sid]["description"] += TRUNCATED_NOTE


def parse(path):
    all_lines = Path(path).read_text(encoding="utf-8").split("\n")
    begin = next(i for i, l in enumerate(all_lines) if l.strip() == "Spell Descriptions" and i > 5000)
    end = next(i for i in range(begin, len(all_lines)) if all_lines[i].strip() == "Rules Glossary")
    lines = clean_lines(all_lines[begin:end])

    heads = []
    for i, line in enumerate(lines):
        if HEADER.match(line):
            j = i
            header = line
            while header.count("(") > header.count(")") and j + 1 < len(lines):
                j += 1
                header += " " + lines[j].strip()
            k = i - 1
            while not lines[k].strip():
                k -= 1
            heads.append((k, i, j, lines[k].strip(), header.strip()))

    spells, stat_blocks, diagnostics = [], [], []
    for n, (name_i, hdr_i, hdr_end, name, header) in enumerate(heads):
        block_end = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
        body = lines[hdr_end + 1:block_end]

        m = HEADER.match(header)
        cantrip = m.group(3) is not None
        level = 0 if cantrip else int(m.group(1))
        school = SCHOOLS[m.group(3) or m.group(2)]
        classes_en = [c.strip() for c in re.search(r"\((.*)\)\s*$", header).group(1).split(",")]
        classes = [CLASSES[c] for c in classes_en]

        fields, idx = extract_fields(body, name, diagnostics)
        desc_lines = body[idx:]

        cut = next((i for i, l in enumerate(desc_lines) if STAT_START.match(l)), None)
        if cut is not None:
            title_i = cut - 1
            while title_i > 0 and not desc_lines[title_i].strip():
                title_i -= 1
            stat_blocks.append({"owner_hint": name, "title": desc_lines[title_i].strip(), "text": paragraphs(desc_lines[title_i:])})
            desc_lines = desc_lines[:title_i]

        casting, ritual, trigger = tr_casting_time(fields.get("Casting Time", ""))
        duration, concentration = tr_duration(fields.get("Duration", ""))
        description = paragraphs(desc_lines)
        if trigger:
            description = f"Casting Time: {fields['Casting Time']}\n" + description

        sid = slug(name)
        spells.append({
            "id": sid, "name": PT_NAMES.get(sid, name), "name_en": name, "level": level, "school": school,
            "classes": classes, "casting_time": casting, "range": tr_range(fields.get("Range", "")),
            "components": fields.get("Components", ""), "duration": duration, "ritual": ritual,
            "concentration": concentration, "description": description, "source": "srd",
        })
    by_id = {sp["id"]: sp for sp in spells}
    for sb in stat_blocks:
        hint = by_id[slug(sb["owner_hint"])]
        owners = [hint] if sb["title"].lower() in hint["description"].lower() else [
            sp for sp in spells if sb["title"].lower() in sp["description"].lower()
        ]
        if not owners:
            diagnostics.append(f"bloco {sb['title']!r} sem magia dona")
            continue
        owners[0]["description"] += f"\n\nStat block: {sb['text']}"
        sb["owner"] = owners[0]["name_en"]
    apply_source_fixes(spells)
    for sp in spells:
        sp["description"] = join_broken_lines(sp["description"])
    return spells, stat_blocks, diagnostics


if __name__ == "__main__":
    spells, stat_blocks, diagnostics = parse(sys.argv[1])
    out = Path(sys.argv[2])
    out.write_text(json.dumps(spells, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(spells), "magias;", len(stat_blocks), "blocos de monstro;", len(diagnostics), "avisos")
    for d in diagnostics:
        print("AVISO:", d)
    for sb in stat_blocks:
        print("BLOCO:", sb["title"], "-> anexado a", sb.get("owner"), "(achado após", sb["owner_hint"] + ")")
