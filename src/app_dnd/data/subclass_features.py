from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources


@dataclass(frozen=True)
class SubclassFeature:
    level: int
    name: str
    name_en: str
    text: str


def _load() -> dict[str, tuple[SubclassFeature, ...]]:
    raw = json.loads(resources.files("app_dnd.data").joinpath("subclass_features_2024.json").read_text("utf-8"))
    return {name: tuple(SubclassFeature(**item) for item in items) for name, items in raw.items()}


SUBCLASS_FEATURES_2024: dict[str, tuple[SubclassFeature, ...]] = _load()
