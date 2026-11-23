"""Le service Ocean2MQTT : clé radio, produits appairés, API commune MQTT / interface web.

Toutes les actions passent par `request(commande, données)` ; les changements sont
diffusés par `emit(topic, données)` aux abonnés (pont MQTT, interface web).
Les topics sont relatifs au topic de base (« ocean2mqtt ») : bridge/state,
bridge/info, bridge/devices, bridge/event, <produit>, <produit>/availability…
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import unicodedata
from collections import deque
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from . import __version__
from .config import Config, DeviceStore, StateStore
from .core import recom
from .core.convert import CommandError, apply_command, device_payload, text_command
from .core.device import (
    AVAILABILITY_KEY,
    LINK_TYPES,
    LINK_TYPES_BY_MODEL,
    LINK_TYPES_DEFAULT,
    Device,
)
from .core.eep import is_1bs_teach_in, is_4bs_teach_in, parse_4bs_teach_in_eep
from .core.esp3 import (
    RORG_1BS,
    RORG_4BS,
    RORG_RPS,
    RORG_VLD,
    RadioTelegram,
    id_to_str,
    parse_ute,
    str_to_id,
)
from .core.exposes import exposes
from .core.gateway import Gateway, GatewayError, ReComError
from .core.pairing import wait_for_teach_in
from .core.product import Product
from .core.settings import SettingError, apply_setting, describe, is_setting
from .library import ALIASES, Library, load_library
from .migration import MigrationError, Source, make_backup, parse_file, read_homeassistant

_LOGGER = logging.getLogger(__name__)

Listener = Callable[[str, Any, bool], None]  # topic, données, retenu

PAIRING_TIMEOUT = 60
RECONNECT_DELAY = 15
REMOTE_PAIRING_TIMEOUT = 60  # s : demande d'appairage attendue après Remote Learn
STATE_SAVE_INTERVAL = 60  # s : enregistrement des derniers états (si changement)
POLL_INTERVAL = 60  # s, interrogation des actionneurs (état, puissance, énergie)
UNKNOWN_MAX = 50  # émetteurs inconnus gardés en mémoire
RECOM_LOG_MAX = 200


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


class RequestError(Exception):
    """Erreur renvoyée à l'appelant (MQTT ou interface web)."""


