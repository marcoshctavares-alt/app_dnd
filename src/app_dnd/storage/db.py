from __future__ import annotations

import sqlite3
from contextlib import AbstractContextManager, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from uuid import UUID

from pydantic import ValidationError

from app_dnd.models import Character, Spell

ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp"}
SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS characters (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    ruleset TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_characters_name ON characters(name);
CREATE INDEX IF NOT EXISTS idx_characters_ruleset ON characters(ruleset);
CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    mime_type TEXT NOT NULL,
    data BLOB NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS custom_spells (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: str | Path = "app_dnd.db") -> None:
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row
        self._depth = 0
        with self._tx():
            self._conn.executescript(_SCHEMA)
            if self._conn.execute("PRAGMA user_version").fetchone()[0] == 0:
                self._conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        self._depth += 1
        try:
            yield self._conn
        except BaseException:
            self._depth -= 1
            self._conn.rollback()
            raise
        self._depth -= 1
        if self._depth == 0:
            self._conn.commit()

    def transaction(self) -> AbstractContextManager[sqlite3.Connection]:
        return self._tx()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def save_character(self, character: Character, touch: bool = True) -> Character:
        if touch:
            character.updated_at = datetime.now(timezone.utc)
        with self._tx() as c:
            c.execute(
                "INSERT INTO characters (id, name, ruleset, updated_at, data) VALUES (?,?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET name=excluded.name, ruleset=excluded.ruleset, "
                "updated_at=excluded.updated_at, data=excluded.data",
                (
                    str(character.id),
                    character.name,
                    character.ruleset,
                    character.updated_at.isoformat(),
                    character.model_dump_json(),
                ),
            )
        return character

    def get_character(self, character_id: UUID) -> Character | None:
        row = self._conn.execute("SELECT data FROM characters WHERE id = ?", (str(character_id),)).fetchone()
        return Character.model_validate_json(row["data"]) if row else None

    def _read_characters(self, ruleset: str | None) -> tuple[list[Character], list[str]]:
        sql, args = "SELECT id, data FROM characters", ()
        if ruleset:
            sql, args = sql + " WHERE ruleset = ?", (ruleset,)
        valid: list[Character] = []
        invalid: list[str] = []
        for row in self._conn.execute(sql + " ORDER BY updated_at DESC", args).fetchall():
            try:
                valid.append(Character.model_validate_json(row["data"]))
            except ValidationError:
                invalid.append(row["id"])
        return valid, invalid

    def list_characters(self, ruleset: str | None = None) -> list[Character]:
        return self._read_characters(ruleset)[0]

    def invalid_character_ids(self, ruleset: str | None = None) -> list[str]:
        return self._read_characters(ruleset)[1]

    def delete_character(self, character_id: UUID) -> bool:
        character = self.get_character(character_id)
        with self._tx() as c:
            deleted = c.execute("DELETE FROM characters WHERE id = ?", (str(character_id),)).rowcount > 0
            if deleted and character and character.portrait_id:
                c.execute("DELETE FROM assets WHERE id = ?", (str(character.portrait_id),))
            return deleted

    def save_asset(self, asset_id: UUID, data: bytes, mime_type: str) -> None:
        if mime_type not in ALLOWED_MIME:
            raise ValueError(f"Tipo de imagem não suportado: {mime_type}")
        with self._tx() as c:
            c.execute(
                "INSERT OR REPLACE INTO assets (id, mime_type, data, created_at) VALUES (?,?,?,?)",
                (str(asset_id), mime_type, data, datetime.now(timezone.utc).isoformat()),
            )

    def delete_asset(self, asset_id: UUID) -> None:
        with self._tx() as c:
            c.execute("DELETE FROM assets WHERE id = ?", (str(asset_id),))

    def get_asset(self, asset_id: UUID) -> tuple[bytes, str] | None:
        row = self._conn.execute("SELECT data, mime_type FROM assets WHERE id = ?", (str(asset_id),)).fetchone()
        return (bytes(row["data"]), row["mime_type"]) if row else None

    def save_custom_spell(self, spell: Spell) -> None:
        with self._tx() as c:
            c.execute(
                "INSERT OR REPLACE INTO custom_spells (id, data) VALUES (?, ?)",
                (spell.id, spell.model_dump_json()),
            )

    def list_custom_spells(self) -> list[Spell]:
        rows = self._conn.execute("SELECT data FROM custom_spells ORDER BY id").fetchall()
        return [Spell.model_validate_json(r["data"]) for r in rows]

    def delete_custom_spell(self, spell_id: str) -> None:
        with self._tx() as c:
            c.execute("DELETE FROM custom_spells WHERE id = ?", (spell_id,))
