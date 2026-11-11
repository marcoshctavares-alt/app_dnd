import json
import re
import sys
from importlib import resources
from pathlib import Path

from app_dnd.data.spells import SRD_SPELLS
from app_dnd.services.spells import SpellCatalog, format_spell

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from import_srd_spells import TRUNCATED_NOTE, join_broken_lines

PT = json.loads(resources.files("app_dnd.data").joinpath("srd_spells_pt.json").read_text(encoding="utf-8"))
EN = {s.id: s.description for s in SRD_SPELLS}
LINE_EXCEPTIONS = {"antilife-shell"}


def numbers(text):
    return sorted(re.findall(r"\d+d\d+|\d+", text))


def test_every_srd_spell_has_a_translation():
    assert set(PT) == set(EN)
    assert all(s.description_pt for s in SRD_SPELLS)


def test_translations_keep_numbers_and_structure():
    for sid, original in EN.items():
        translated = PT[sid]
        if sid in {"antipathy-sympathy", "telekinesis"}:
            original, translated = original.replace(TRUNCATED_NOTE, ""), translated.replace(TRUNCATED_NOTE, "")
        missing = [n for n in set(numbers(original)) if numbers(original).count(n) > numbers(translated).count(n)]
        assert not missing, (sid, missing)
        assert translated.count("•") == original.count("•"), sid
        if sid not in LINE_EXCEPTIONS:
            assert translated.count("\n") == original.count("\n"), sid
        assert len(translated) > 0.7 * len(original), sid


def test_translations_have_no_leftover_english_rules_terms():
    text = "\n".join(PT.values())
    for term in ("saving throw", "Hit Points", "spell slot", "Bonus Action", "Long Rest", "within range"):
        assert term not in text, term


def test_no_stray_line_breaks_in_either_language():
    for source in (EN, PT):
        for sid, text in source.items():
            assert not re.search(r"\n[a-zà-ú.,;]", text), sid


def test_join_broken_lines():
    assert join_broken_lines("a 10-\nfoot square") == "a 10-foot square"
    assert join_broken_lines("the\nspell") == "the spell"
    assert join_broken_lines("end.\nNew paragraph\n1 Red") == "end.\nNew paragraph\n1 Red"


def test_guards_and_wards_is_complete():
    text = EN["guards-and-wards"]
    assert text.endswith("receives the suggestion mentally")
    for part in ("Corridors.", "Doors.", "Stairs.", "Other Spell Effect.", "Gust of Wind", "Magic Mouth"):
        assert part in text
    assert PT["guards-and-wards"].count("\n") == text.count("\n")


def test_format_spell_prefers_portuguese_and_can_show_original():
    spell = SpellCatalog().get("fireball")
    assert "salvaguarda de Destreza" in format_spell(spell)
    assert "Dexterity saving throw" not in format_spell(spell)
    assert "Dexterity saving throw" in format_spell(spell, original=True)


def test_format_spell_falls_back_to_english_without_translation():
    spell = SpellCatalog().get("fireball").model_copy(update={"description_pt": None})
    assert "Dexterity saving throw" in format_spell(spell)
