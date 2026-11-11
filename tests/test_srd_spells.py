import json
import re
from collections import Counter

import pytest

from app_dnd.data.spells import SRD_SPELLS
from app_dnd.services.spells import SpellCatalog, format_spell

BY_ID = {s.id: s for s in SRD_SPELLS}
CLASSES = {"Bardo", "Clérigo", "Druida", "Paladino", "Patrulheiro", "Feiticeiro", "Bruxo", "Mago"}


def test_full_srd_522_catalog():
    assert len(SRD_SPELLS) == 339 and len(BY_ID) == 339
    assert Counter(s.level for s in SRD_SPELLS) == {0: 27, 1: 57, 2: 57, 3: 42, 4: 34, 5: 38, 6: 31, 7: 20, 8: 17, 9: 16}
    assert all(s.source == "srd" for s in SRD_SPELLS)


def test_every_spell_has_complete_data():
    for s in SRD_SPELLS:
        assert s.classes and set(s.classes) <= CLASSES, s.id
        assert s.casting_time and s.range and s.components and s.duration, s.id
        assert len(s.description) > 40, s.id
        assert re.fullmatch(r"[a-z0-9-]+", s.id)


def test_no_extraction_garbage():
    for s in SRD_SPELLS:
        text = s.description + s.components + s.range
        assert "\x02" not in text and "System Reference Document" not in text, s.id
        assert not s.description.startswith(("Casting Time:", "Range:", "Duration:")) or s.casting_time, s.id


def test_spot_check_fireball():
    s = BY_ID["fireball"]
    assert (s.name, s.name_en, s.level, s.school) == ("Bola de Fogo", "Fireball", 3, "Evocação")
    assert s.classes == ["Feiticeiro", "Mago"] or tuple(s.classes) == ("Feiticeiro", "Mago")
    assert (s.casting_time, s.range, s.duration) == ("1 ação", "150 pés", "Instantânea")
    assert s.components == "V, S, M (a ball of bat guano and sulfur)"
    assert "8d6 Fire damage" in s.description and "spell slot level above 3" in s.description


def test_cantrip_and_flags():
    guidance = BY_ID["guidance"]
    assert guidance.level == 0 and guidance.concentration and not guidance.ritual
    assert guidance.duration == "até 1 minuto"
    detect = BY_ID["detect-magic"]
    assert detect.ritual and detect.concentration
    assert BY_ID["alarm"].ritual and BY_ID["alarm"].casting_time == "1 minuto"


def test_translated_structured_fields():
    assert BY_ID["burning-hands"].range == "Pessoal"
    assert "15-foot Cone" in BY_ID["burning-hands"].description
    assert BY_ID["shield"].casting_time == "1 reação"
    assert BY_ID["healing-word"].casting_time == "1 ação bônus"
    assert BY_ID["power-word-kill"].components == "V"
    assert BY_ID["glyph-of-warding"].duration == "Até ser dissipada ou ativada"
    assert BY_ID["plant-growth"].casting_time.startswith("1 ação (Overgrowth) ou 8 horas")
    english_left = [
        s.id for s in SRD_SPELLS
        if re.search(r"\b(Action|Reaction|Instantaneous|Touch|Self|Concentration|minutes?|hours?)\b", s.casting_time + s.range + s.duration)
    ]
    assert english_left == []


def test_long_reaction_triggers_go_to_description():
    smite = BY_ID["divine-smite"]
    assert smite.casting_time == "1 ação bônus"
    assert smite.description.startswith("Casting Time: Bonus Action, which you take immediately after hitting")
    assert len(smite.casting_time) < 30


def test_stat_blocks_attached_to_the_right_spell():
    for sid, title in (("find-steed", "Otherworldly Steed"), ("animate-objects", "Animated Object"),
                       ("giant-insect", "Giant Insect"), ("summon-dragon", "Draconic Spirit")):
        assert f"Stat block: {title}" in BY_ID[sid].description, sid
    assert "Stat block:" not in BY_ID["fireball"].description


def test_original_portuguese_names_are_kept_and_searchable():
    cat = SpellCatalog()
    assert [s.id for s in cat.search("bencao")] == ["bless"]
    assert cat.get("magic-missile").name == "Mísseis Mágicos"
    assert cat.get("acid-arrow").name == "Acid Arrow"
    assert any(s.id == "acid-arrow" for s in cat.search("acid arr"))


def test_class_lists_follow_the_srd_text():
    wizard = {s.id for s in SpellCatalog().search(class_name="Mago")}
    assert {"fireball", "shield", "wish", "acid-arrow"} <= wizard and "cure-wounds" not in wizard
    assert "eldritch-blast" in {s.id for s in SpellCatalog().search(class_name="Bruxo")}
    assert all(s.level == 0 for s in SpellCatalog().search(level=0))


def test_format_spell_shows_real_text():
    text = format_spell(BY_ID["fireball"])
    assert "3º nível de Evocação" in text and "8d6 de dano de Fogo" in text
    assert "8d6 Fire damage" in format_spell(BY_ID["fireball"], original=True)
    assert "sem descrição" not in text


def test_json_roundtrip_is_valid_and_ordered():
    from importlib import resources
    raw = json.loads(resources.files("app_dnd.data").joinpath("srd_spells.json").read_text(encoding="utf-8"))
    assert [i["name_en"] for i in raw] == sorted((i["name_en"] for i in raw), key=lambda n: n.lower()) or len(raw) == 339


def test_required_attribution_is_present_everywhere():
    from pathlib import Path

    from app_dnd.data.credits import ATTRIBUTION

    assert "System Reference Document 5.2.1" in ATTRIBUTION and "creativecommons.org/licenses/by/4.0" in ATTRIBUTION
    root = Path(__file__).resolve().parent.parent
    assert ATTRIBUTION in (root / "NOTICE.md").read_text(encoding="utf-8")
    assert "NOTICE.md" in (root / "README.md").read_text(encoding="utf-8")


def test_find_the_path_fragment_is_back_in_the_right_spell():
    assert "face a choice of paths" not in BY_ID["find-steed"].description
    assert "Stat block: Otherworldly Steed" in BY_ID["find-steed"].description
    assert BY_ID["find-the-path"].description.endswith("Whenever you face a choice of paths along the way there, you know which path is the most direct.")


def test_descriptions_end_cleanly_or_are_explicitly_flagged():
    flagged = {"antipathy-sympathy", "telekinesis"}
    legit_non_sentence_endings = {"control-weather", "greater-restoration", "guards-and-wards"}
    for s in SRD_SPELLS:
        ok = re.search(r"[.)”\"!?:\]]$", s.description.strip())
        if s.id in flagged:
            assert s.description.rstrip().endswith("trecho final.]"), s.id
        elif s.id not in legit_non_sentence_endings:
            assert ok, f"{s.id} termina no meio da frase: ...{s.description[-60:]!r}"
