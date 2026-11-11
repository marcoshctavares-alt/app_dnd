from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SUBCLASSES = {
    "Path of the Berserker": "Barbarian",
    "College of Lore": "Bard",
    "Life Domain": "Cleric",
    "Circle of the Land": "Druid",
    "Champion": "Fighter",
    "Warrior of the Open Hand": "Monk",
    "Oath of Devotion": "Paladin",
    "Hunter": "Ranger",
    "Thief": "Rogue",
    "Draconic Sorcery": "Sorcerer",
    "Fiend Patron": "Warlock",
    "Evoker": "Wizard",
}
FOOTER = re.compile(r"^\d+ System Reference Document 5\.2\.1$")
LEVEL = re.compile(r"^Level (\d+): (.+)$")


def parse(lines: list[str]) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for name, cls in SUBCLASSES.items():
        starts = [i for i, ln in enumerate(lines) if re.match(rf"^{cls} Subclass:", ln) and i > 2000]
        start = next(i for i in starts if name.split()[0] in " ".join(lines[i : i + 3]))
        end = next(
            (i for i in range(start + 1, len(lines)) if FOOTER.match(lines[i]) and not _continues(lines, i)),
            len(lines),
        )
        result[name] = _features(lines[start:end])
    return result


CLASS_WORDS = {
    "Barbarian", "Bard", "Cleric", "Druid", "Fighter", "Monk", "Paladin", "Ranger", "Rogue", "Sorcerer", "Warlock", "Wizard",
}


def _continues(lines: list[str], footer_index: int) -> bool:
    after = lines[footer_index + 1 : footer_index + 2]
    return not after or after[0].strip() not in CLASS_WORDS


def _features(block: list[str]) -> list[dict]:
    features: list[dict] = []
    for line in block:
        if FOOTER.match(line):
            continue
        if m := LEVEL.match(line):
            if features and int(m[1]) < features[-1]["level"]:
                break
            features.append({"level": int(m[1]), "name": m[2].strip(), "text": []})
        elif features:
            features[-1]["text"].append(line)
    return [{**f, "text": _trim(" ".join(f["text"]))} for f in features]


TAIL = re.compile(r"\s(?:%s) Core \w+ Traits.*$|\sCharacter Origins .*$" % "|".join(sorted(CLASS_WORDS)))


def _trim(text: str) -> str:
    return TAIL.sub("", text.replace("  ", " ")).strip()


def main(path: str, out: str) -> None:
    data = parse(Path(path).read_text(encoding="utf-8").splitlines())
    Path(out).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    for name, feats in data.items():
        print(name, [(f["level"], f["name"], len(f["text"])) for f in feats])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