class Ocean2MQTT:
    def __init__(self, config: Config, library: Library | None = None) -> None:
        self.config = config
        self.library = library or load_library()
        self.store = DeviceStore(config.data_dir).load()
        self._migrate_product_ids()
        if not self.store.meta.get("recom_secret"):
            self.store.meta["recom_secret"] = recom.new_secret()
            self.store.save()
        self.gateway = Gateway(config["serial"]["port"])
        self.gateway.reman_enabled = bool(config["recom"].get("enabled", True))
        self.gateway_ok = False
        self.devices: dict[str, Device] = {}  # identifiant EnOcean -> produit
        self.last_seen: dict[str, str] = {}
        self.retained: dict[str, Any] = {}
        self._listeners: list[Listener] = []
        self._unsubs: dict[str, Callable[[], None]] = {}
        self._available: dict[str, bool] = {}
        self._pairing: asyncio.Task | None = None
        self.pairing: dict[str, Any] | None = None
        self._tasks: set[asyncio.Task] = set()
        self._stopping = False
        # Émetteurs entendus mais pas appairés (id -> infos), suggestion automatique
        self.unknown: dict[str, dict[str, Any]] = {}
        # Pont MQTT en cours et relance après un changement de réglages (__main__)
        self.mqtt_bridge: Any = None
        self.mqtt_restart: Callable[[], Any] | None = None
        self.recom_log: deque[dict[str, Any]] = deque(maxlen=RECOM_LOG_MAX)
        # Dernier état connu des produits, rechargé au démarrage (mise à jour, redémarrage)
        self.state_store = StateStore(config.data_dir)
        self._saved_states = self.state_store.load()
        self._states_dirty = False

    # -- Diffusion -----------------------------------------------------------

    def subscribe(self, listener: Listener) -> Callable[[], None]:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def emit(self, topic: str, payload: Any, retain: bool = False) -> None:
        if retain:
            if payload in ("", None):
                self.retained.pop(topic, None)
            else:
                self.retained[topic] = payload
        for listener in list(self._listeners):
            try:
                listener(topic, payload, retain)
            except Exception:
                _LOGGER.exception("Erreur d'un abonné sur %s", topic)

    def _task(self, coro) -> asyncio.Task:
        task = asyncio.get_running_loop().create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    # -- Cycle de vie --------------------------------------------------------

    def _migrate_product_ids(self) -> None:
        """Fiches déplacées (marque d'origine) : met à jour les produits déjà appairés."""
        changed = False
        for entry in self.store.devices.values():
            if (new := ALIASES.get(entry.get("product", ""))) is not None:
                _LOGGER.info("%s : fiche %s renommée en %s", entry.get("name"), entry["product"], new)
                entry["product"] = new
                changed = True
        if changed:
            self.store.save()

    async def start(self) -> None:
        self.gateway.on_disconnect = self._on_gateway_lost
        self.gateway.add_record_listener(self._on_record)
        self.gateway.subscribe_all(self._on_any_telegram)
        await self._connect_gateway(wait=False)
        for entry in list(self.store.devices.values()):
            self._add_device(entry)
        self._saved_states = {}
        self._task(self._availability_loop())
        self._task(self._poll_loop())
        self._task(self._state_save_loop())
        self.emit("bridge/state", "online", True)
        self._publish_info()
        self._publish_devices()

    async def stop(self) -> None:
        self._stopping = True
        if self._pairing:
            self._pairing.cancel()
        for task in list(self._tasks):
            task.cancel()
        for device in self.devices.values():
            device.stop()
        self.save_states()
        self.gateway.close()
        self.emit("bridge/state", "offline", True)

    async def _connect_gateway(self, wait: bool = True) -> None:
        """Ouvre la clé ; en cas d'échec, réessaie en tâche de fond."""
        try:
            await self.gateway.connect()
            self.gateway_ok = True
            _LOGGER.info("Clé EnOcean prête, Base ID %s", id_to_str(self.gateway.info.base_id))
            self._check_base_id()
            self._task(self._init_actuators())
        except GatewayError as err:
            self.gateway_ok = False
            _LOGGER.warning("Clé EnOcean indisponible (%s), nouvel essai dans %s s", err,
                            RECONNECT_DELAY)
            if not self._stopping:
                self._task(self._reconnect_later())
        self._publish_info()

    async def _reconnect_later(self) -> None:
        await asyncio.sleep(RECONNECT_DELAY)
        await self._connect_gateway()

    def _on_gateway_lost(self) -> None:
        self.gateway_ok = False
        self._publish_info()
        if not self._stopping:
            self._task(self._reconnect_later())

    def _check_base_id(self) -> None:
        """Clé changée : les actionneurs appairés avec l'ancienne clé ne répondent plus."""
        current = id_to_str(self.gateway.info.base_id)
        stored = self.store.meta.get("base_id")
        if stored and stored != current:
            names = []
            for entry in self.store.devices.values():
                product = self.library.get(entry["product"])
                if product and product.is_actuator and not entry.get("needs_pairing"):
                    entry["needs_pairing"] = True
                    names.append(entry["name"])
            _LOGGER.warning("Nouvelle clé EnOcean (Base ID %s, avant %s) : %d actionneur(s) à "
                            "réappairer", current, stored, len(names))
            self.store.meta["previous_base_id"] = stored
            self.emit("bridge/event", {"type": "gateway_changed",
                                       "data": {"base_id": current, "previous": stored,
                                                "devices": names}})
        if stored != current:
            self.store.meta["base_id"] = current
            self.store.save()
            self._publish_devices()

    async def _init_actuator(self, device: Device) -> None:
        """Comme NodOcean : infos NodOn, rapport automatique des mesures, état."""
        if device.product.brand.lower() == "nodon":
            await device.query_info()
            await asyncio.sleep(0.2)
        if device.product.metering:
            await device.configure_reporting()
            await asyncio.sleep(0.2)
        await device.refresh()

    async def _write_base_id(self, data: dict[str, Any]) -> dict[str, Any]:
        """Écrit un Base ID dans la clé (ex. celui d'une clé HS : pas de réappairage)."""
        if not self.gateway_ok or self.gateway.info is None:
            raise RequestError("Clé EnOcean non connectée")
        try:
            value = str_to_id(str(data.get("base_id") or ""))
        except ValueError as err:
            raise RequestError("Base ID invalide (8 caractères hexadécimaux)") from err
        if value == self.gateway.info.base_id:
            raise RequestError("La clé a déjà ce Base ID")
        try:
            info = await self.gateway.write_base_id(value)
        except GatewayError as err:
            raise RequestError(str(err)) from err
        new = id_to_str(info.base_id)
        restored = []
        if new == self.store.meta.get("previous_base_id"):
            # Ancien Base ID repris : les actionneurs appairés avec lui répondent à nouveau
            for entry in self.store.devices.values():
                if entry.get("needs_pairing") and entry.get("sender_offset") is not None:
                    entry.pop("needs_pairing", None)
                    restored.append(entry["name"])
            self.store.meta.pop("previous_base_id", None)
            self.store.meta["base_id"] = new
            self.store.save()
        else:
            # Autre Base ID : les actionneurs appairés avec l'ancien sont à réappairer
            self._check_base_id()
        _LOGGER.warning("Base ID de la clé changé en %s (%s écriture(s) restante(s))", new,
                        info.base_id_writes_left)
        self._publish_info()
        self._publish_devices()
        self._task(self._init_actuators())
        return {"base_id": new, "writes_left": info.base_id_writes_left, "restored": restored}

    # -- Serveur MQTT (modifiable depuis l'interface) -------------------------

    MQTT_EDITABLE = ("host", "port", "username", "password", "base_topic", "topic_name",
                     "discovery", "discovery_prefix", "tls")

    def mqtt_settings(self) -> dict[str, Any]:
        mqtt = self.config["mqtt"]
        out = {k: mqtt.get(k) for k in self.MQTT_EDITABLE if k != "password"}
        out["has_password"] = bool(mqtt.get("password"))
        out["auto"] = self.config.is_auto("mqtt")
        out["can_auto"] = bool(self.config.env.get("mqtt"))
        out["editable"] = self.mqtt_restart is not None
        out["connected"] = bool(self.mqtt_bridge and self.mqtt_bridge.connected)
        return out

    def _mqtt_values(self, data: dict[str, Any]) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for key in self.MQTT_EDITABLE:
            if key not in data:
                continue
            value = data[key]
            if key == "password" and value in (None, ""):
                continue  # mot de passe inchangé
            if key == "port":
                try:
                    value = int(value)
                except (TypeError, ValueError) as err:
                    raise RequestError("Port MQTT invalide") from err
                if not 1 <= value <= 65535:
                    raise RequestError("Port MQTT invalide")
            elif key in ("discovery", "tls"):
                value = bool(value)
            elif key == "topic_name":
                if value not in ("name", "id"):
                    raise RequestError("Nom des topics : name ou id")
            else:
                value = str(value).strip() if value is not None else None
                if key in ("base_topic", "discovery_prefix"):
                    value = (value or "").strip("/")
                    if not value or any(c in value for c in "#+ "):
                        raise RequestError("Topic invalide (sans espace, # ni +)")
                if key == "host" and not value:
                    raise RequestError("Adresse du serveur MQTT obligatoire")
                if key == "username" and not value:
                    value = None
            values[key] = value
        if data.get("clear_password"):
            values["password"] = None
        return values

    async def _test_mqtt(self, data: dict[str, Any]) -> dict[str, Any]:
        from .mqtt import test_connection

        settings = {**self.config["mqtt"], **self._mqtt_values(data)}
        error = await test_connection(settings)
        if error:
            raise RequestError(f"Connexion MQTT impossible : {error}")
        return {"ok": True}

    async def _set_mqtt(self, data: dict[str, Any]) -> dict[str, Any]:
        if data.get("auto"):
            # Retour au réglage automatique (add-on : Mosquitto du Supervisor)
            self.config.reset_ui("mqtt")
        else:
            values = self._mqtt_values(data)
            if not data.get("skip_test"):
                await self._test_mqtt(data)
            self.config.update("mqtt", values, ui=True)
        if self.mqtt_restart is not None:
            await self.mqtt_restart()
        self._publish_devices()
        self._publish_info()
        return self.mqtt_settings()

    async def _init_actuators(self) -> None:
        for device in list(self.devices.values()):
            entry = self.store.devices.get(device.id_str, {})
            if device.product.is_actuator and self.gateway_ok and not entry.get("needs_pairing"):
                await self._init_actuator(device)
                await asyncio.sleep(0.3)

    async def _poll_loop(self) -> None:
        """Interroge régulièrement les actionneurs (mesures manquées, état réel)."""
        while True:
            await asyncio.sleep(POLL_INTERVAL)
            if not self.gateway_ok:
                continue
            for device in list(self.devices.values()):
                if device.product.is_actuator and self.gateway_ok:
                    await device.refresh()
                    await asyncio.sleep(0.2)

    # -- Derniers états (gardés entre deux démarrages) -------------------------

    def save_states(self) -> None:
        data: dict[str, dict[str, Any]] = {}
        for device_id, device in self.devices.items():
            state = {k: v for k, v in device.state.items() if k != "event"}
            entry: dict[str, Any] = {"state": state}
            if last := self.last_seen.get(device_id):
                entry["last_seen"] = last
            if device.last_dbm is not None:
                entry["dbm"] = device.last_dbm
            if device._energy_time is not None:
                entry["energy_time"] = device._energy_time
            data[device_id] = entry
        try:
            self.state_store.save(data)
            self._states_dirty = False
        except OSError as err:
            _LOGGER.warning("Derniers états non enregistrés : %s", err)

    def _restore_state(self, device: Device) -> None:
        saved = self._saved_states.get(device.id_str)
        if not isinstance(saved, dict):
            return
        state = dict(saved.get("state") or {})
        energy = state.pop("energy", None)
        state.pop("event", None)
        device.state.update(state)
        if energy is not None:
            device.restore_energy(energy, saved.get("energy_time") or time.time())
        if isinstance(saved.get("dbm"), int):
            device.last_dbm = saved["dbm"]
        if last := saved.get("last_seen"):
            self.last_seen[device.id_str] = last
            try:
                age = (datetime.now(UTC) - datetime.fromisoformat(last)).total_seconds()
                device.last_seen = time.monotonic() - max(0.0, age)
            except (TypeError, ValueError):
                pass

    async def _state_save_loop(self) -> None:
        while True:
            await asyncio.sleep(STATE_SAVE_INTERVAL)
            if self._states_dirty:
                self.save_states()

    async def _availability_loop(self) -> None:
        while True:
            await asyncio.sleep(30)
            for device in self.devices.values():
                device.notify({AVAILABILITY_KEY})

    # -- Produits ------------------------------------------------------------

    def _product(self, product_id: str) -> Product:
        product = self.library.get(product_id)
        if product is None:
            raise RequestError(f"Produit inconnu dans la bibliothèque : {product_id}")
        return product

    def _add_device(self, entry: dict[str, Any]) -> Device | None:
        product = self.library.get(entry["product"])
        if product is None:
            _LOGGER.error("%s : fiche %s introuvable, produit ignoré", entry["id"],
                          entry["product"])
            return None
        device = Device(
            self.gateway,
            product,
            str_to_id(entry["id"]),
            entry.get("sender_offset"),
            entry["id"],
            entry["name"],
        )
        device.settings.update(entry.get("settings") or {})
        device.recom_code = entry.get("recom_code")
        device.recom_pending = entry.get("recom_pending", False)
        device.recom_mode = entry.get("recom_mode") or (
            "random" if device.recom_code is not None else None)
        device.on_code_change = self._save_code
        self._restore_state(device)
        self.devices[entry["id"]] = device
        self._unsubs[entry["id"]] = device.add_listener(self._listener(device), first=True)
        device.start()
        self._available[entry["id"]] = device.available
        return device

    async def _save_code(self, device: Device) -> None:
        entry = self.store.devices[device.id_str]
        entry["recom_code"] = device.recom_code
        entry["recom_pending"] = device.recom_pending
        entry["recom_mode"] = device.recom_mode
        self.store.put(entry)

    def topic_name(self, device_id: str) -> str:
        entry = self.store.devices[device_id]
        if self.config["mqtt"]["topic_name"] == "id":
            return device_id
        name = slugify(entry["name"]) or device_id
        taken = {
            slugify(e["name"]) for i, e in self.store.devices.items() if i != device_id
        } | {"bridge"}
        return f"{name}_{device_id}" if name in taken else name

    def _image_url(self, product: Product) -> str | None:
        if not product.image:
            return None
        return f"produits/{product.id.split('/')[0]}/{product.image.rsplit('/', 1)[-1]}"

    def product_dict(self, product: Product) -> dict[str, Any]:
        lang = self.config["language"]
        return {
            "id": product.id,
            "brand": product.brand,
            "model": product.model,
            "name": product.name(lang),
            "type": product.type,
            "eep": product.eep,
            "extra_eeps": list(product.extra_eeps),
            "support": product.support,
            "teach_in": product.teach_in,
            "steps": list(product.steps(lang)),
            "after": product.after_text(lang),
            "i18n": {code: {"name": product.name(code), "steps": list(product.steps(code)),
                            "after": product.after_text(code)} for code in ("fr", "en")},
            "manual": product.manual,
            "image": self._image_url(product),
            "variants": list(product.variants),
            "recom": product.recom,
            "generic": product.generic,
            "exposes": [e.as_dict() for e in exposes(product)],
        }

    def device_dict(self, device: Device) -> dict[str, Any]:
        entry = self.store.devices[device.id_str]
        product = device.product
        return {
            "id": device.id_str,
            "name": entry["name"],
            "room": entry.get("room"),
            "topic": self.topic_name(device.id_str),
            "product": self.product_dict(product),
            "identity": entry.get("identity", {}),
            "state": device_payload(device),
            "available": device.available,
            "last_seen": self.last_seen.get(device.id_str),
            "actuator": product.is_actuator,
            "settings": describe(device),
            "needs_pairing": bool(self.store.devices.get(device.id_str, {}).get("needs_pairing")),
            "recom": self.recom_status(device) if product.recom and self.recom_enabled
            else None,
        }

    def recom_status(self, device: Device) -> dict[str, Any]:
        """État du Remote Commissioning (le code n'est jamais transmis)."""
        types = LINK_TYPES_BY_MODEL.get(device.product.model, LINK_TYPES_DEFAULT)
        return {
            "secured": device.recom_secured,
            "pending": device.recom_pending,
            "has_code": device.recom_code is not None,
            "mode": device.recom_mode,
            # Session encore ouverte : la prochaine opération ne renverra pas le code
            "session_until": round(time.time() + left) if (
                left := self.gateway.unlocked_for(device.device_id)) else 0,
            "links": device.state.get("links"),
            "links_max": device.state.get("links_max"),
            "link_types": list(types),
            "config": {k: device.state[k] for k in ("rs_switch_type", "rs_calibration_type",
                                                     "rs_time_down", "rs_time_up")
                       if device.state.get(k) is not None},
        }

    def _listener(self, device: Device) -> Callable[[set[str]], None]:
        def _update(keys: set[str]) -> None:
            topic = self.topic_name(device.id_str)
            available = device.available
            if self._available.get(device.id_str) != available:
                self._available[device.id_str] = available
                self.emit(f"{topic}/availability", "online" if available else "offline", True)
            if keys == {AVAILABILITY_KEY}:
                return
            if "rssi" in keys:
                self.last_seen[device.id_str] = datetime.now(UTC).isoformat(timespec="seconds")
            self._states_dirty = True
            if "setpoint" in keys:
                self._save_settings(device)
            event = device.state.pop("event", None) if "event" in keys else None
            if event:
                self.emit(f"{topic}/action", event, False)
            self._publish_state(device)

        return _update

    def _save_settings(self, device: Device) -> None:
        entry = self.store.devices.get(device.id_str)
        if entry is not None:
            entry["settings"] = dict(device.settings)
            self.store.put(entry)

    # -- Journal radio, émetteurs inconnus -----------------------------------

    def _telegram_dict(self, record: dict[str, Any]) -> dict[str, Any]:
        peer = record["destination"] if record["dir"] == "tx" else record["sender"]
        known = self.devices.get(peer)
        decoded = None
        # Only decode received application data. Never expose ReMan/security payloads.
        if known and record["dir"] == "rx" and record.get("rorg") in {"F6", "D5", "A5", "D2"}:
            try:
                telegram = RadioTelegram(
                    rorg=int(record["rorg"], 16),
                    payload=bytes.fromhex(record.get("data", "")),
                    sender=int(record["sender"], 16),
                    status=int(record.get("status", "00"), 16),
                    destination=int(record["destination"], 16),
                    dbm=record.get("dbm"),
                )
                values = known.decode(telegram)
                allowed = {e.key for e in exposes(known.product)}
                decoded = {k: v for k, v in (values or {}).items() if k in allowed} or None
            except (ValueError, IndexError, KeyError, TypeError):
                pass
        return {
            **record,
            "decoded": decoded,
            "name": known.title if known else None,
            "eep": known.eep_code if known else None,
        }

    def _on_record(self, record: dict[str, Any]) -> None:
        self.emit("bridge/telegrams", self._telegram_dict(record))

    def _on_any_telegram(self, telegram: RadioTelegram) -> None:
        sender = telegram.sender_str
        info = self.gateway.info
        if info and (telegram.sender == info.chip_id or (
            info.base_id is not None and info.base_id <= telegram.sender < info.base_id + 128
        )):
            return
        if sender in self.devices or telegram.rorg not in (RORG_RPS, RORG_1BS, RORG_4BS,
                                                            RORG_VLD, 0xD4):
            return
        now = datetime.now(UTC).isoformat(timespec="seconds")
        entry = self.unknown.get(sender)
        new = entry is None
        if new:
            if len(self.unknown) >= UNKNOWN_MAX:
                oldest = min(self.unknown, key=lambda k: self.unknown[k]["last_seen"])
                self.unknown.pop(oldest)
            entry = {"id": sender, "rorg": f"{telegram.rorg:02X}", "count": 0,
                     "first_seen": now, "eep": None, "manufacturer": None,
                     "teach_in": None, "suggestions": []}
            self.unknown[sender] = entry
        entry["count"] += 1
        entry["last_seen"] = now
        entry["rssi"] = telegram.dbm
        teach = self._teach_in_info(telegram)
        if teach is not None:
            mode, eep, manufacturer = teach
            entry["teach_in"] = mode
            entry["eep"] = eep or entry["eep"]
            entry["manufacturer"] = manufacturer
            products = self.library.match_teach_in(eep, manufacturer) if eep else []
            if eep and not products and (generic := self.library.get(f"generique/{eep}")):
                products = [generic]
            entry["suggestions"] = [p.id for p in products]
        if new or teach is not None:
            self.emit("bridge/unknown", list(self.unknown.values()))
            if teach is not None and entry["suggestions"]:
                self.emit("bridge/event", {"type": "suggestion", "data": entry})

    @staticmethod
    def _teach_in_info(telegram: RadioTelegram) -> tuple[str, str | None, int | None] | None:
        """(mode, EEP, fabricant) si le télégramme est une demande d'appairage."""
        if (ute := parse_ute(telegram)) is not None:
            return "ute", ute.eep, ute.manufacturer
        if is_4bs_teach_in(telegram):
            parsed = parse_4bs_teach_in_eep(telegram)
            if parsed:
                func, type_, manufacturer = parsed
                return "4bs", f"A5-{func:02X}-{type_:02X}", manufacturer
            return "4bs", None, None
        if telegram.rorg == RORG_1BS and is_1bs_teach_in(telegram):
            return "1bs", "D5-00-01", None
        return None

    def _publish_state(self, device: Device) -> None:
        payload = device_payload(device)
        payload["available"] = device.available
        if last := self.last_seen.get(device.id_str):
            payload["last_seen"] = last
        self.emit(self.topic_name(device.id_str), payload, True)

    def _publish_info(self) -> None:
        info = self.info()
        self.emit("bridge/info", info, True)

    def _publish_devices(self) -> None:
        self.emit("bridge/devices", [self.device_dict(d) for d in self.devices.values()], True)
        for device in self.devices.values():
            topic = self.topic_name(device.id_str)
            self.emit(f"{topic}/availability", "online" if device.available else "offline", True)
            self._publish_state(device)

    def info(self) -> dict[str, Any]:
        gw = self.gateway.info
        return {
            "version": __version__,
            "gateway": {
                "connected": self.gateway_ok,
                "port": self.gateway.port,
                "base_id": id_to_str(gw.base_id) if gw else None,
                "chip_id": id_to_str(gw.chip_id) if gw and gw.chip_id else None,
                "app_version": gw.app_version if gw else None,
                "base_id_writes_left": gw.base_id_writes_left if gw else None,
            },
            "mqtt": {"connected": bool(self.mqtt_bridge and self.mqtt_bridge.connected),
                     "editable": self.mqtt_restart is not None},
            "language": self.config["language"],
            "recom_enabled": self.recom_enabled,
            "pairing": self.pairing,
            "config": self.config.public(),
            "devices": len(self.devices),
            "migration": {
                "nodocean": [s.summary() for s in self._ha_sources()],
                "dismissed": bool(self.store.meta.get("migration_dismissed")),
                "previous_base_id": self.store.meta.get("previous_base_id"),
            },
        }

    # -- Appairage -----------------------------------------------------------

    async def _run_pairing(self, product: Product, timeout: int, only: int | None = None) -> None:
        offset = self.store.free_sender_offset() if product.is_actuator else None
        self.pairing = {"product": product.id, "timeout": timeout,
                        "until": round(time.time() + timeout)}
        self.emit("bridge/event", {"type": "pairing", "data": {"status": "started",
                                                               **self.pairing}})
        self._publish_info()
        try:
            result = await wait_for_teach_in(self.gateway, product, offset, timeout, set(),
                                             only)
        except asyncio.CancelledError:
            self.pairing = None
            self.emit("bridge/event", {"type": "pairing", "data": {"status": "stopped"}})
            self._publish_info()
            raise
        self.pairing = None
        if result is None:
            self.emit("bridge/event", {"type": "pairing", "data": {"status": "timeout",
                                                                   "product": product.id}})
            self._publish_info()
            return
        device_id = id_to_str(result.device_id)
        if product.generic and result.eep != product.eep:
            product = self.library.get(f"generique/{result.eep}") or product
        self.unknown.pop(device_id, None)
        old = self.store.devices.get(device_id)
        if old is not None:  # nouvel appairage d'un produit connu : on garde nom et pièce
            self._remove_device(device_id, keep_entry=True)
            if old.get("sender_offset") is not None and product.is_actuator:
                offset = old["sender_offset"]
        entry = {
            "id": device_id,
            "product": product.id,
            "name": old["name"] if old else f"{product.name(self.config['language'])} "
                                            f"{device_id[-4:]}",
            "room": old.get("room") if old else None,
            "sender_offset": offset,
            "settings": old.get("settings", {}) if old else {},
            "recom_code": old.get("recom_code") if old else None,
            "recom_pending": bool(old.get("recom_pending")) if old else False,
            "recom_mode": old.get("recom_mode") if old else None,
            "paired_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        self.store.put(entry)
        device = self._add_device(entry)
        if device is not None:
            device.last_dbm = result.dbm
            self.last_seen[device_id] = datetime.now(UTC).isoformat(timespec="seconds")
        self._publish_devices()
        self._publish_info()
        data = self.device_dict(device) if device else {"id": device_id}
        self.emit("bridge/event", {"type": "pairing", "data": {"status": "success", **data}})
        self.emit("bridge/event", {"type": "device_joined", "data": data})
        if device is not None and product.is_actuator:
            await asyncio.sleep(1)
            await self._init_actuator(device)

    def _remove_device(self, device_id: str, keep_entry: bool = False) -> None:
        device = self.devices.pop(device_id, None)
        if device is None:
            return
        topic = self.topic_name(device_id)
        device.stop()
        if unsub := self._unsubs.pop(device_id, None):
            unsub()
        self.emit(topic, "", True)
        self.emit(f"{topic}/availability", "", True)
        if not keep_entry:
            self.store.remove(device_id)

    # -- API -----------------------------------------------------------------

    def _device(self, data: dict[str, Any]) -> Device:
        key = str(data.get("id") or "").upper()
        device = self.devices.get(key)
        if device is None:
            device = self.device_by_topic(str(data.get("id") or ""))
        if device is None:
            raise RequestError(f"Produit inconnu : {data.get('id')}")
        return device

    def device_by_topic(self, name: str) -> Device | None:
        for device_id, device in self.devices.items():
            if self.topic_name(device_id) == name or device_id == name.upper():
                return device
        return None

    async def request(self, command: str, data: dict[str, Any] | None = None) -> Any:
        """Point d'entrée commun : bridge/request/<commande> (MQTT ou WebSocket)."""
        data = data or {}
        if command == "info":
            return self.info()
        if command == "devices":
            return [self.device_dict(d) for d in self.devices.values()]
        if command == "gateway/base_id":
            return await self._write_base_id(data)
        if command == "config/mqtt":
            return self.mqtt_settings()
        if command == "config/recom/set":
            return self._set_recom(bool(data.get("enabled")))
        if command == "config/mqtt/test":
            return await self._test_mqtt(data)
        if command == "config/mqtt/set":
            return await self._set_mqtt(data)
        if command == "library":
            products = self.library.search(data["search"]) if data.get("search") else list(
                self.library.products.values())
            return [self.product_dict(p) for p in products]
        if command == "library/generic":
            return [self.product_dict(p) for p in self.library.generics()]
        if command == "unknown":
            return list(self.unknown.values())
        if command == "unknown/clear":
            self.unknown.clear()
            self.emit("bridge/unknown", [])
            return []
        if command == "telegrams":
            return [self._telegram_dict(r) for r in self.gateway.history]
        if command == "device/add":
            return self._add_known(data)
        if command == "migration/sources":
            return [s.summary() for s in self._ha_sources()]
        if command == "migration/preview":
            source = self._migration_source(data)
            return self._plan(source, str(data.get("mode") or "same"))
        if command == "migration/import":
            source = self._migration_source(data)
            choices = data.get("choices") if isinstance(data.get("choices"), dict) else None
            return await self._import(source, str(data.get("mode") or "same"), choices)
        if command == "migration/dismiss":
            self.store.meta["migration_dismissed"] = True
            self.store.save()
            self._publish_info()
            return {"dismissed": True}
        if command == "backup/create":
            base = id_to_str(self.gateway.info.base_id) if self.gateway.info else None
            return make_backup(self.store.devices, base or self.store.meta.get("base_id"),
                               __version__, self.config.public(),
                               self.store.meta.get("recom_secret"))
        if command == "device/identify":
            device = self._device(data)
            if not device.product.generic:
                raise RequestError("Identification réservée aux produits génériques")
            identity = {}
            for key in ("brand", "model", "photo", "manual", "pairing"):
                value = str(data.get(key) or "").strip()
                if len(value) > (2000 if key == "pairing" else 500):
                    raise RequestError(f"Champ trop long : {key}")
                identity[key] = value
            if len(identity["brand"]) < 2 or len(identity["model"]) < 2:
                raise RequestError("Marque et référence obligatoires")
            from urllib.parse import urlsplit

            for key in ("photo", "manual"):
                if identity[key]:
                    url = urlsplit(identity[key])
                    if url.scheme != "https" or not url.hostname or url.username or url.password:
                        raise RequestError("Les liens photo et notice doivent être des URL HTTPS")
            entry = {**self.store.devices[device.id_str], "identity": identity}
            self.store.put(entry)
            self._publish_devices()
            return self.device_dict(device)
        if command == "device/compatible":
            device = self._device(data)
            return [self.product_dict(p) for p in self.library.compatible(device.product)]
        if command == "device/change_product":
            return self._change_product(self._device(data), str(data.get("product") or ""))
        if command == "device/settings":
            return describe(self._device(data))
        if command == "device/settings/set":
            device = self._device(data)
            values = data.get("settings")
            if not isinstance(values, dict):
                values = {str(data.get("key")): data.get("value")}
            await self._apply_settings(device, values)
            return describe(device)
        if command.startswith("device/recom/"):
            return await self._recom_request(command.removeprefix("device/recom/"), data)
        if command == "recom/log":
            return list(self.recom_log)
        if command == "pairing/start":
            if not self.gateway_ok:
                raise RequestError("Clé EnOcean non connectée")
            product = self._product(str(data.get("product")))
            timeout = max(10, min(300, int(data.get("timeout") or PAIRING_TIMEOUT)))
            if self._pairing and not self._pairing.done():
                self._pairing.cancel()
            self._pairing = self._task(self._run_pairing(product, timeout))
            return {"product": product.id, "timeout": timeout}
        if command == "pairing/remote":
            return await self._remote_pairing(data)
        if command == "pairing/stop":
            if self._pairing and not self._pairing.done():
                self._pairing.cancel()
            return {}
        if command == "device/rename":
            device = self._device(data)
            entry = self.store.devices[device.id_str]
            old_topic = self.topic_name(device.id_str)
            if name := str(data.get("name") or "").strip():
                entry["name"] = name
                device.title = name
            if "room" in data:
                entry["room"] = (str(data["room"]).strip() or None) if data["room"] else None
            self.store.put(entry)
            if old_topic != self.topic_name(device.id_str):
                self.emit(old_topic, "", True)
                self.emit(f"{old_topic}/availability", "", True)
            self._publish_devices()
            return self.device_dict(device)
        if command == "device/remove":
            device = self._device(data)
            self._remove_device(device.id_str)
            self._publish_devices()
            self._publish_info()
            return {"id": device.id_str}
        if command == "device/set":
            device = self._device(data)
            payload = data.get("payload")
            if isinstance(payload, str):
                payload = text_command(device, payload)
            if not isinstance(payload, dict):
                raise RequestError("Commande attendue : objet JSON dans « payload »")
            await self.command(device, payload)
            return device_payload(device)
        if command == "device/get":
            device = self._device(data)
            if device.product.is_actuator and self.gateway_ok:
                await device.refresh()
                await asyncio.sleep(0.5)
            self._publish_state(device)
            return device_payload(device)
        raise RequestError(f"Commande inconnue : {command}")

    # -- Migration, sauvegarde, restauration ----------------------------------

    def _ha_sources(self) -> list[Source]:
        try:
            return read_homeassistant(self.config["homeassistant"].get("config_dir"))
        except Exception as err:  # noqa: BLE001 - lecture d'un dossier externe
            _LOGGER.warning("Lecture de la configuration Home Assistant impossible : %s", err)
            return []

    def _migration_source(self, data: dict[str, Any]) -> Source:
        if data.get("file") is not None:
            try:
                return parse_file(data["file"])
            except MigrationError as err:
                raise RequestError(str(err)) from err
        sources = self._ha_sources()
        index = int(data.get("index") or 0)
        if not sources or index >= len(sources):
            raise RequestError("NodOcean for HA introuvable dans la configuration de Home "
                               "Assistant")
        return sources[index]

    def _plan(self, source: Source, mode: str) -> dict[str, Any]:
        """Ce que donnera l'import : par produit ok, à réappairer, déjà présent, inconnu."""
        current = id_to_str(self.gateway.info.base_id) if self.gateway_ok and \
            self.gateway.info else None
        mismatch = bool(current and source.base_id and current != source.base_id)
        used = {e.get("sender_offset") for e in self.store.devices.values()}
        items = []
        for entry in source.devices:
            product = self.library.get(entry["product"])
            actuator = bool(product and product.is_actuator)
            existing = self.store.devices.get(entry["id"])
            if product is None:
                status = "unknown"
            elif existing is not None:
                # Déjà présent : on reprend seulement le code ReCom s'il manque
                # (ou si le nôtre n'est qu'un candidat jamais confirmé par le produit).
                status = "code" if entry["recom_code"] is not None and (
                    existing.get("recom_code") is None or existing.get("recom_pending")
                ) and existing.get("recom_code") != entry["recom_code"] else "exists"
            elif actuator and (mode == "new" or mismatch or entry["sender_offset"] is None
                               or entry["sender_offset"] in used):
                status = "repair"
            else:
                status = "ok"
            alts = self.library.compatible(product) if (
                product is not None and product.generic and status != "exists") else []
            alternatives = [p.id for p in alts]
            labels = {p.id: f"{p.brand} {p.model} — {p.name(self.config['language'])}"
                      for p in alts}
            items.append({"id": entry["id"], "name": entry["name"], "room": entry["room"],
                          "product": entry["product"], "alternatives": alternatives,
                          "labels": labels,
                          "model": product.model if product else entry["product"],
                          "brand": product.brand if product else None,
                          "actuator": actuator, "recom": entry["recom_code"] is not None,
                          "status": status})
        return {"source": source.summary(), "mode": mode, "current_base_id": current,
                "key_mismatch": mismatch, "items": items}

    async def _import(self, source: Source, mode: str,
                      choices: dict[str, str] | None = None) -> dict[str, Any]:
        plan = self._plan(source, mode)
        status = {i["id"]: i["status"] for i in plan["items"]}
        # Fiche choisie par l'utilisateur pour les produits génériques (même EEP)
        allowed = {i["id"]: set(i["alternatives"]) for i in plan["items"]}
        choices = {k.upper(): v for k, v in (choices or {}).items()
                   if v in allowed.get(k.upper(), set())}
        imported = repair = codes = 0
        for entry in source.devices:
            if status.get(entry["id"]) == "code":
                stored = self.store.devices[entry["id"]]
                stored["recom_code"] = entry["recom_code"]
                stored["recom_pending"] = entry["recom_pending"]
                if (device := self.devices.get(entry["id"])) is not None:
                    device.recom_code = entry["recom_code"]
                    device.recom_pending = entry["recom_pending"]
                    self.gateway.forget_unlock(device.device_id)
                codes += 1
                continue
            if status.get(entry["id"]) not in ("ok", "repair"):
                continue
            entry = dict(entry)
            if entry["id"] in choices:
                entry["product"] = choices[entry["id"]]
            if status[entry["id"]] == "repair":
                entry["needs_pairing"] = True
                entry["sender_offset"] = None
                repair += 1
            imported += 1
            self.store.devices[entry["id"]] = entry
        if mode == "same" and source.base_id and not plan["key_mismatch"]:
            self.store.meta["base_id"] = source.base_id
        if repair and source.base_id:
            self.store.meta["previous_base_id"] = source.base_id
        self.store.meta["migration_dismissed"] = True
        if source.recom_secret and not any(
            e.get("recom_mode") == "auto" for e in self.store.devices.values()
            if e["id"] not in status
        ):
            # Restauration : on reprend le secret pour recalculer les mêmes codes auto
            self.store.meta["recom_secret"] = source.recom_secret
        self.store.save()
        for device_id, st in status.items():
            if st in ("ok", "repair") and device_id not in self.devices:
                self._add_device(self.store.devices[device_id])
                self.unknown.pop(device_id, None)
        self._publish_devices()
        self._publish_info()
        if self.gateway_ok:
            self._task(self._init_actuators())
        result = {"imported": imported, "repair": repair, "codes": codes,
                  "skipped": len(plan["items"]) - imported - codes, "source": plan["source"]}
        self.emit("bridge/event", {"type": "migration", "data": result})
        return result

    async def command(self, device: Device, payload: dict[str, Any]) -> None:
        settings = {k: v for k, v in payload.items() if is_setting(device, k)}
        controls = {k: v for k, v in payload.items() if k not in settings}
        if settings:
            await self._apply_settings(device, settings)
        if not controls:
            return
        if not device.product.is_actuator:
            raise RequestError(f"{device.title} est un capteur : pas de commande possible")
        try:
            ignored = await apply_command(device, controls)
        except (GatewayError, CommandError, ValueError, TypeError) as err:
            raise RequestError(f"Commande impossible : {err}") from err
        self._publish_state(device)
        if ignored:
            raise RequestError(f"{device.title} ne comprend pas : {', '.join(ignored)}")

    async def _apply_settings(self, device: Device, values: dict[str, Any]) -> None:
        errors: list[str] = []
        for key, value in values.items():
            try:
                await apply_setting(device, key, value)
            except SettingError as err:
                errors.append(str(err))
            except GatewayError as err:
                errors.append(f"{key} : {err}")
        self._save_settings(device)
        self._publish_state(device)
        self._publish_devices()
        if errors:
            raise RequestError("Réglage non appliqué : " + " ; ".join(errors))

    def _change_product(self, device: Device, product_id: str) -> dict[str, Any]:
        """Change la fiche d'un produit (même EEP) : nom, pièce, topic et code gardés."""
        if product_id == device.product.id:
            return self.device_dict(device)
        allowed = {p.id: p for p in self.library.compatible(device.product)}
        if product_id not in allowed:
            raise RequestError("Fiche incompatible : même profil EEP requis "
                               f"({device.product.eep})")
        entry = self.store.devices[device.id_str]
        self._remove_device(device.id_str, keep_entry=True)
        entry["product"] = product_id
        self.store.put(entry)
        new = self._add_device(entry)
        if new is None:
            raise RequestError("Fiche introuvable")
        self._publish_state(new)
        self._publish_devices()
        result = self.device_dict(new)
        self.emit("bridge/event", {"type": "device_changed", "data": result})
        return result

    def _parse_device_id(self, raw: Any) -> tuple[str, int]:
        """Identifiant EnOcean saisi (0x, espaces tolérés) ; refuse les adresses réservées."""
        device_id = re.sub(r"[\s:-]", "", str(raw or "")).upper().removeprefix("0X")
        try:
            value = str_to_id(device_id)
        except ValueError as err:
            raise RequestError(f"Identifiant EnOcean invalide : {device_id}") from err
        device_id = id_to_str(value)
        base = self.gateway.info.base_id if self.gateway.info else None
        if value in (0, 0xFFFFFFFF) or (base is not None and base <= value < base + 128):
            raise RequestError(f"{device_id} n'est pas l'identifiant d'un produit (adresse "
                               "réservée ou adresse de la clé)")
        return device_id, value

    async def _remote_pairing(self, data: dict[str, Any]) -> dict[str, Any]:
        """Appairage d'un actionneur Remote Commissioning sans toucher à son bouton.

        Le produit (juste remis sous tension, ou déverrouillé avec son code) reçoit
        la commande ReMan « Remote Set Learn Mode » : il passe en mode apprentissage
        et envoie sa demande UTE, à laquelle on répond comme pour un appairage normal.
        """
        if not self.gateway_ok:
            raise RequestError("Clé EnOcean non connectée")
        if not self.recom_enabled:
            raise RequestError("Remote Commissioning désactivé dans la configuration")
        product = self._product(str(data.get("product")))
        if not (product.recom and product.is_actuator):
            raise RequestError(f"{product.model} ne gère pas l'appairage à distance")
        device_id, value = self._parse_device_id(data.get("id"))
        code = None
        if str(data.get("code") or "").strip():
            code = recom.parse_code(str(data["code"]))
            if code is None:
                raise RequestError("Code invalide : 8 caractères hexadécimaux (avec ou sans "
                                   "le préfixe 11Z du QR code)")
        if self._pairing and not self._pairing.done():
            self._pairing.cancel()
        timeout = REMOTE_PAIRING_TIMEOUT
        self._pairing = self._task(self._run_pairing(product, timeout, only=value))
        await asyncio.sleep(0.2)
        sender = self.gateway.sender_id(self.store.free_sender_offset())
        try:
            await self.gateway.reman_request(value, sender, recom.remote_learn(0), None, 3.0,
                                             code=code)
        except ReComError as err:
            if err.status is not None:  # refus explicite (code, verrouillé…)
                self._pairing.cancel()
                self._log_recom_id(device_id, "remote_learn", False, str(err))
                raise RequestError(f"Appairage à distance refusé : {err}") from err
            # Pas d'accusé : normal pour cette commande, on attend la demande d'appairage
        self._log_recom_id(device_id, "remote_learn", True, None)
        return {"product": product.id, "id": device_id, "timeout": timeout}

    def _log_recom_id(self, device_id: str, action: str, ok: bool, detail: str | None) -> None:
        entry = {"time": datetime.now(UTC).isoformat(timespec="seconds"), "id": device_id,
                 "name": device_id, "action": action, "ok": ok, "detail": detail}
        self.recom_log.append(entry)
        self.emit("bridge/event", {"type": "recom", "data": entry})

    def _add_known(self, data: dict[str, Any]) -> dict[str, Any]:
        """Appairage en un clic d'un émetteur déjà entendu (capteurs, interrupteurs)."""
        device_id, _value = self._parse_device_id(data.get("id"))
        if device_id in self.devices:
            raise RequestError(f"{device_id} est déjà appairé")
        product = self._product(str(data.get("product")))
        offset = None
        if product.is_actuator:
            offset = self._known_sender_offset(data.get("sender"), device_id)
        name = str(data.get("name") or "").strip() or (
            f"{product.name(self.config['language'])} {device_id[-4:]}")
        entry = {"id": device_id, "product": product.id, "name": name,
                 "room": data.get("room") or None, "sender_offset": offset, "settings": {},
                 "recom_code": None,
                 "paired_at": datetime.now(UTC).isoformat(timespec="seconds")}
        self.store.put(entry)
        device = self._add_device(entry)
        self.unknown.pop(device_id, None)
        self.emit("bridge/unknown", list(self.unknown.values()))
        self._publish_devices()
        self._publish_info()
        result = self.device_dict(device) if device else {"id": device_id}
        self.emit("bridge/event", {"type": "device_joined", "data": result})
        if device is not None and product.is_actuator and self.gateway_ok:
            self._task(self._init_actuator(device))
        return result

    def _known_sender_offset(self, raw: Any, device_id: str) -> int:
        """Adresse d'émission déjà apprise par un actionneur (autre box, même clé)."""
        if not str(raw or "").strip():
            raise RequestError("Un actionneur doit être appairé avec sa procédure, ou déclaré "
                               "avec l'adresse d'émission qu'il a déjà apprise")
        text = re.sub(r"[\s:-]", "", str(raw)).upper().removeprefix("0X")
        try:
            address = str_to_id(text)
        except ValueError as err:
            raise RequestError(f"Adresse d'émission invalide : {text}") from err
        if self.gateway.info is None:
            raise RequestError("Clé EnOcean non connectée")
        base = self.gateway.info.base_id
        offset = address - base
        if not 0 <= offset < 128:
            raise RequestError(
                f"L'adresse {id_to_str(address)} n'appartient pas à cette clé (de "
                f"{id_to_str(base)} à {id_to_str(base + 127)}) : utilisez la même clé que "
                "l'autre box, ou donnez-lui son Base ID (Réglages → Clé EnOcean)")
        for other in self.store.devices.values():
            if other["id"] != device_id and other.get("sender_offset") == offset:
                raise RequestError(f"L'adresse {id_to_str(address)} est déjà utilisée pour "
                                   f"« {other['name']} »")
        return offset

    # -- Remote Commissioning ------------------------------------------------

    @property
    def recom_enabled(self) -> bool:
        return bool(self.config["recom"].get("enabled", True))

    def _set_recom(self, enabled: bool) -> dict[str, Any]:
        """Active / désactive le Remote Commissioning depuis l'interface (prioritaire)."""
        self.config.update("recom", {"enabled": enabled}, ui=True)
        self.gateway.reman_enabled = enabled
        _LOGGER.warning("Remote Commissioning %s depuis l'interface",
                        "activé" if enabled else "désactivé")
        self._publish_info()
        self._publish_devices()  # réglages du groupe « recom » ajoutés ou retirés (+ découverte)
        return {"enabled": enabled}

    def auto_code(self, device: Device) -> int:
        return recom.derive_code(self.store.meta["recom_secret"], device.device_id)

    async def _recom_request(self, action: str, data: dict[str, Any]) -> Any:
        device = self._device(data)
        if not self.recom_enabled:
            raise RequestError("Remote Commissioning désactivé dans la configuration "
                               "(recom.enabled)")
        if not device.product.recom:
            raise RequestError(f"{device.title} ne gère pas le Remote Commissioning")
        if not self.gateway_ok:
            raise RequestError("Clé EnOcean non connectée")
        sender = self.gateway.sender_id(device.sender_offset or 0)
        detail: Any = None
        try:
            if action == "status":
                return self.recom_status(device)
            if action == "ping":
                ok = await self.gateway.ping(device.device_id, sender)
                detail = "répond" if ok else "muet"
                if not ok:
                    raise ReComError("Le produit ne répond pas au Ping", "no_answer")
            elif action == "unlock":
                detail = await device.unlock_recom()
            elif action == "assign":
                mode = str(data.get("mode") or "auto")
                if mode not in recom.CODE_MODES:
                    raise RequestError(f"Mode de code inconnu : {mode}")
                if mode == "none":
                    await device.set_no_code()
                    detail = "sans code"
                else:
                    if mode == "auto":
                        code = self.auto_code(device)
                    else:
                        code = recom.parse_code(str(data.get("code") or ""))
                        if code is None:
                            raise RequestError("Code invalide : 8 caractères hexadécimaux "
                                               "(avec ou sans le préfixe 11Z du QR code)")
                    detail = await device.unlock_recom(code, mode)
            elif action == "detect":
                candidates = [("auto", self.auto_code(device))]
                if device.recom_code is not None:
                    candidates.insert(0, (device.recom_mode or "custom", device.recom_code))
                extra = recom.parse_code(str(data.get("code") or ""))
                if extra is not None:
                    candidates.append(("custom", extra))
                found = await device.detect_code(candidates)
                if found is None:
                    if await self.gateway.ping(device.device_id, sender):
                        raise ReComError("Aucun code connu accepté : le produit a un autre "
                                         "code, ou n'en a pas (déverrouillage possible "
                                         "seulement juste après sa mise sous tension)",
                                         "unknown_code")
                    raise ReComError("Le produit ne répond pas au Ping", "no_answer")
                detail = f"code {found}"
            elif action == "code":
                code = recom.parse_code(str(data.get("code") or ""))
                if code is None:
                    raise RequestError("Code invalide : 8 caractères hexadécimaux (avec ou sans "
                                       "le préfixe 11Z du QR code)")
                await device.use_code(code)
                detail = "code accepté"
            elif action == "links":
                links = await device.read_links()
                detail = f"{len(links)} télécommande(s)"
            elif action == "links/add":
                link_type = str(data.get("type") or "")
                if link_type not in LINK_TYPES:
                    raise RequestError(f"Type de télécommande inconnu : {link_type}")
                try:
                    link_id = str_to_id(str(data.get("link_id") or ""))
                except ValueError as err:
                    raise RequestError("Identifiant de télécommande invalide") from err
                index = await device.add_link(link_id, link_type)
                detail = f"ajoutée en position {index}"
            elif action == "links/delete":
                index = int(data.get("index"))
                await device.delete_link(index)
                detail = f"position {index} supprimée"
            elif action == "config":
                if not device.product.has("roller_shutter"):
                    raise RequestError("Paramètres lisibles uniquement sur le volet roulant")
                detail = await device.rs_read_config()
            else:
                raise RequestError(f"Commande ReCom inconnue : {action}")
        except ReComError as err:
            self._log_recom(device, action, False, str(err))
            raise RequestError(f"ReCom : {err}") from err
        except GatewayError as err:
            self._log_recom(device, action, False, str(err))
            raise RequestError(f"ReCom : {err}") from err
        self._log_recom(device, action, True, detail)
        self._publish_devices()
        return self.recom_status(device)

    def _log_recom(self, device: Device, action: str, ok: bool, detail: Any) -> None:
        entry = {"time": datetime.now(UTC).isoformat(timespec="seconds"), "id": device.id_str,
                 "name": device.title, "action": action, "ok": ok,
                 "detail": detail if isinstance(detail, str) else None}
        self.recom_log.append(entry)
        self.emit("bridge/event", {"type": "recom", "data": entry})
