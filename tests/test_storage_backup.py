import json
from uuid import uuid4

import pytest

from app_dnd.backup import BackupError, export_backup, import_backup
from app_dnd.models import Character, HitPoints, Spell
from app_dnd.storage import Database

PNG = b"\x89PNG\r\n\x1a\nfake"


def make(name="Thalia", ruleset="dnd-5e-2024", **kw):
    return Character(name=name, ruleset=ruleset, hit_points=HitPoints(current=8, maximum=8), **kw)


@pytest.fixture
def db():
    with Database(":memory:") as d:
        yield d


def test_save_get_update_delete(db):
    c = db.save_character(make())
    assert db.get_character(c.id) == c
    c.level = 5
    db.save_character(c)
    assert db.get_character(c.id).level == 5 and len(db.list_characters()) == 1
    assert db.delete_character(c.id) is True and db.get_character(c.id) is None
    assert db.delete_character(c.id) is False


def test_filter_by_ruleset(db):
    db.save_character(make(ruleset="dnd-5e-2014"))
    db.save_character(make(ruleset="dnd-5e-2024"))
    db.save_character(make(ruleset="dnd-5e-2024"))
    assert len(db.list_characters("dnd-5e-2024")) == 2


def test_assets_roundtrip_and_mime_check(db):
    aid = uuid4()
    db.save_asset(aid, PNG, "image/png")
    assert db.get_asset(aid) == (PNG, "image/png")
    with pytest.raises(ValueError):
        db.save_asset(uuid4(), b"x", "application/pdf")


def test_backup_roundtrip_with_image_preserves_data():
    src = Database(":memory:")
    aid = uuid4()
    src.save_asset(aid, PNG, "image/png")
    ch = src.save_character(make(portrait_id=aid))
    raw = export_backup(src)

    dst = Database(":memory:")
    assert import_backup(dst, raw).imported == 1
    restored = dst.get_character(ch.id)
    assert restored == ch
    assert dst.get_asset(aid) == (PNG, "image/png")


@pytest.mark.parametrize(
    "raw",
    [
        "não é json",
        json.dumps({"app": "outro"}),
        json.dumps({"app": "APP_DND", "format_version": 99}),
        json.dumps({"app": "APP_DND", "format_version": 1, "characters": [{"name": ""}]}),
    ],
)
def test_invalid_backup_is_rejected_atomically(db, raw):
    with pytest.raises(BackupError):
        import_backup(db, raw)
    assert db.list_characters() == []


def backup_with(db, **extra):
    payload = json.loads(export_backup(db))
    payload.update(extra)
    return json.dumps(payload)


def asset_entry(data=PNG, mime="image/png"):
    import base64

    return {"id": str(uuid4()), "mime_type": mime, "data_b64": base64.b64encode(data).decode()}


def test_backup_rejects_bad_images_with_backup_error(db):
    src = Database(":memory:")
    src.save_character(make())
    for entry in (
        asset_entry(b"<script>alert(1)</script>", "text/html"),
        asset_entry(b"nao sou png", "image/png"),
        asset_entry(PNG, "image/jpeg"),
        asset_entry(b"", "image/png"),
        asset_entry(PNG + b"0" * (5 * 1024 * 1024 + 1), "image/png"),
    ):
        with pytest.raises(BackupError):
            import_backup(db, backup_with(src, assets=[entry]))
    assert db.list_characters() == []


def test_backup_import_is_atomic_when_a_write_fails(db, monkeypatch):
    src = Database(":memory:")
    src.save_character(make("A"))
    src.save_character(make("B"))
    src.save_custom_spell(Spell(
            id="x", name="X", level=1, school="Evocação", casting_time="1 ação", range="Pessoal",
            components="V", duration="Instantânea",
        ))
    raw = backup_with(src, assets=[asset_entry()])
    real = db.save_character
    calls = []

    def flaky(character, touch=True):
        calls.append(character.name)
        if len(calls) == 2:
            raise ValueError("falha simulada")
        return real(character, touch)

    monkeypatch.setattr(db, "save_character", flaky)
    with pytest.raises(BackupError):
        import_backup(db, raw)
    assert db.list_characters() == [] and db.list_custom_spells() == []
    assert db._conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0] == 0


def test_backup_does_not_overwrite_newer_characters_unless_asked(db):
    c = db.save_character(make("Antigo"))
    raw = export_backup(db)
    c.name = "Novo"
    db.save_character(c)
    result = import_backup(db, raw)
    assert (result.imported, result.skipped_newer) == (0, 1)
    assert db.get_character(c.id).name == "Novo"
    result = import_backup(db, raw, overwrite_newer=True)
    assert (result.imported, result.skipped_newer) == (1, 0)
    assert db.get_character(c.id).name == "Antigo"


def test_backup_imports_new_and_same_age_characters(db):
    db.save_character(make("Mesmo"))
    raw = export_backup(db)
    assert import_backup(db, raw).imported == 1
    other = Database(":memory:")
    result = import_backup(other, raw)
    assert (result.imported, result.skipped_newer) == (1, 0)


def test_corrupt_rows_are_skipped_and_reported(db):
    good = db.save_character(make("Boa"))
    bad_id = str(uuid4())
    db._conn.execute(
        "INSERT INTO characters VALUES (?,?,?,?,?)", (bad_id, "X", "dnd-5e-2024", "2026-01-01T00:00:00+00:00", '{"name": ""}')
    )
    db._conn.commit()
    assert [c.id for c in db.list_characters()] == [good.id]
    assert db.invalid_character_ids() == [bad_id]
    assert db._conn.execute("SELECT COUNT(*) FROM characters").fetchone()[0] == 2
    assert [c["name"] for c in json.loads(export_backup(db))["characters"]] == ["Boa"]


def test_nested_transactions_roll_back_together(db):
    with pytest.raises(RuntimeError):
        with db.transaction():
            db.save_character(make("Dentro"))
            with db.transaction():
                db.save_character(make("Mais dentro"))
            raise RuntimeError
    assert db.list_characters() == []
    with db.transaction():
        db.save_character(make("A"))
        db.save_character(make("B"))
    assert len(db.list_characters()) == 2
