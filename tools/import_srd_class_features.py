from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CLASSES = ["Barbarian", "Bard", "Cleric", "Druid", "Fighter", "Monk", "Paladin", "Ranger", "Rogue", "Sorcerer", "Warlock", "Wizard"]
FOOTER = re.compile(r"^\d+ System Reference Document 5\.2\.1$")
LEVEL = re.compile(r"^Level (\d+): (.+)$")
TAIL = re.compile(r"\s(?:%s)\s+Core \w+ Traits.*$" % "|".join(CLASSES))


def class_ranges(lines: list[str]) -> dict[str, tuple[int, int]]:
    starts = {}
    for i, line in enumerate(lines):
        if m := re.match(r"^Core (\w+) Traits$", line):
            starts.setdefault(m[1], i)
    names = [c for c in CLASSES if c in starts]
    ranges = {}
    for n, name in enumerate(names):
        end = starts[names[n + 1]] - 2 if n + 1 < len(names) else len(lines)
        subclass = next(
            (i for i in range(starts[name], end) if re.match(rf"^{name} Subclass:", lines[i])), end
        )
        ranges[name] = (starts[name], subclass)
    return ranges


def features(block: list[str]) -> list[dict]:
    found: list[dict] = []
    for line in block:
        if FOOTER.match(line):
            continue
        if m := LEVEL.match(line):
            found.append({"level": int(m[1]), "name": m[2].strip(), "text": []})
        elif found:
            found[-1]["text"].append(line)
    return [{**f, "text": TAIL.sub("", " ".join(f["text"])).replace("  ", " ").strip()} for f in found]


EXTRA_ASI = {"Fighter": (6, 14), "Rogue": (10,)}


def add_repeated_asi(name: str, feats: list[dict]) -> list[dict]:
    base = next(f for f in feats if f["name"] == "Ability Score Improvement")
    extra = [{**base, "level": lv} for lv in (8, 12, 16, *EXTRA_ASI.get(name, ()))]
    return sorted([*feats, *extra], key=lambda f: f["level"])


def main(path: str, out: str) -> None:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    data = {name: add_repeated_asi(name, features(lines[a:b])) for name, (a, b) in class_ranges(lines).items()}
    Path(out).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    for name, feats in data.items():
        print(name, len(feats), [(f["level"], f["name"]) for f in feats])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
