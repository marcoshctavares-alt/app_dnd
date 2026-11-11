import pytest

from app_dnd.data.backgrounds import BACKGROUNDS_2024
from app_dnd.data.feats import CATEGORIES, FEAT_BY_NAME, FEATS_2024, find_feat
from app_dnd.models import AbilityScores, Character, HitPoints
from app_dnd.services.backgrounds import apply_background
from app_dnd.services.feats import (
    add_feat,
    available_feats,
    increase_options,
    prerequisite_text,
    remove_feat,
    unmet_prerequisites,
)


def make(cls=None, level=1, ruleset="dnd-5e-2024", **abilities):
    return Character(
        name="T", ruleset=ruleset, character_class=cls, level=level, abilities=AbilityScores(**abilities),
        hit_points=HitPoints(current=8, maximum=8),
    )


def names(ch):
    return {f.name for f in available_feats(ch)}


def test_catalog_matches_srd_counts():
    assert len(FEATS_2024) == 19
    counts = {c: sum(f.category == c for f in FEATS_2024) for c in CATEGORIES}
    assert counts == {"Origem": 6, "Geral": 2, "Estilo de Luta": 4, "Dádiva Épica": 7}
    assert len(FEAT_BY_NAME) == len(FEATS_2024)
    assert all(f.description.strip() for f in FEATS_2024)


def test_background_feats_exist_in_catalog():
    assert all(b.feat in FEAT_BY_NAME for b in BACKGROUNDS_2024)


def test_level_one_commoner_only_gets_origin_feats():
    assert {FEAT_BY_NAME[n].category for n in names(make())} == {"Origem"}


def test_prerequisites_by_level_ability_and_class():
    assert "Aumento de Atributo" not in names(make(level=3))
    assert "Aumento de Atributo" in names(make(level=4))
    assert "Agarrador" not in names(make(level=4, strength=12, dexterity=12))
    assert "Agarrador" in names(make(level=4, dexterity=13))
    assert "Defesa" not in names(make("Mago"))
    assert "Defesa" in names(make("Guerreiro"))
    assert "Defesa" not in names(make("Paladino", level=1)) and "Defesa" in names(make("Paladino", level=2))
    assert "Dádiva do Destino" not in names(make(level=18)) and "Dádiva do Destino" in names(make(level=19))
    assert "Dádiva de Recordação de Magias" not in names(make("Guerreiro", level=20))
    assert "Dádiva de Recordação de Magias" in names(make("Mago", level=20))


def test_add_and_remove_feat_and_repeat_rules():
    ch = make()
    add_feat(ch, "Alerta")
    assert ch.feats == ["Alerta"]
    with pytest.raises(ValueError):
        add_feat(ch, "Alerta")
    add_feat(ch, "Habilidoso")
    add_feat(ch, "Habilidoso")
    assert ch.feats.count("Habilidoso") == 2
    remove_feat(ch, "Habilidoso")
    assert ch.feats == ["Alerta", "Habilidoso"]
    with pytest.raises(ValueError):
        remove_feat(ch, "Defesa")


@pytest.mark.parametrize("name", ["Inexistente", "Defesa", "Dádiva da Visão Verdadeira"])
def test_add_feat_rejects_unknown_or_unmet(name):
    ch = make("Mago")
    with pytest.raises(ValueError):
        add_feat(ch, name)
    assert ch.feats == []


def test_feats_refused_for_2014():
    ch = make(ruleset="dnd-5e-2014")
    assert available_feats(ch) == []
    with pytest.raises(ValueError):
        add_feat(ch, "Alerta")


def test_prerequisite_text_and_unmet_messages():
    assert prerequisite_text(FEAT_BY_NAME["Agarrador"]) == "nível 4+, Força ou Destreza 13+"
    assert prerequisite_text(FEAT_BY_NAME["Alerta"]) == ""
    assert unmet_prerequisites(make("Mago"), FEAT_BY_NAME["Defesa"])


def test_background_grants_its_feat_once():
    out = apply_background(make(), "Criminoso", {"dexterity": 2, "constitution": 1})
    assert out.feats == ["Alerta"]
    assert "Alerta" not in names(out)


def test_feats_survive_storage_roundtrip_and_old_data(tmp_path):
    from app_dnd.storage import Database

    db = Database(tmp_path / "t.db")
    ch = make()
    add_feat(ch, "Alerta")
    db.save_character(ch)
    assert db.list_characters()[0].feats == ["Alerta"]
    legacy = ch.model_dump(mode="json")
    legacy.pop("feats")
    assert Character.model_validate(legacy).feats == []
    db.close()


def test_increase_options_shapes():
    asi = increase_options(find_feat("Aumento de Atributo"))
    assert len(asi) == 6 + 15
    assert {"strength": 2} in asi.values() and {"strength": 1, "wisdom": 1} in asi.values()
    assert list(increase_options(find_feat("Agarrador")).values()) == [{"strength": 1}, {"dexterity": 1}]
    assert increase_options(find_feat("Alerta")) == {}
    assert len(increase_options(find_feat("Dádiva do Destino"))) == 6
    assert len(increase_options(find_feat("Dádiva de Recordação de Magias"))) == 3


def test_asi_feat_applies_increase_with_cap_20():
    ch = make(level=4, strength=19, dexterity=12)
    add_feat(ch, "Aumento de Atributo", {"strength": 1, "dexterity": 1})
    assert (ch.abilities.strength, ch.abilities.dexterity) == (20, 13)
    add_feat(ch, "Aumento de Atributo", {"strength": 2})
    assert ch.abilities.strength == 20 and ch.feats.count("Aumento de Atributo") == 2


def test_grappler_and_boon_apply_and_boon_cap_30():
    ch = make(level=19, strength=20, dexterity=14)
    add_feat(ch, "Agarrador", {"dexterity": 1})
    assert ch.abilities.dexterity == 15
    add_feat(ch, "Dádiva do Destino", {"strength": 1})
    assert ch.abilities.strength == 21
    ch.abilities = AbilityScores(strength=30)
    add_feat(ch, "Dádiva da Visão Verdadeira", {"strength": 1})
    assert ch.abilities.strength == 30


@pytest.mark.parametrize(
    "name,inc",
    [
        ("Aumento de Atributo", None),
        ("Aumento de Atributo", {"strength": 3}),
        ("Agarrador", {"wisdom": 1}),
        ("Alerta", {"strength": 1}),
        ("Dádiva de Recordação de Magias", {"strength": 1}),
    ],
)
def test_bad_increase_is_rejected_and_nothing_changes(name, inc):
    ch = make("Mago", level=20, strength=15, dexterity=15)
    before = (ch.abilities.model_copy(), list(ch.feats))
    with pytest.raises(ValueError):
        add_feat(ch, name, inc)
    assert (ch.abilities, ch.feats) == before


def test_increase_never_lowers_score_already_above_cap():
    ch = make(level=4, strength=24)
    add_feat(ch, "Aumento de Atributo", {"strength": 1, "dexterity": 1})
    assert ch.abilities.strength == 24
    out = apply_background(make(strength=22), "Soldado", {"strength": 2, "dexterity": 1})
    assert out.abilities.strength == 22
