"""Pont MQTT : publie les topics du service et reçoit commandes et requêtes.

Topics (base « ocean2mqtt ») :
- <base>/bridge/state                online / offline (dernière volonté)
- <base>/bridge/info, bridge/devices  état de la passerelle, produits appairés
- <base>/bridge/event                 appairage, nouveau produit…
- <base>/bridge/request/<commande>    requêtes -> réponse sur bridge/response/<commande>
- <base>/<produit>                    état JSON ; /availability ; /action (boutons)
- <base>/<produit>/set, /get          commandes, relecture
"""

from __future__ import annotations

import asyncio
import json
import logging
import ssl
from typing import TYPE_CHECKING, Any

from .core.exposes import Expose, exposes
from .core.settings import settings_for

if TYPE_CHECKING:
    import paho.mqtt.client as mqtt

    from .app import Ocean2MQTT
    from .core.device import Device

_LOGGER = logging.getLogger(__name__)

ORIGIN = {"name": "Ocean2MQTT", "support_url": "https://github.com/eHomeLabs/Ocean2MQTT"}

# Noms des réglages (entités « configuration » de HA)
SETTING_NAMES = {
    "fr": {"led": "LED", "local_control": "Bouton local", "taught_in": "Télécommandes directes",
           "power_failure": "Détection de coupure", "power_on_state": "État au retour du courant",
           "switch_type": "Type d'interrupteur", "auto_off": "Extinction automatique",
           "delay_off": "Extinction retardée", "travel_time": "Temps de course",
           "rs_switch_type": "Type d'interrupteur (volet)", "calibration": "Calibration",
           "repeater": "Répéteur", "energy_reset": "Remise à zéro de l'énergie",
           "buttons": "Nombre de boutons", "temperature_offset": "Correction température",
           "humidity_offset": "Correction humidité", "timeout": "Délai d'indisponibilité"},
    "en": {"led": "LED", "local_control": "Local button", "taught_in": "Direct remotes",
           "power_failure": "Power failure detection", "power_on_state": "Power-on state",
           "switch_type": "Switch type", "auto_off": "Auto off", "delay_off": "Delay off",
           "travel_time": "Travel time", "rs_switch_type": "Switch type (shutter)",
           "calibration": "Calibration", "repeater": "Repeater",
           "energy_reset": "Reset energy", "buttons": "Number of buttons",
           "temperature_offset": "Temperature offset", "humidity_offset": "Humidity offset",
           "timeout": "Unavailability timeout"},
}

# Noms des entités (la découverte MQTT de HA n'est pas traduisible)
NAMES = {
    "fr": {"channel": "Canal {n}", "mode": "Mode fil pilote", "action": "Boutons",
           "rssi": "Signal", "bridge": "Connexion", "gateway": "Passerelle Ocean2MQTT",
           "setpoint": "Consigne", "valve_position": "Ouverture vanne", "card": "Carte insérée",
           "handle": "Poignée", "voc": "COV"},
    "en": {"channel": "Channel {n}", "mode": "Pilot wire mode", "action": "Buttons",
           "rssi": "Signal", "bridge": "Connection", "gateway": "Ocean2MQTT gateway",
           "setpoint": "Setpoint", "valve_position": "Valve opening", "card": "Card inserted",
           "handle": "Handle", "voc": "VOC"},
}


def _v(key: str, expr: str | None = None) -> str:
    """Modèle Jinja : valeur de la clé, vide si absente (HA ignore alors le message)."""
    return (
        f"{{% if value_json.{key} is defined %}}{{{{ {expr or 'value_json.' + key} }}}}"
        "{% endif %}"
    )


