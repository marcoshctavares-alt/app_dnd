from __future__ import annotations

from uuid import uuid4

from app_dnd.models import Character
from app_dnd.storage import Database

MAX_BYTES = 5 * 1024 * 1024


def sniff_mime(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    raise ValueError("Formato não suportado (use PNG, JPEG ou WebP)")


def set_portrait(db: Database, character: Character, data: bytes) -> Character:
    if not data:
        raise ValueError("Imagem vazia")
    if len(data) > MAX_BYTES:
        raise ValueError(f"Imagem maior que {MAX_BYTES // (1024 * 1024)} MB")
    mime = sniff_mime(data)
    old = character.portrait_id
    new_id = uuid4()
    db.save_asset(new_id, data, mime)
    character.portrait_id = new_id
    saved = db.save_character(character)
    if old:
        db.delete_asset(old)
    return saved


def clear_portrait(db: Database, character: Character) -> Character:
    old = character.portrait_id
    character.portrait_id = None
    saved = db.save_character(character)
    if old:
        db.delete_asset(old)
    return saved
