"""Configuration (configuration.yaml) et produits appairés (devices.json)."""

from __future__ import annotations

import json
import logging
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

_LOGGER = logging.getLogger(__name__)

DEFAULTS: dict[str, Any] = {
    "serial": {"port": "/dev/ttyUSB0"},
    "mqtt": {
        "enabled": True,
        "host": "localhost",
        "port": 1883,
        "username": None,
        "password": None,
        "base_topic": "ocean2mqtt",
        "topic_name": "name",  # « name » ou « id » (identifiant EnOcean)
        "discovery": True,
        "discovery_prefix": "homeassistant",
        "retain": True,
        "qos": 0,
        "tls": False,
        "tls_insecure": False,
        "ca": None,
        "client_id": None,
        "telegrams": False,
    },
    "frontend": {
        "enabled": True,
        "host": "0.0.0.0",
        "port": 8080,
        "password": None,
        "allow_remote": False,  # par défaut, seules les adresses du réseau local
    },
    "recom": {
        # Remote Commissioning (ReMan) : le code de sécurité passe en clair à la radio
        # lors d'un déverrouillage. false = aucune commande ReMan n'est jamais envoyée.
        "enabled": True,
    },
    "homeassistant": {
        # Dossier de configuration de Home Assistant (lecture seule), pour reprendre
        # les produits de NodOcean for HA. L'add-on le renseigne tout seul.
        "config_dir": None,
    },
    "language": "fr",
}


def _merge(base: dict, extra: dict) -> dict:
    out = deepcopy(base)
    for key, value in (extra or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def _env_overrides() -> dict:
    """Variables d'environnement (Docker) : OCEAN2MQTT_SERIAL_PORT, OCEAN2MQTT_MQTT_HOST…"""
    out: dict[str, dict] = {}
    for section, values in DEFAULTS.items():
        if not isinstance(values, dict):
            continue
        for key in values:
            env = os.environ.get(f"OCEAN2MQTT_{section}_{key}".upper())
            if env is not None:
                out.setdefault(section, {})[key] = yaml.safe_load(env)
    return out


# Clés réglées depuis l'interface : elles l'emportent sur les variables d'environnement
# (ex. serveur MQTT trouvé automatiquement par l'add-on). Liste « section.clé ».
UI_KEY = "ui_overrides"


class Config:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / "configuration.yaml"
        self.file: dict[str, Any] = deepcopy(DEFAULTS)  # contenu du fichier (sans l'env)
        self.env: dict[str, Any] = {}
        self.data: dict[str, Any] = deepcopy(DEFAULTS)

    def load(self) -> Config:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if self.path.is_file():
            content = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
            self.file = _merge(DEFAULTS, content)
        else:
            self.save()
            _LOGGER.info("Configuration créée : %s", self.path)
        self.env = _env_overrides()
        self._rebuild()
        return self

    def _ui_keys(self) -> list[str]:
        return list(self.file.get(UI_KEY) or [])

    def _rebuild(self) -> None:
        env = deepcopy(self.env)
        for item in self._ui_keys():
            section, _, key = item.partition(".")
            env.get(section, {}).pop(key, None)
        data = _merge(self.file, env)
        data.pop(UI_KEY, None)
        self.data = data

    def save(self) -> None:
        """Écrit le fichier, sans les valeurs venues de l'environnement."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            yaml.safe_dump(self.file, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )

    def update(self, section: str, values: dict[str, Any], ui: bool = False) -> None:
        self.file[section] = _merge(self.file.get(section, {}), values)
        if ui:
            keys = set(self._ui_keys()) | {f"{section}.{k}" for k in values}
            self.file[UI_KEY] = sorted(keys)
        self.save()
        self._rebuild()

    def reset_ui(self, section: str) -> None:
        """Revient aux valeurs de l'environnement (réglage automatique) pour une section."""
        self.file[UI_KEY] = [k for k in self._ui_keys() if not k.startswith(section + ".")]
        if not self.file[UI_KEY]:
            self.file.pop(UI_KEY)
        self.save()
        self._rebuild()

    def is_auto(self, section: str) -> bool:
        """Réglages venus de l'environnement (add-on) et non remplacés dans l'interface."""
        ui = {k.partition(".")[2] for k in self._ui_keys() if k.startswith(section + ".")}
        return bool(set(self.env.get(section, {})) - ui)

    def __getitem__(self, section: str) -> Any:
        return self.data[section]

    def public(self) -> dict[str, Any]:
        """Configuration sans les mots de passe (pour l'interface et bridge/info)."""
        data = deepcopy(self.data)
        data.pop(UI_KEY, None)
        for section in ("mqtt", "frontend"):
            if data.get(section, {}).get("password"):
                data[section]["password"] = "********"
        return data


class DeviceStore:
    """Produits appairés : identifiant EnOcean, fiche, nom, pièce, réglages, code ReCom."""

    def __init__(self, data_dir: Path) -> None:
        self.path = Path(data_dir) / "devices.json"
        self.devices: dict[str, dict[str, Any]] = {}
        # Base ID de la clé qui a appairé les actionneurs, choix de migration…
        self.meta: dict[str, Any] = {}

    def load(self) -> DeviceStore:
        if self.path.is_file():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.devices = {d["id"]: d for d in data.get("devices", [])}
            self.meta = data.get("meta") or {}
        return self

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps({"version": 1, "meta": self.meta, "devices": list(self.devices.values())},
                       indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(self.path)

    def put(self, entry: dict[str, Any]) -> None:
        self.devices[entry["id"]] = entry
        self.save()

    def remove(self, device_id: str) -> None:
        self.devices.pop(device_id, None)
        self.save()

    def free_sender_offset(self) -> int:
        used = {d.get("sender_offset") for d in self.devices.values() if
                not d.get("needs_pairing")}
        for offset in range(1, 128):
            if offset not in used:
                return offset
        raise RuntimeError("Plus d'adresse d'émission libre sur cette clé (127 actionneurs)")