def discovery_configs(
    app: Ocean2MQTT, device: Device, base: str, prefix: str
) -> dict[str, dict[str, Any]]:
    """Topic de configuration -> configuration, pour un produit."""
    names = NAMES["fr" if app.config["language"].startswith("fr") else "en"]
    product = device.product
    topic = f"{base}/{app.topic_name(device.id_str)}"
    node = f"ocean2mqtt_{(app.gateway.info.base_id if app.gateway.info else 0):08x}"
    common = {
        "device": {
            "identifiers": [f"ocean2mqtt_{device.id_str}"],
            "name": device.title,
            "manufacturer": product.brand,
            "model": product.references,
            "model_id": product.model,
            "serial_number": device.id_str,
            "via_device": node,
        },
        "origin": ORIGIN,
        "availability": [{"topic": f"{base}/bridge/state"}, {"topic": f"{topic}/availability"}],
        "availability_mode": "all",
        "state_topic": topic,
    }
    out: dict[str, dict[str, Any]] = {}

    def add(component: str, expose: Expose, cfg: dict[str, Any]) -> None:
        object_id = f"{device.id_str}_{expose.key}"
        conf = {**common, "unique_id": f"ocean2mqtt_{object_id}", **cfg}
        if expose.category:
            conf["entity_category"] = expose.category
        out[f"{prefix}/{component}/{node}/{object_id}/config"] = conf

    cmd = f"{topic}/set"
    for e in exposes(product):
        if e.kind == "switch":
            add("switch", e, {"name": None, "command_topic": cmd, "payload_on": "ON",
                              "payload_off": "OFF", "value_template": _v(e.key),
                              "state_on": "ON", "state_off": "OFF",
                              "device_class": e.device_class})
        elif e.kind == "light":
            n = e.key.removeprefix("state_l")
            add("light", e, {"name": names["channel"].format(n=n), "schema": "template",
                             "command_topic": cmd,
                             "command_on_template": f'{{"{e.key}": "ON"}}',
                             "command_off_template": f'{{"{e.key}": "OFF"}}',
                             "state_template": _v(e.key, f"value_json.{e.key} | lower")})
        elif e.kind == "cover":
            add("cover", e, {"name": None, "device_class": "shutter", "command_topic": cmd,
                             "payload_open": "OPEN", "payload_close": "CLOSE",
                             "payload_stop": "STOP", "position_topic": topic,
                             "position_template": _v("position"), "set_position_topic": cmd,
                             "set_position_template": '{"position": {{ position }}}',
                             "value_template": _v("state", "value_json.state | lower"),
                             "state_open": "open", "state_closed": "closed"})
        elif e.kind == "select":
            add("select", e, {"name": names.get(e.key, e.key), "command_topic": cmd,
                              "command_template": f'{{"{e.key}": "{{{{ value }}}}"}}',
                              "value_template": _v(e.key), "options": list(e.options)})
        elif e.kind == "number":
            add("number", e, {"name": names.get(e.key, e.key), "command_topic": cmd,
                              "command_template": f'{{"{e.key}": {{{{ value }}}}}}',
                              "value_template": _v(e.key), "min": e.min, "max": e.max,
                              "step": e.step, "unit_of_measurement": e.unit,
                              "device_class": e.device_class, "mode": "box"})
        elif e.kind == "sensor":
            cfg: dict[str, Any] = {"value_template": _v(e.key), "unit_of_measurement": e.unit,
                                   "state_class": e.state_class}
            if e.device_class:
                cfg["device_class"] = e.device_class
            if e.key in names:
                cfg["name"] = names[e.key]
            if e.key == "rssi":
                cfg["enabled_by_default"] = False
            add("sensor", e, cfg)
        elif e.kind == "enum":
            add("sensor", e, {"name": names.get(e.key, e.key), "device_class": "enum",
                              "options": list(e.options), "value_template": _v(e.key)})
        elif e.kind == "binary_sensor":
            cfg = {"payload_on": "ON", "payload_off": "OFF",
                   "value_template": _v(e.key, f"'ON' if value_json.{e.key} else 'OFF'")}
            if e.device_class:
                cfg["device_class"] = e.device_class
            if e.key in names:
                cfg["name"] = names[e.key]
            add("binary_sensor", e, cfg)
        elif e.kind == "event":
            add("event", e, {"name": names["action"], "device_class": "button",
                             "state_topic": f"{topic}/action", "event_types": list(e.options),
                             "value_template": '{"event_type": "{{ value }}"}'})
    labels = SETTING_NAMES["fr" if app.config["language"].startswith("fr") else "en"]
    for s in settings_for(device):
        base_key = s.key.rsplit("_l", 1)[0] if s.channel is not None else s.key
        name = labels.get(base_key, s.key)
        if s.channel is not None and product.channels > 1:
            name = f"{name} {s.channel + 1}"
        e = Expose(s.key, s.kind, category="config")
        if s.kind == "binary":
            add("switch", e, {"name": name, "command_topic": cmd,
                              "command_template": f'{{"{s.key}": "{{{{ value }}}}"}}',
                              "payload_on": "ON", "payload_off": "OFF",
                              "value_template": _v(s.key), "state_on": "ON",
                              "state_off": "OFF"})
        elif s.kind == "enum":
            add("select", e, {"name": name, "command_topic": cmd,
                              "command_template": f'{{"{s.key}": "{{{{ value }}}}"}}',
                              "value_template": _v(s.key), "options": list(s.options)})
        elif s.kind == "numeric":
            add("number", e, {"name": name, "command_topic": cmd,
                              "command_template": f'{{"{s.key}": {{{{ value }}}}}}',
                              "value_template": _v(s.key), "min": s.min, "max": s.max,
                              "step": s.step, "unit_of_measurement": s.unit, "mode": "box"})
        elif s.key == "energy_reset":
            add("button", e, {"name": name, "command_topic": cmd,
                              "payload_press": '{"energy_reset": "reset"}'})
    return out


