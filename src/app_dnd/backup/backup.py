from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from pydantic import ValidationError

from app_dnd.models import Character, Spell
from app_dnd.services.portrait import MAX_BYTES, sniff_mime
from app_dnd.storage import Database

FORMAT_VERSION = 1


class BackupError(ValueError):
    pass


@dataclass(frozen=True)
class ImportResult:
    imported: int
    skipped_newer: int


def export_backup(db: Database, include_images: bool = True) -> str:
    characters = db.list_characters()
    assets: list[dict] = []
    if include_images:
        for ch in characters:
            if ch.portrait_id and (asset := db.get_asset(ch.portrait_id)):
                data, mime = asset
                assets.append(
                    {"id": str(ch.portrait_id), "mime_type": mime, "data_b64": base64.b64encode(data).decode()}
                )
    payload = {
        "app": "APP_DND",
        "format_version": FORMAT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "characters": [json.loads(c.model_dump_json()) for c in characters],
        "assets": assets,
        "custom_spells": [json.loads(sp.model_dump_json()) for sp in db.list_custom_spells()],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _decode_asset(entry: dict) -> tuple[UUID, bytes, str]:
    data = base64.b64decode(entry["data_b64"], validate=True)
    if not data or len(data) > MAX_BYTES:
        raise ValueError(f"Imagem vazia ou maior que {MAX_BYTES // (1024 * 1024)} MB")
    mime = sniff_mime(data)
    if entry["mime_type"] != mime:
        raise ValueError(f"Tipo de imagem declarado ({entry['mime_type']}) difere do conteúdo ({mime})")
    return UUID(entry["id"]), data, mime


def import_backup(db: Database, raw: str, overwrite_newer: bool = False) -> ImportResult:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        raise BackupError(f"JSON inválido: {e}") from e
    if not isinstance(payload, dict) or payload.get("app") != "APP_DND":
        raise BackupError("Arquivo não é um backup do APP_DND")
    if payload.get("format_version") != FORMAT_VERSION:
        raise BackupError(f"Versão de backup não suportada: {payload.get('format_version')!r}")

    try:
        characters = [Character.model_validate(c) for c in payload.get("characters", [])]
        assets = [_decode_asset(a) for a in payload.get("assets", [])]
        custom_spells = [Spell.model_validate({**sp, "source": "custom"}) for sp in payload.get("custom_spells", [])]
    except (ValidationError, KeyError, ValueError, TypeError) as e:
        raise BackupError(f"Backup com dados inválidos: {e}") from e

    imported = skipped = 0
    try:
        with db.transaction():
            for asset_id, data, mime in assets:
                db.save_asset(asset_id, data, mime)
            for spell in custom_spells:
                db.save_custom_spell(spell)
            for ch in characters:
                stored = db.get_character(ch.id)
                if stored is not None and stored.updated_at > ch.updated_at and not overwrite_newer:
                    skipped += 1
                    continue
                db.save_character(ch, touch=False)
                imported += 1
    except (ValueError, OSError) as e:
        raise BackupError(f"Falha ao gravar o backup; nada foi alterado: {e}") from e
    return ImportResult(imported, skipped)
