"""Base ID de la clé (reprise d'une clé HS) et réglages MQTT depuis l'interface."""

from __future__ import annotations

import asyncio

import pytest
from test_app import _free_port, _pair, app  # noqa: F401 (fixture)

from ocean2mqtt.app import Ocean2MQTT, RequestError
from ocean2mqtt.config import Config

RELAY = 0x05112233


async def test_clone_base_id_restores_actuators(app: Ocean2MQTT) -> None:  # noqa: F811
    info = await app.request("info", {})
    assert info["gateway"]["base_id_writes_left"] == 10
    await _pair(app, "nodon/sin-2-2-01", 0xD4, "A0 02 46 00 12 01 D2", RELAY)
    old = info["gateway"]["base_id"]
    # Nouvelle clé (Base ID différent) : l'actionneur est à réappairer
    app.dongle.base_id = 0xFF9A0000
    app.gateway.info = await app.gateway._read_info()
    app._check_base_id()
    assert app.store.devices["05112233"]["needs_pairing"]
    assert app.store.meta["previous_base_id"] == old
    # On écrit l'ancien Base ID dans la nouvelle clé : plus rien à réappairer
    result = await app.request("gateway/base_id", {"base_id": old})
    assert result["base_id"] == old and result["writes_left"] == 9
    assert result["restored"] == [app.store.devices["05112233"]["name"]]
    assert "needs_pairing" not in app.store.devices["05112233"]
    assert "previous_base_id" not in app.store.meta
    with pytest.raises(RequestError, match="déjà ce Base ID"):
        await app.request("gateway/base_id", {"base_id": old})
    with pytest.raises(RequestError, match="invalide"):
        await app.request("gateway/base_id", {"base_id": "FF9A0001"})
    with pytest.raises(RequestError, match="invalide"):
        await app.request("gateway/base_id", {"base_id": "01234567"})
    app.dongle.base_id_writes_left = 0
    with pytest.raises(RequestError, match="nombre maximal"):
        await app.request("gateway/base_id", {"base_id": "FF9A0080"})
    await asyncio.sleep(0)


