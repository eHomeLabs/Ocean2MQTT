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
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from . import __version__
from .config import Config, DeviceStore
from .core.convert import CommandError, apply_command, device_payload, text_command
from .core.device import AVAILABILITY_KEY, Device
from .core.esp3 import id_to_str, str_to_id
from .core.exposes import exposes
from .core.gateway import Gateway, GatewayError
from .core.pairing import wait_for_teach_in
from .core.product import Product
from .library import Library, load_library

_LOGGER = logging.getLogger(__name__)

Listener = Callable[[str, Any, bool], None]  # topic, données, retenu

PAIRING_TIMEOUT = 60
RECONNECT_DELAY = 15


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
        self.gateway = Gateway(config["serial"]["port"])
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

    async def start(self) -> None:
        self.gateway.on_disconnect = self._on_gateway_lost
        await self._connect_gateway(wait=False)
        for entry in list(self.store.devices.values()):
            self._add_device(entry)
        self._task(self._availability_loop())
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
        self.gateway.close()
        self.emit("bridge/state", "offline", True)

    async def _connect_gateway(self, wait: bool = True) -> None:
        """Ouvre la clé ; en cas d'échec, réessaie en tâche de fond."""
        try:
            await self.gateway.connect()
            self.gateway_ok = True
            _LOGGER.info("Clé EnOcean prête, Base ID %s", id_to_str(self.gateway.info.base_id))
            for device in self.devices.values():
                if device.product.is_actuator:
                    self._task(device.refresh())
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

    async def _availability_loop(self) -> None:
        while True:
            await asyncio.sleep(30)
            for device in self.devices.values():
                device.notify({AVAILABILITY_KEY})

    # -- Produits ------------------------------------------------------------

    def _product(self, product_id: str) -> Product:
        try:
            return self.library.products[product_id]
        except KeyError as err:
            raise RequestError(f"Produit inconnu dans la bibliothèque : {product_id}") from err

    def _add_device(self, entry: dict[str, Any]) -> Device | None:
        product = self.library.products.get(entry["product"])
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
        device.on_code_change = self._save_code
        self.devices[entry["id"]] = device
        self._unsubs[entry["id"]] = device.add_listener(self._listener(device), first=True)
        device.start()
        self._available[entry["id"]] = device.available
        return device

    async def _save_code(self, device: Device) -> None:
        entry = self.store.devices[device.id_str]
        entry["recom_code"] = device.recom_code
        entry["recom_pending"] = device.recom_pending
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
            "manual": product.manual,
            "image": self._image_url(product),
            "variants": list(product.variants),
            "recom": product.recom,
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
            "state": device_payload(device),
            "available": device.available,
            "last_seen": self.last_seen.get(device.id_str),
            "actuator": product.is_actuator,
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
            if "setpoint" in keys:
                entry = self.store.devices[device.id_str]
                entry["settings"] = {**entry.get("settings", {}), "setpoint": device.settings.get(
                    "setpoint")}
                self.store.put(entry)
            event = device.state.pop("event", None) if "event" in keys else None
            if event:
                self.emit(f"{topic}/action", event, False)
            self._publish_state(device)

        return _update

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
            },
            "language": self.config["language"],
            "pairing": self.pairing,
            "config": self.config.public(),
            "devices": len(self.devices),
        }

    # -- Appairage -----------------------------------------------------------

    async def _run_pairing(self, product: Product, timeout: int) -> None:
        offset = self.store.free_sender_offset() if product.is_actuator else None
        self.pairing = {"product": product.id, "timeout": timeout,
                        "until": round(time.time() + timeout)}
        self.emit("bridge/event", {"type": "pairing", "data": {"status": "started",
                                                               **self.pairing}})
        self._publish_info()
        try:
            result = await wait_for_teach_in(self.gateway, product, offset, timeout, set())
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
            await device.refresh()

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
        if command == "library":
            products = self.library.search(data["search"]) if data.get("search") else list(
                self.library.products.values())
            return [self.product_dict(p) for p in products]
        if command == "pairing/start":
            if not self.gateway_ok:
                raise RequestError("Clé EnOcean non connectée")
            product = self._product(str(data.get("product")))
            timeout = max(10, min(300, int(data.get("timeout") or PAIRING_TIMEOUT)))
            if self._pairing and not self._pairing.done():
                self._pairing.cancel()
            self._pairing = self._task(self._run_pairing(product, timeout))
            return {"product": product.id, "timeout": timeout}
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

    async def command(self, device: Device, payload: dict[str, Any]) -> None:
        if not device.product.is_actuator:
            raise RequestError(f"{device.title} est un capteur : pas de commande possible")
        try:
            ignored = await apply_command(device, payload)
        except (GatewayError, CommandError, ValueError, TypeError) as err:
            raise RequestError(f"Commande impossible : {err}") from err
        self._publish_state(device)
        if ignored:
            raise RequestError(f"{device.title} ne comprend pas : {', '.join(ignored)}")
