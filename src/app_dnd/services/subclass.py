from __future__ import annotations

from app_dnd.data.class_features import CLASS_FEATURES_2024, ClassFeature
from app_dnd.data.subclass_features import SUBCLASS_FEATURES_2024, SubclassFeature
from app_dnd.models import Character


def subclass_features(character: Character) -> tuple[SubclassFeature, ...]:
    if character.ruleset != "dnd-5e-2024" or not character.subclass:
        return ()
    return SUBCLASS_FEATURES_2024.get(character.subclass, ())


def unlocked_features(character: Character) -> list[SubclassFeature]:
    return [f for f in subclass_features(character) if f.level <= character.level]


SKIPPED_IN_SUMMARY = {"Aumento de Atributo", "Escolha da subclasse", "Dádiva Épica"}


def class_features(character: Character) -> tuple[ClassFeature, ...]:
    if character.ruleset != "dnd-5e-2024":
        return ()
    return CLASS_FEATURES_2024.get(character.character_class or "", ())


def class_feature_summary(character: Character) -> list[str]:
    seen: set[str] = set()
    names = []
    for feature in class_features(character):
        if feature.level <= character.level and feature.name not in SKIPPED_IN_SUMMARY and feature.name not in seen:
            seen.add(feature.name)
            names.append(f"{feature.name} ({feature.level})")
    return names
