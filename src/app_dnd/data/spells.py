import json
from importlib import resources

from app_dnd.models import Spell


def _read(name: str):
    return json.loads(resources.files("app_dnd.data").joinpath(name).read_text(encoding="utf-8"))


def _load() -> tuple[Spell, ...]:
    translations = _read("srd_spells_pt.json")
    return tuple(
        Spell.model_validate({**item, "description_pt": translations.get(item["id"])}) for item in _read("srd_spells.json")
    )


SRD_SPELLS: tuple[Spell, ...] = _load()