def test_ui_settings_override_environment(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OCEAN2MQTT_MQTT_HOST", '"core-mosquitto"')
    monkeypatch.setenv("OCEAN2MQTT_MQTT_PASSWORD", '"secret-supervisor"')
    config = Config(tmp_path).load()
    assert config["mqtt"]["host"] == "core-mosquitto" and config.is_auto("mqtt")
    # Le mot de passe venu de l'environnement n'est jamais écrit dans le fichier
    assert "secret-supervisor" not in config.path.read_text(encoding="utf-8")
    config.update("mqtt", {"host": "192.168.1.10", "base_topic": "maison"}, ui=True)
    again = Config(tmp_path).load()
    assert again["mqtt"]["host"] == "192.168.1.10" and again["mqtt"]["base_topic"] == "maison"
    assert again["mqtt"]["password"] == "secret-supervisor"  # pas remplacé : reste auto
    assert "ui_overrides" not in again.public()
    again.reset_ui("mqtt")
    assert Config(tmp_path).load()["mqtt"]["host"] == "core-mosquitto"


async def test_mqtt_settings_from_interface(app: Ocean2MQTT) -> None:  # noqa: F811
    amqtt_broker = pytest.importorskip("amqtt.broker")
    port = _free_port()
    broker = amqtt_broker.Broker({
        "listeners": {"default": {"type": "tcp", "bind": f"127.0.0.1:{port}"}},
        "plugins": {"amqtt.plugins.authentication.AnonymousAuthPlugin": {"allow_anonymous": True}},
    })
    await broker.start()
    restarts: list[str] = []

    async def restart() -> None:
        restarts.append(app.config["mqtt"]["base_topic"])

    app.mqtt_restart = restart
    try:
        with pytest.raises(RequestError, match="Connexion MQTT impossible"):
            await app.request("config/mqtt/set", {"host": "127.0.0.1", "port": _free_port()})
        with pytest.raises(RequestError, match="Topic invalide"):
            await app.request("config/mqtt/set", {"base_topic": "a b"})
        assert restarts == []
        settings = await app.request("config/mqtt/set", {
            "host": "127.0.0.1", "port": str(port), "base_topic": "/maison/",
            "username": "", "password": ""})
        assert settings["host"] == "127.0.0.1" and settings["port"] == port
        assert settings["base_topic"] == "maison" and not settings["has_password"]
        assert restarts == ["maison"]
        mq = await app.request("config/mqtt", {})
        assert mq["base_topic"] == "maison" and mq["editable"]
    finally:
        await broker.shutdown()


async def test_mqtt_restart_moves_base_topic(app: Ocean2MQTT) -> None:  # noqa: F811
    amqtt_broker = pytest.importorskip("amqtt.broker")
    import paho.mqtt.client as mqtt

    from ocean2mqtt.mqtt import MqttBridge, restart_bridge

    port = _free_port()
    broker = amqtt_broker.Broker({
        "listeners": {"default": {"type": "tcp", "bind": f"127.0.0.1:{port}"}},
        "plugins": {"amqtt.plugins.authentication.AnonymousAuthPlugin": {"allow_anonymous": True}},
    })
    await broker.start()
    app.config.update("mqtt", {"enabled": True, "host": "127.0.0.1", "port": port})
    app.mqtt_bridge = MqttBridge(app)
    app.mqtt_restart = lambda: restart_bridge(app)
    received: dict[str, str] = {}
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="t2")
    client.on_message = lambda c, u, m: received.__setitem__(m.topic, m.payload.decode())
    loop = asyncio.get_running_loop()
    try:
        await app.mqtt_bridge.start()
        for _ in range(100):
            if app.mqtt_bridge.connected:
                break
            await asyncio.sleep(0.05)
        await loop.run_in_executor(None, client.connect, "127.0.0.1", port)
        client.subscribe([("#", 0)])
        client.loop_start()
        await asyncio.sleep(0.4)
        assert received.get("ocean2mqtt/bridge/state") == "online"
        await app.request("config/mqtt/set", {"base_topic": "maison"})
        for _ in range(100):
            if received.get("maison/bridge/state") == "online":
                break
            await asyncio.sleep(0.05)
        assert received["maison/bridge/state"] == "online"
        assert received["ocean2mqtt/bridge/state"] == ""  # ancien topic nettoyé
        assert (await app.request("info", {}))["mqtt"]["connected"]
    finally:
        client.loop_stop()
        client.disconnect()
        await app.mqtt_bridge.stop()
        await broker.shutdown()


async def test_other_base_id_flags_actuators(app: Ocean2MQTT) -> None:  # noqa: F811
    await _pair(app, "nodon/sin-2-2-01", 0xD4, "A0 02 46 00 12 01 D2", RELAY)
    old = (await app.request("info", {}))["gateway"]["base_id"]
    result = await app.request("gateway/base_id", {"base_id": "FF9A0080"})
    assert result["restored"] == []
    assert app.store.devices["05112233"]["needs_pairing"]
    assert app.store.meta["previous_base_id"] == old
    # Retour à l'ancien : tout revient
    result = await app.request("gateway/base_id", {"base_id": old})
    assert len(result["restored"]) == 1 and "needs_pairing" not in app.store.devices["05112233"]
    await asyncio.sleep(0)


async def test_add_by_enocean_id(app: Ocean2MQTT) -> None:  # noqa: F811
    """Produit ajouté par son identifiant, sans télégramme d'apprentissage."""
    device = await app.request("device/add", {"id": " 0x0199aabb", "product": "generique/F6-02-01"})
    assert device["id"] == "0199AABB"
    app.dongle.inject(0xF6, bytes([0x30]), 0x0199AABB, status=0x30)
    await asyncio.sleep(0.05)
    assert "0199AABB" in app.last_seen  # reconnu dès son premier télégramme
    base = app.gateway.info.base_id
    for bad in ("00000000", "FFFFFFFF", f"{base + 5:08X}"):
        with pytest.raises(RequestError, match="réservée"):
            await app.request("device/add", {"id": bad, "product": "generique/F6-02-01"})
    with pytest.raises(RequestError, match="actionneur"):
        await app.request("device/add", {"id": "05999999", "product": "nodon/sin-2-1-01"})