def _new_client(settings: dict[str, Any], client_id: str) -> mqtt.Client:
    import paho.mqtt.client as mqtt

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id,
                         protocol=mqtt.MQTTv311)
    if settings.get("username"):
        client.username_pw_set(settings["username"], settings.get("password"))
    if settings.get("tls"):
        insecure = bool(settings.get("tls_insecure"))
        client.tls_set(ca_certs=settings.get("ca") or None,
                       cert_reqs=ssl.CERT_NONE if insecure else ssl.CERT_REQUIRED)
        if insecure:
            client.tls_insecure_set(True)
    client.reconnect_delay_set(min_delay=1, max_delay=60)
    return client


class MqttBridge:
    def __init__(self, app: Ocean2MQTT) -> None:
        self.app = app
        self.settings = app.config["mqtt"]
        self.base = str(self.settings["base_topic"]).strip("/") or "ocean2mqtt"
        self.prefix = str(self.settings["discovery_prefix"]).strip("/") or "homeassistant"
        self.connected = False
        self._client: mqtt.Client | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._discovery: dict[str, dict] = {}
        self._unsubs: list = []

    # -- Cycle de vie -------------------------------------------------------

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        gw = self.app.gateway.info
        client_id = self.settings.get("client_id") or (
            f"ocean2mqtt-{gw.base_id:08x}" if gw else "ocean2mqtt"
        )
        client = await self._loop.run_in_executor(None, _new_client, self.settings, client_id)
        client.will_set(self._t("bridge/state"), "offline", qos=1, retain=True)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_connect_fail = self._on_connect_fail
        client.on_message = self._on_message
        self._client = client
        self._unsubs.append(self.app.subscribe(self._on_emit))
        try:
            await self._loop.run_in_executor(
                None, client.connect_async, self.settings["host"], int(self.settings["port"]), 60
            )
        except (OSError, ValueError) as err:
            _LOGGER.warning("MQTT : %s", err)
        client.loop_start()

    async def stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        client, self._client = self._client, None
        if client is None:
            return

        def _stop() -> None:
            if self.connected:
                info = client.publish(self._t("bridge/state"), "offline", qos=1, retain=True)
                try:
                    info.wait_for_publish(timeout=2)
                except (RuntimeError, ValueError):
                    pass
            self.connected = False
            client.disconnect()
            client.loop_stop()

        await asyncio.get_running_loop().run_in_executor(None, _stop)

    def _t(self, topic: str) -> str:
        return f"{self.base}/{topic}"

    # -- Découverte HA -------------------------------------------------------

    def _discovery_node(self) -> str:
        gw = self.app.gateway.info
        return f"ocean2mqtt_{(gw.base_id if gw else 0):08x}"

    def _build_discovery(self) -> dict[str, dict]:
        if not self.settings.get("discovery"):
            return {}
        node = self._discovery_node()
        names = NAMES["fr" if self.app.config["language"].startswith("fr") else "en"]
        configs: dict[str, dict] = {
            f"{self.prefix}/binary_sensor/{node}/bridge/config": {
                "name": names["bridge"],
                "unique_id": f"{node}_bridge",
                "device_class": "connectivity",
                "entity_category": "diagnostic",
                "state_topic": self._t("bridge/state"),
                "payload_on": "online",
                "payload_off": "offline",
                "device": {"identifiers": [node], "name": names["gateway"],
                           "manufacturer": "eHomeLabs", "model": "Ocean2MQTT",
                           "sw_version": self.app.info()["version"]},
                "origin": ORIGIN,
            }
        }
        for device in self.app.devices.values():
            configs.update(discovery_configs(self.app, device, self.base, self.prefix))
        return configs

    def _sync_discovery(self) -> None:
        """Publie les configurations et retire celles des produits supprimés."""
        if self._client is None or not self.connected:
            return
        new = self._build_discovery()
        for topic in set(self._discovery) - set(new):
            self._client.publish(topic, "", qos=1, retain=True)
        for topic, config in new.items():
            if self._discovery.get(topic) != config:
                self._client.publish(topic, json.dumps(config, ensure_ascii=False), qos=1,
                                     retain=True)
        self._discovery = new

    def _is_discovery_topic(self, topic: str) -> bool:
        parts = topic.split("/")
        return (len(parts) >= 5 and topic.startswith(self.prefix + "/")
                and parts[-3] == self._discovery_node() and parts[-1] == "config")

    # -- Callbacks paho (fil réseau) -----------------------------------------

    def _on_connect(self, client, _userdata, _flags, reason_code, _props) -> None:
        if reason_code.is_failure:
            self.connected = False
            _LOGGER.warning("MQTT : connexion refusée (%s)", reason_code)
            return
        self.connected = True
        _LOGGER.info("MQTT connecté à %s:%s (topic %s)", self.settings["host"],
                     self.settings["port"], self.base)
        qos = int(self.settings.get("qos") or 0)
        client.subscribe([
            (self._t("+/set"), qos),
            (self._t("+/get"), qos),
            (self._t("bridge/request/#"), qos),
            (f"{self.prefix}/+/{self._discovery_node()}/+/config", 1),
        ])
        self._loop.call_soon_threadsafe(self._publish_snapshot)

    def _on_connect_fail(self, _client, _userdata) -> None:
        _LOGGER.warning("MQTT : broker %s:%s injoignable, nouvel essai…", self.settings["host"],
                        self.settings["port"])

    def _on_disconnect(self, _client, _userdata, _flags, reason_code, _props) -> None:
        if self.connected:
            _LOGGER.warning("MQTT déconnecté (%s), reconnexion…", reason_code)
        self.connected = False

    def _on_message(self, client, _userdata, message) -> None:
        topic = message.topic
        if self._is_discovery_topic(topic):
            # Configuration retenue d'un produit supprimé : on l'efface.
            if message.payload and topic not in self._discovery and self._discovery is not None:
                self._loop.call_soon_threadsafe(self._clean_discovery, topic)
            return
        payload = bytes(message.payload)
        self._loop.call_soon_threadsafe(self._handle, topic, payload)

    def _clean_discovery(self, topic: str) -> None:
        if topic not in self._discovery and self._client is not None:
            self._client.publish(topic, "", qos=1, retain=True)

    # -- Publication ---------------------------------------------------------

    def _publish(self, topic: str, payload: Any, retain: bool) -> None:
        if self._client is None or not self.connected:
            return
        if not isinstance(payload, str):
            payload = json.dumps(payload, ensure_ascii=False)
        retain = retain and bool(self.settings.get("retain", True)) or (retain and payload == "")
        self._client.publish(self._t(topic), payload,
                             qos=int(self.settings.get("qos") or 0), retain=retain)

    def _publish_snapshot(self) -> None:
        self._sync_discovery()
        for topic, payload in list(self.app.retained.items()):
            self._publish(topic, payload, True)
        self._publish("bridge/state", "online", True)

    def _on_emit(self, topic: str, payload: Any, retain: bool) -> None:
        if topic == "bridge/telegrams" and not self.settings.get("telegrams"):
            return
        self._publish(topic, payload, retain)
        if topic in ("bridge/devices", "bridge/info"):
            self._sync_discovery()

    # -- Réception -----------------------------------------------------------

    def _handle(self, topic: str, payload: bytes) -> None:
        rel = topic[len(self.base) + 1:] if topic.startswith(self.base + "/") else None
        if rel is None:
            return
        text = payload.decode("utf-8", errors="replace").strip()
        if rel.startswith("bridge/request/"):
            self.app._task(self._request(rel.removeprefix("bridge/request/"), text))
            return
        name, _, verb = rel.rpartition("/")
        device = self.app.device_by_topic(name)
        if device is None or verb not in ("set", "get"):
            return
        if verb == "get":
            self.app._task(self.app.request("device/get", {"id": device.id_str}))
            return
        try:
            data = json.loads(text) if text.startswith("{") else text
        except ValueError:
            _LOGGER.warning("MQTT : JSON invalide sur %s : %s", topic, text)
            return
        self.app._task(self._set(device, data))

    async def _set(self, device: Device, data: Any) -> None:
        from .app import RequestError

        try:
            await self.app.request("device/set", {"id": device.id_str, "payload": data})
        except RequestError as err:
            _LOGGER.warning("MQTT : %s", err)

    async def _request(self, command: str, text: str) -> None:
        from .app import RequestError

        try:
            data = json.loads(text) if text else {}
        except ValueError:
            data = {"value": text}
        if not isinstance(data, dict):
            data = {"value": data}
        transaction = data.pop("transaction", None)
        try:
            result = {"status": "ok", "data": await self.app.request(command, data)}
        except RequestError as err:
            result = {"status": "error", "error": str(err)}
        if transaction is not None:
            result["transaction"] = transaction
        self._publish(f"bridge/response/{command}", result, False)
