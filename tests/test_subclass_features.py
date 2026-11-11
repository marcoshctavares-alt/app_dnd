import random
import re

from app_dnd.data.srd import CLASSES
from app_dnd.data.subclass_features import SUBCLASS_FEATURES_2024
from app_dnd.models import Character, HitPoints
from app_dnd.pdf.sheet_export import build_sheet_values
from app_dnd.services.generator import random_character
from app_dnd.services.subclass import subclass_features, unlocked_features

R24, R14 = "dnd-5e-2024", "dnd-5e-2014"


def make(subclass, level, ruleset=R24):
    return Character(
        name="T", ruleset=ruleset, subclass=subclass, level=level, hit_points=HitPoints(current=8, maximum=8)
    )


def test_every_2024_subclass_has_ordered_features():
    names = {c.subclass_for(R24)[0] for c in CLASSES}
    assert names == set(SUBCLASS_FEATURES_2024)
    for name, features in SUBCLASS_FEATURES_2024.items():
        levels = [f.level for f in features]
        assert levels == sorted(levels) and levels[0] == 3 and levels[-1] <= 20, name
        assert all(f.text.strip() and f.name.strip() and f.name_en.strip() for f in features)
        assert not any(re.search(r"\b(you|your)\b", f.text) for f in features), name


def test_unlocked_features_follow_level():
    assert unlocked_features(make("Campeão", 2)) == []
    assert [f.name_en for f in unlocked_features(make("Campeão", 3))] == ["Improved Critical", "Remarkable Athlete"]
    assert len(unlocked_features(make("Campeão", 20))) == len(SUBCLASS_FEATURES_2024["Campeão"]) == 6


def test_features_only_for_2024_and_known_subclass():
    assert subclass_features(make("Campeão", 10, R14)) == ()
    assert subclass_features(make(None, 10)) == ()
    assert subclass_features(make("Inventada", 10)) == ()


def test_random_2024_characters_have_matching_features():
    for seed in range(100):
        ch = random_character(level=10, rng=random.Random(seed))
        assert ch.subclass in SUBCLASS_FEATURES_2024
        assert unlocked_features(ch)


def test_pdf_lists_unlocked_subclass_features():
    text = build_sheet_values(make("Ladrão", 9)).text["features-and-traits"]
    assert "Mãos Rápidas (3)" in text and "Furtividade Suprema (9)" in text
    assert "Usar Dispositivo Mágico" not in text
    assert "Características da subclasse" not in build_sheet_values(make("Ladrão", 2)).text["features-and-traits"]
