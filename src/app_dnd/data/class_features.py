from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources


@dataclass(frozen=True)
class ClassFeature:
    level: int
    name: str
    name_en: str
    text: str


def _load() -> dict[str, tuple[ClassFeature, ...]]:
    raw = json.loads(resources.files("app_dnd.data").joinpath("class_features_2024.json").read_text("utf-8"))
    return {cls: tuple(ClassFeature(**item) for item in items) for cls, items in raw.items()}


CLASS_FEATURES_2024: dict[str, tuple[ClassFeature, ...]] = _load()
