import random
from uuid import uuid4

import pytest

from app_dnd.data.srd import CLASS_BY_NAME, CLASSES
from app_dnd.models import ability_modifier
from app_dnd.services.generator import (
    assign_scores,
    hit_points_for,
    random_character,
    roll_ability_scores,
)
from app_dnd.services.portrait import MAX_BYTES, clear_portrait, set_portrait, sniff_mime
from app_dnd.services.sheet import new_character
from app_dnd.storage import Database

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20
JPG = b"\xff\xd8\xff\xe0" + b"0" * 20
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"0" * 20


def test_ability_scores_in_range_and_sorted():
    for seed in range(50):
        scores = roll_ability_scores(random.Random(seed))
        assert len(scores) == 6 and scores == sorted(scores, reverse=True)
        assert all(3 <= s <= 18 for s in scores)


def test_primary_stat_gets_highest_score():
    wizard = CLASS_BY_NAME["Mago"]
    ab = assign_scores([8, 15, 12, 10, 14, 13], wizard)
    assert ab.intelligence == 15 and ab.constitution == 14 and ab.dexterity == 13


@pytest.mark.parametrize("level,expected", [(1, 12), (2, 12 + 7), (5, 12 + 7 * 4)])
def test_hp_barbarian_con_10(level, expected):
    assert hit_points_for(CLASS_BY_NAME["Bárbaro"], level, 10) == expected


def test_hp_has_minimum_one_per_level():
    assert hit_points_for(CLASS_BY_NAME["Mago"], 3, 1) >= 3


def test_random_characters_are_always_valid_and_consistent():
    for seed in range(300):
        ch = random_character(rng=random.Random(seed))
        info = CLASS_BY_NAME[ch.character_class]
        assert ch.hit_points.current == ch.hit_points.maximum >= 1
        name, level = info.subclass_for(ch.ruleset)
        assert (ch.subclass is not None) == (ch.level >= level)
        assert ch.subclass in (None, name)


def test_random_character_is_reproducible_with_seed():
    a = random_character(level=5, rng=random.Random(42))
    b = random_character(level=5, rng=random.Random(42))
    assert a.model_dump(exclude={"id", "created_at", "updated_at"}) == b.model_dump(
        exclude={"id", "created_at", "updated_at"}
    )


def test_random_character_rejects_bad_level():
    with pytest.raises(ValueError):
        random_character(level=0)


def test_all_classes_reachable():
    seen = {random_character(level=1, rng=random.Random(s)).character_class for s in range(400)}
    assert seen == {c.name for c in CLASSES}


@pytest.mark.parametrize("data,mime", [(PNG, "image/png"), (JPG, "image/jpeg"), (WEBP, "image/webp")])
def test_sniff_mime(data, mime):
    assert sniff_mime(data) == mime


def test_sniff_rejects_other_content():
    with pytest.raises(ValueError):
        sniff_mime(b"%PDF-1.7 ...")


def test_set_replace_and_clear_portrait_manages_assets():
    db = Database(":memory:")
    ch = db.save_character(new_character())
    ch = set_portrait(db, ch, PNG)
    first = ch.portrait_id
    assert db.get_asset(first) == (PNG, "image/png")

    ch = set_portrait(db, ch, JPG)
    assert ch.portrait_id != first and db.get_asset(first) is None

    second = ch.portrait_id
    ch = clear_portrait(db, ch)
    assert ch.portrait_id is None and db.get_asset(second) is None


def test_portrait_validation():
    db = Database(":memory:")
    ch = db.save_character(new_character())
    with pytest.raises(ValueError):
        set_portrait(db, ch, b"")
    with pytest.raises(ValueError):
        set_portrait(db, ch, PNG + b"0" * MAX_BYTES)
    with pytest.raises(ValueError):
        set_portrait(db, ch, b"texto qualquer")
    assert ch.portrait_id is None


def test_deleting_character_removes_its_portrait():
    db = Database(":memory:")
    ch = set_portrait(db, db.save_character(new_character()), PNG)
    pid = ch.portrait_id
    assert db.delete_character(ch.id) and db.get_asset(pid) is None
