"""Migration depuis NodOcean for HA, sauvegarde et restauration d'Ocean2MQTT.

Trois sources possibles pour retrouver des produits sans les réappairer :

- **Home Assistant** (add-on) : lecture seule de la configuration de NodOcean for HA
  dans le dossier de configuration de HA (`.storage/core.config_entries`, codes ReCom,
  pièces des appareils).
- **Fichier d'export NodOcean** (bouton « Exporter pour Ocean2MQTT » de NodOcean,
  format `ocean2mqtt-import`), pour Docker ou une autre machine.
- **Sauvegarde Ocean2MQTT** (format `ocean2mqtt-backup`).

Les actionneurs ont appris l'adresse de la clé (Base ID + décalage) : ils ne
répondent sans réappairage qu'avec la **même clé**. Les capteurs et interrupteurs
n'ont besoin que de leur identifiant.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .core.esp3 import str_to_id

_LOGGER = logging.getLogger(__name__)

NODOCEAN_DOMAIN = "nodon_enocean"
IMPORT_FORMAT = "ocean2mqtt-import"
BACKUP_FORMAT = "ocean2mqtt-backup"


class MigrationError(ValueError):
    """Fichier ou configuration illisible."""


@dataclass
class Source:
    """Produits à reprendre, d'où qu'ils viennent."""

    kind: str  # nodocean, backup
    base_id: str | None  # clé qui a appairé les actionneurs
    devices: list[dict[str, Any]] = field(default_factory=list)  # entrées devices.json
    unknown_models: list[str] = field(default_factory=list)
    active: bool | None = None  # NodOcean encore activé dans Home Assistant
    port: str | None = None
    title: str | None = None

    def summary(self) -> dict[str, Any]:
        return {"kind": self.kind, "base_id": self.base_id, "active": self.active,
                "port": self.port, "title": self.title, "devices": len(self.devices)}


def product_id(model: str) -> str:
    """Modèle NodOcean -> fiche Ocean2MQTT."""
    model = model.strip().upper()
    if model == "ASP-2-METERING":
        return "ubiwizz/ubid1501s"
    if model.startswith("EEP-"):  # produit générique de NodOcean (« EEP-F6-02-01 »)
        return f"generique/{model[4:].lower()}"
    return f"nodon/{model.lower()}"


def _code(value: Any) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, int):
        return value & 0xFFFFFFFF
    try:
        return int(str(value), 16) & 0xFFFFFFFF
    except ValueError:
        return None


def _device_id(value: Any) -> str:
    text = str(value or "").replace(":", "").strip().upper()
    str_to_id(text)  # lève ValueError si invalide
    return text


def _entry(dev_id: str, product: str, name: str | None, room: str | None,
           sender_offset: Any, recom_code: Any, recom_pending: bool = False,
           settings: dict | None = None, paired_at: str | None = None) -> dict[str, Any]:
    return {
        "id": dev_id,
        "product": product,
        "name": (name or "").strip() or dev_id,
        "room": room or None,
        "sender_offset": sender_offset if isinstance(sender_offset, int) else None,
        "settings": settings or {},
        "recom_code": _code(recom_code),
        "recom_pending": bool(recom_pending),
        "paired_at": paired_at or datetime.now(UTC).isoformat(timespec="seconds"),
    }


# -- Configuration de Home Assistant (add-on) --------------------------------


def _storage(config_dir: Path, key: str) -> dict[str, Any] | None:
    path = config_dir / ".storage" / key
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("data") or {}
    except (OSError, ValueError) as err:
        _LOGGER.warning("Lecture de %s impossible : %s", path, err)
        return None


def read_homeassistant(config_dir: str | Path | None) -> list[Source]:
    """Clés NodOcean for HA trouvées dans la configuration de Home Assistant."""
    if not config_dir:
        return []
    config_dir = Path(config_dir)
    entries = (_storage(config_dir, "core.config_entries") or {}).get("entries") or []
    nodocean = [e for e in entries if e.get("domain") == NODOCEAN_DOMAIN]
    if not nodocean:
        return []
    # Pièces : registre des appareils + registre des pièces
    areas = {a.get("id"): a.get("name")
             for a in (_storage(config_dir, "core.area_registry") or {}).get("areas") or []}
    device_area: dict[str, str] = {}
    for dev in (_storage(config_dir, "core.device_registry") or {}).get("devices") or []:
        for ident in dev.get("identifiers") or []:
            if len(ident) == 2 and ident[0] == NODOCEAN_DOMAIN and dev.get("area_id"):
                device_area[str(ident[1]).upper()] = areas.get(dev["area_id"])
    sources = []
    for entry in nodocean:
        codes = _storage(config_dir, f"{NODOCEAN_DOMAIN}.recom_codes.{entry.get('entry_id')}")
        codes = codes or {}
        source = Source(
            kind="nodocean",
            base_id=(entry.get("unique_id") or "").upper() or None,
            active=entry.get("disabled_by") is None,
            port=(entry.get("data") or {}).get("device"),
            title=entry.get("title"),
        )
        for sub in entry.get("subentries") or []:
            if sub.get("subentry_type") != "device":
                continue
            data = sub.get("data") or {}
            try:
                dev_id = _device_id(data.get("device_id"))
            except ValueError:
                continue
            source.devices.append(_entry(
                dev_id, product_id(str(data.get("model") or "")), sub.get("title"),
                device_area.get(dev_id), data.get("sender_offset"), codes.get(dev_id),
                codes.get(f"{dev_id}_pending") == "1",
            ))
        sources.append(source)
    return sources


# -- Fichiers : export NodOcean, sauvegarde Ocean2MQTT ------------------------


def parse_file(data: Any) -> Source:
    """Export NodOcean (`ocean2mqtt-import`) ou sauvegarde Ocean2MQTT (`ocean2mqtt-backup`)."""
    if isinstance(data, (str, bytes)):
        try:
            data = json.loads(data)
        except ValueError as err:
            raise MigrationError("Fichier illisible : JSON attendu") from err
    if not isinstance(data, dict):
        raise MigrationError("Fichier illisible")
    fmt = data.get("format")
    if fmt == IMPORT_FORMAT:
        gateway = data.get("gateway") or {}
        source = Source(kind="nodocean", base_id=(gateway.get("base_id") or "").upper() or None,
                        port=gateway.get("port"), title=data.get("source"))
        for dev in data.get("devices") or []:
            try:
                dev_id = _device_id(dev.get("id"))
            except ValueError:
                continue
            source.devices.append(_entry(
                dev_id, dev.get("product") or product_id(str(dev.get("model") or "")),
                dev.get("name"), dev.get("area") or dev.get("room"), dev.get("sender_offset"),
                dev.get("recom_code"), bool(dev.get("recom_pending")),
            ))
        return source
    if fmt == BACKUP_FORMAT:
        source = Source(kind="backup", base_id=(data.get("base_id") or "").upper() or None)
        for dev in data.get("devices") or []:
            try:
                dev_id = _device_id(dev.get("id"))
            except ValueError:
                continue
            source.devices.append(_entry(
                dev_id, str(dev.get("product")), dev.get("name"), dev.get("room"),
                dev.get("sender_offset"), dev.get("recom_code"),
                bool(dev.get("recom_pending")), dev.get("settings"), dev.get("paired_at"),
            ))
        return source
    raise MigrationError("Format inconnu : export NodOcean for HA ou sauvegarde Ocean2MQTT "
                         "attendu")


def make_backup(devices: dict[str, dict[str, Any]], base_id: str | None,
                version: str, configuration: dict[str, Any]) -> dict[str, Any]:
    """Sauvegarde complète des produits appairés (codes ReCom compris)."""
    out = []
    for entry in devices.values():
        item = {k: v for k, v in entry.items() if k != "recom_code"}
        if entry.get("recom_code") is not None:
            item["recom_code"] = f"{entry['recom_code']:08X}"
        out.append(item)
    return {
        "format": BACKUP_FORMAT,
        "version": 1,
        "ocean2mqtt": version,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "base_id": base_id,
        "devices": out,
        "configuration": configuration,  # pour information (mots de passe masqués)
    }
