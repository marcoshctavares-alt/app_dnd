import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_srd_spells import clean_lines, join_broken_lines, paragraphs

CLASSES = {
    "Barbarian": "Bárbaro", "Bard": "Bardo", "Cleric": "Clérigo", "Druid": "Druida", "Fighter": "Guerreiro",
    "Monk": "Monge", "Paladin": "Paladino", "Ranger": "Patrulheiro", "Rogue": "Ladino", "Sorcerer": "Feiticeiro",
    "Warlock": "Bruxo", "Wizard": "Mago",
}
ASI_LEVELS = {"Guerreiro": (6, 8, 12, 14, 16), "Ladino": (8, 10, 12, 16)}
ASI_DEFAULT = (8, 12, 16)
REPEATS = {
    "Bardo": ((9, "Expertise"),),
    "Ladino": ((6, "Expertise"),),
    "Feiticeiro": ((10, "Metamagic"), (17, "Metamagic")),
    "Bruxo": ((13, "Mystic Arcanum"), (15, "Mystic Arcanum"), (17, "Mystic Arcanum")),
    "Guerreiro": ((17, "Action Surge"), (17, "Indomitable")),
}
FEATURE = re.compile(r"^Level (\d{1,2}): (.+)$")


def parse(path):
    lines = clean_lines(Path(path).read_text(encoding="utf-8").split("\n"))
    cores = {}
    for i, line in enumerate(lines):
        m = re.fullmatch(r"Core ([A-Z][a-z]+) Traits", line)
        if m and m[1] in CLASSES and i > 2000:
            cores[m[1]] = i
    order = sorted(cores.items(), key=lambda kv: kv[1])
    stop_after_wizard = next(i for i in range(order[-1][1], len(lines)) if lines[i] == "Character Origins" and i > order[-1][1])
    result, problems = {}, []
    for n, (cls, start) in enumerate(order):
        end = order[n + 1][1] if n + 1 < len(order) else stop_after_wizard
        stoppers = re.compile(rf"^(?:{cls} Spell List|{cls} Subclass:.*|Core [A-Z][a-z]+ Traits)$")
        marks = [i for i in range(start, end) if FEATURE.match(lines[i]) or stoppers.match(lines[i])]
        features, subclass_name, subclass_features = [], None, []
        target = features
        for k, i in enumerate(marks):
            line = lines[i]
            if stoppers.match(line):
                if line.startswith(f"{cls} Subclass:"):
                    name = line.split(":", 1)[1].strip()
                    j = i + 1
                    while not name or lines[j - 1].endswith(" ") or lines[j - 1].endswith(":"):
                        name = (name + " " + lines[j].strip()).strip()
                        j += 1
                        if not lines[j - 1].endswith(" "):
                            break
                    subclass_name = name
                    target = subclass_features
                continue
            level, title = FEATURE.match(line).groups()
            stop = next((m for m in marks[k + 1:]), end)
            body = lines[i + 1:stop]
            target.append({"level": int(level), "name": title.strip(), "text": join_broken_lines(paragraphs(body))})
        pt = CLASSES[cls]
        known = {f["name"] for f in features}
        extra = [(lvl, "Ability Score Improvement") for lvl in ASI_LEVELS.get(pt, ASI_DEFAULT)] + list(REPEATS.get(pt, ()))
        for lvl, title in extra:
            if title not in known:
                problems.append(f"{cls}: repetição sem característica original ({title})")
            features.append({"level": lvl, "name": title, "text": "", "repeat": True})
        features.sort(key=lambda f: (f["level"], f.get("repeat", False)))
        result[pt] = {"features": features, "subclass": {"name": subclass_name, "features": subclass_features}}
        if not subclass_name or len(features) < 8:
            problems.append(cls)
    return result, problems


if __name__ == "__main__":
    data, problems = parse(sys.argv[1])
    Path(sys.argv[2]).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(data), "classes;", sum(len(c["features"]) + len(c["subclass"]["features"]) for c in data.values()), "características")
    for p in problems:
        print("AVISO:", p)
