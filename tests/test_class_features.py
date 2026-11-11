from app_dnd.data.class_features import CLASS_FEATURES_2024
from app_dnd.data.srd import CLASSES
from app_dnd.models import Character, HitPoints
from app_dnd.pdf.sheet_export import build_sheet_values
from app_dnd.services.subclass import class_feature_summary, class_features

R24 = "dnd-5e-2024"


def make(cls, level, ruleset=R24):
    return Character(
        name="T", ruleset=ruleset, character_class=cls, level=level, hit_points=HitPoints(current=8, maximum=8)
    )


def test_every_class_has_ordered_features_from_level_one():
    assert set(CLASS_FEATURES_2024) == {c.name for c in CLASSES}
    for name, features in CLASS_FEATURES_2024.items():
        levels = [f.level for f in features]
        assert levels == sorted(levels) and levels[0] == 1 and levels[-1] >= 19, name
        assert all(f.name.strip() and f.name_en.strip() for f in features)
        assert sum(f.name == "Escolha da subclasse" for f in features) == 1


def test_asi_levels_follow_class_tables():
    def asi(cls):
        return [f.level for f in CLASS_FEATURES_2024[cls] if f.name == "Aumento de Atributo"]

    assert asi("Mago") == [4, 8, 12, 16]
    assert asi("Guerreiro") == [4, 6, 8, 12, 14, 16]
    assert asi("Ladino") == [4, 8, 10, 12, 16]


def test_known_features_at_expected_levels():
    def at(cls, name):
        return [f.level for f in CLASS_FEATURES_2024[cls] if f.name == name]

    assert at("Bárbaro", "Fúria") == [1] and at("Bárbaro", "Ataque Extra") == [5]
    assert at("Ladino", "Especialização") == [1, 6]
    assert at("Feiticeiro", "Metamagia") == [2, 10, 17]
    assert at("Bruxo", "Arcana Mística") == [11, 13, 15, 17]


def test_features_only_for_2024_and_known_class():
    assert class_features(make("Mago", 5, "dnd-5e-2014")) == ()
    assert class_features(make(None, 5)) == ()


def test_summary_is_level_filtered_deduplicated_and_without_noise():
    summary = class_feature_summary(make("Ladino", 6))
    assert "Ataque Furtivo (1)" in summary and "Ação Ardilosa (2)" in summary
    assert sum(s.startswith("Especialização") for s in summary) == 1
    assert not any(s.startswith(("Aumento", "Escolha")) for s in summary)
    assert all("Uncanny" not in s and "(7)" not in s for s in summary)


def test_pdf_includes_class_feature_summary():
    text = build_sheet_values(make("Monge", 5)).text["features-and-traits"]
    assert "Características de classe:" in text and "Artes Marciais (1)" in text and "Ataque Extra (5)" in text


def test_pdf_lists_remaining_class_resources():
    from app_dnd.services.rests import use_resource

    ch = make("Bárbaro", 3)
    use_resource(ch, "rage")
    text = build_sheet_values(ch).text["features-and-traits"]
    assert "Recursos: Fúrias 2/3" in text
    assert "Recursos:" not in build_sheet_values(make("Ladino", 3)).text["features-and-traits"]


def test_every_class_feature_has_a_portuguese_description():
    import re

    for cls, features in CLASS_FEATURES_2024.items():
        for f in features:
            assert len(f.text) >= 30, (cls, f.name)
            assert not re.search(r"\b(the|your|you|can|which)\b", f.text), (cls, f.name)
