import json
import re
import sys
from pathlib import Path

CLASSES = {
    "Bard": "Bardo", "Cleric": "Clérigo", "Druid": "Druida", "Paladin": "Paladino",
    "Ranger": "Patrulheiro", "Sorcerer": "Feiticeiro", "Warlock": "Bruxo", "Wizard": "Mago",
}
FOOTER = re.compile(r"^\d+ System Reference Document 5\.2\.1\s*$|^System Reference Document 5\.2\.1 \d+\s*$")
ROW = re.compile(r"^(\d{1,2}) \+(\d) ")
TOKEN = re.compile(r"^(\d+|—|-)$")


def tail_numbers(text, count):
    tokens = text.split()
    out = []
    for tok in reversed(tokens):
        if not TOKEN.match(tok):
            break
        out.append(0 if tok in ("—", "-") else int(tok))
        if len(out) == count:
            break
    if len(out) < count:
        raise ValueError(f"linha sem {count} números finais: {text!r}")
    return list(reversed(out))


def find_table(lines, class_en):
    heading = f"{class_en} Features"
    start = next(i for i, l in enumerate(lines) if l.strip() == heading and any(ROW.match(x) for x in lines[i:i + 40]))
    rows, buf = [], None
    for line in lines[start:]:
        if FOOTER.match(line.strip()):
            continue
        if ROW.match(line):
            if buf is not None:
                rows.append(buf)
            buf = line.strip()
        elif buf is not None and line.strip() and not rows.__len__() == 20:
            if re.match(r"^\d+ System", line.strip()):
                continue
            buf += " " + line.strip()
        elif buf is not None and not line.strip():
            rows.append(buf)
            buf = None
            break
        if len(rows) == 20:
            break
    if buf is not None and len(rows) < 20:
        rows.append(buf)
    if len(rows) != 20:
        raise ValueError(f"{class_en}: esperava 20 linhas, achei {len(rows)}")
    return rows


def parse(path):
    lines = Path(path).read_text(encoding="utf-8").split("\n")
    result = {}
    for class_en, class_pt in CLASSES.items():
        rows = find_table(lines, class_en)
        levels = {}
        for n, row in enumerate(rows, start=1):
            assert ROW.match(row) and int(ROW.match(row).group(1)) == n, (class_en, n, row)
            if class_en == "Warlock":
                inv, cantrips, prepared, slots, slot_level = tail_numbers(row, 5)
                levels[n] = {"cantrips": cantrips, "prepared": prepared, "pact_slots": slots, "pact_slot_level": slot_level}
            elif class_en in ("Paladin", "Ranger"):
                nums = tail_numbers(row, 6)
                levels[n] = {"cantrips": 0, "prepared": nums[0], "slots": nums[1:]}
            else:
                nums = tail_numbers(row, 11)
                levels[n] = {"cantrips": nums[0], "prepared": nums[1], "slots": nums[2:]}
        result[class_pt] = levels
    return result


if __name__ == "__main__":
    data = parse(sys.argv[1])
    Path(sys.argv[2]).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(len(data), "classes;", sum(len(v) for v in data.values()), "linhas")
