import json
from importlib import resources


def _load() -> dict[str, dict[int, dict]]:
    raw = resources.files("app_dnd.data").joinpath("spellcasting_2024.json").read_text(encoding="utf-8")
    return {cls: {int(level): row for level, row in rows.items()} for cls, rows in json.loads(raw).items()}


SPELLCASTING_2024: dict[str, dict[int, dict]] = _load()


def cantrips_known(class_name: str | None, level: int) -> int | None:
    row = SPELLCASTING_2024.get(class_name or "", {}).get(level)
    return row["cantrips"] if row else None


def prepared_spells(class_name: str | None, level: int) -> int | None:
    row = SPELLCASTING_2024.get(class_name or "", {}).get(level)
    return row["prepared"] if row else None
