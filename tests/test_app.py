"""Service complet sans matériel : appairage, état, commandes, MQTT, WebSocket."""

from __future__ import annotations

import asyncio
import json
import socket

import pytest
from fake_dongle import BASE_ID, FakeDongle

from ocean2mqtt.app import Ocean2MQTT, RequestError
from ocean2mqtt.config import Config

FP = 0x051E575A
STPH = 0x0181A2B3
VALVE = 0x01A0B0C0


async def _stop_broker(broker) -> None:
    """Arrêt du broker de test borné : amqtt attend parfois sans fin la fin des sessions."""
    try:
        await asyncio.wait_for(broker.shutdown(), 5)
    except TimeoutError:
        pass


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
async def app(tmp_path):
    config = Config(tmp_path).load()
    config.data["mqtt"]["enabled"] = False
    service = Ocean2MQTT(config)
    dongle = FakeDongle()
    dongle.attach(service.gateway)
    service.gateway.connect = lambda: service.gateway.connect_transport(dongle)
    service.dongle = dongle
    events: list = []
    service.subscribe(lambda topic, payload, retain: events.append((topic, payload)))
    service.events = events
    await service.start()
    yield service
    await service.stop()


async def _pair(app: Ocean2MQTT, product: str, rorg: int, frame: str, sender: int) -> dict:
    await app.request("pairing/start", {"product": product, "timeout": 10})
    await asyncio.sleep(0.05)
    app.dongle.inject(rorg, bytes.fromhex(frame), sender)
    for _ in range(50):
        await asyncio.sleep(0.02)
        done = [p for t, p in app.events if t == "bridge/event"
                and p["data"].get("status") == "success"]
        if done:
            return done[-1]["data"]
    raise AssertionError("appairage non abouti")


def _4bs_teach(func: int, type_: int, manu: int = 0x046) -> str:
    db3 = (func << 2) | (type_ >> 5)
    db2 = ((type_ & 0x1F) << 3) | (manu >> 8)
    return bytes([db3, db2, manu & 0xFF, 0x80]).hex()


async def test_pair_rename_command_remove(app: Ocean2MQTT, tmp_path) -> None:
    data = await _pair(app, "nodon/sin-2-fp-01", 0xD4, "A0 01 46 00 0C 01 D2", FP)
    assert data["id"] == "051E575A" and data["product"]["model"] == "SIN-2-FP-01"
    assert (tmp_path / "devices.json").is_file()
    stored = json.loads((tmp_path / "devices.json").read_text())["devices"][0]
    assert stored["sender_offset"] == 1 and stored["product"] == "nodon/sin-2-fp-01"
    # Renommage : nouveau topic, l'ancien est vidé
    old_topic = data["topic"]
    renamed = await app.request("device/rename", {"id": FP and "051E575A",
                                                  "name": "Radiateur salon", "room": "Salon"})
    assert renamed["topic"] == "radiateur_salon" and renamed["room"] == "Salon"
    assert (old_topic, "") in app.events
    # Commande : mode Éco -> trame VLD envoyée au module
    before = len(app.dongle.sent)
    await app.request("device/set", {"id": "radiateur_salon", "payload": {"mode": "eco"}})
    sent = app.dongle.sent[before:]
    assert sent and sent[-1].rorg == 0xD2 and sent[-1].destination == FP
    assert app.retained["radiateur_salon"]["mode"] == "eco"
    # Réception d'une mesure de puissance
    app.dongle.inject(0xD2, bytes.fromhex("07 60 00 00 04 D2"), FP)
    assert app.retained["radiateur_salon"]["power"] == 1234
    # Commande invalide
    with pytest.raises(RequestError):
        await app.request("device/set", {"id": "radiateur_salon", "payload": {"mode": "x"}})
    # Suppression
    await app.request("device/remove", {"id": "radiateur_salon"})
    assert app.devices == {} and "radiateur_salon" not in app.retained


async def test_sensor_state_and_restart(app: Ocean2MQTT, tmp_path) -> None:
    await _pair(app, "nodon/stph-2", 0xA5, _4bs_teach(0x04, 0x01), STPH)
    app.dongle.inject(0xA5, bytes.fromhex("00 96 7D 0A"), STPH)
    topic = app.topic_name("0181A2B3")
    assert app.retained[topic]["temperature"] == 20.0
    assert app.retained[topic]["humidity"] == 60.0
    with pytest.raises(RequestError):  # un capteur ne se commande pas
        await app.request("device/set", {"id": topic, "payload": {"state": "ON"}})
    # Redémarrage : le produit est rechargé depuis devices.json
    other = Ocean2MQTT(Config(tmp_path).load())
    assert "0181A2B3" in other.store.devices
    # … avec ses dernières valeurs (mise à jour, redémarrage de l'add-on)
    app.save_states()
    other = Ocean2MQTT(Config(tmp_path).load())
    dongle = FakeDongle()
    dongle.attach(other.gateway)
    other.gateway.connect = lambda: other.gateway.connect_transport(dongle)
    await other.start()
    try:
        state = other.retained[topic]
        assert state["temperature"] == 20.0 and state["humidity"] == 60.0
        assert state["last_seen"] == app.last_seen["0181A2B3"]
        assert other.devices["0181A2B3"].available
    finally:
        await other.stop()


async def test_valve_pairing_and_setpoint(app: Ocean2MQTT) -> None:
    data = await _pair(app, "micropelt/micitrv004", 0xA5, _4bs_teach(0x20, 0x01, 0x049), VALVE)
    # Réponse au teach-in 4BS bidirectionnel
    reply = next(t for t in reversed(app.dongle.sent) if t.destination == VALVE)
    assert reply.payload[3] == 0xF0 and reply.sender == BASE_ID + 1
    await app.request("device/set", {"id": data["id"], "payload": {"setpoint": 21}})
    # Réveil de la vanne : elle reçoit la consigne en réponse
    app.dongle.inject(0xA5, bytes.fromhex("28 00 80 08"), VALVE)
    await asyncio.sleep(0.05)
    answer = app.dongle.sent[-1]
    assert answer.destination == VALVE and answer.payload == bytes([134, 0, 0x04, 0x08])
    state = app.retained[data["topic"]]
    assert state["valve_position"] == 40 and state["setpoint"] == 21


async def test_library_and_errors(app: Ocean2MQTT) -> None:
    products = await app.request("library", {"search": "fil pilote"})
    assert [p["model"] for p in products] == ["SIN-2-FP-01", "UBICH009"]
    assert products[0]["image"] == "produits/nodon/sin-2-fp-01.png"
    assert any(e["key"] == "mode" and e["access"] == "rw" for e in products[0]["exposes"])
    with pytest.raises(RequestError):
        await app.request("pairing/start", {"product": "acme/inconnu"})
    with pytest.raises(RequestError):
        await app.request("nimporte/quoi")
    info = await app.request("info")
    assert info["gateway"]["connected"] and info["gateway"]["base_id"] == f"{BASE_ID:08X}"


async def test_websocket(app: Ocean2MQTT) -> None:
    from aiohttp import ClientSession

    from ocean2mqtt.web import WebServer

    port = _free_port()
    app.config.data["frontend"].update({"host": "127.0.0.1", "port": port})
    web = WebServer(app)
    await web.start()
    try:
        async with ClientSession() as session:
            async with session.get(f"http://127.0.0.1:{port}/") as resp:
                assert resp.status == 200
            async with session.get(
                f"http://127.0.0.1:{port}/produits/nodon/sin-2-fp-01.png"
            ) as resp:
                assert resp.status == 200 and resp.content_type == "image/png"
            async with session.get(f"http://127.0.0.1:{port}/produits/../app.py") as resp:
                assert resp.status == 404
            async with session.ws_connect(f"http://127.0.0.1:{port}/api") as ws:
                first = json.loads((await ws.receive()).data)
                assert first["topic"].startswith("bridge/")
                await ws.send_str(json.dumps({"topic": "bridge/request/library",
                                              "payload": {"search": "SIN-2-FP", "transaction": 7}}))
                while True:
                    msg = json.loads((await ws.receive(timeout=2)).data)
                    if msg["topic"] == "bridge/response/library":
                        break
                assert msg["payload"]["status"] == "ok" and msg["payload"]["transaction"] == 7
    finally:
        await web.stop()


async def test_mqtt_bridge_end_to_end(app: Ocean2MQTT) -> None:
    amqtt_broker = pytest.importorskip("amqtt.broker")
    import paho.mqtt.client as mqtt

    from ocean2mqtt.mqtt import MqttBridge

    port = _free_port()
    broker = amqtt_broker.Broker({
        "listeners": {"default": {"type": "tcp", "bind": f"127.0.0.1:{port}"}},
        "plugins": {"amqtt.plugins.authentication.AnonymousAuthPlugin": {"allow_anonymous": True}},
    })
    await broker.start()
    await _pair(app, "nodon/sin-2-fp-01", 0xD4, "A0 01 46 00 0C 01 D2", FP)
    app.config.data["mqtt"].update({"enabled": True, "host": "127.0.0.1", "port": port})
    bridge = MqttBridge(app)
    received: dict[str, str] = {}
    loop = asyncio.get_running_loop()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="test")
    client.on_message = lambda c, u, m: received.__setitem__(m.topic, m.payload.decode())
    try:
        await bridge.start()
        for _ in range(100):
            if bridge.connected:
                break
            await asyncio.sleep(0.05)
        assert bridge.connected
        await loop.run_in_executor(None, client.connect, "127.0.0.1", port)
        client.subscribe([("ocean2mqtt/#", 0), ("homeassistant/#", 0)])
        client.loop_start()
        await asyncio.sleep(0.5)
        topic = app.topic_name("051E575A")
        assert received["ocean2mqtt/bridge/state"] == "online"
        assert json.loads(received["ocean2mqtt/bridge/info"])["gateway"]["connected"]
        selects = [t for t in received if t.startswith("homeassistant/select/")]
        assert selects and "Mode fil pilote" in received[selects[0]]
        # Commande MQTT -> trame radio
        before = len(app.dongle.sent)
        client.publish(f"ocean2mqtt/{topic}/set", '{"mode": "comfort"}')
        client.publish("ocean2mqtt/bridge/request/devices", '{"transaction": 1}')
        for _ in range(60):
            await asyncio.sleep(0.05)
            if len(app.dongle.sent) > before and "ocean2mqtt/bridge/response/devices" in received:
                break
        assert app.dongle.sent[-1].destination == FP
        response = json.loads(received["ocean2mqtt/bridge/response/devices"])
        assert response["status"] == "ok" and response["transaction"] == 1
        assert response["data"][0]["id"] == "051E575A"
    finally:
        client.disconnect()
        await asyncio.get_running_loop().run_in_executor(None, client.loop_stop)
        await asyncio.wait_for(bridge.stop(), 10)
        await _stop_broker(broker)


def test_moved_sheet_ids_are_migrated(tmp_path) -> None:
    (tmp_path / "devices.json").write_text(json.dumps({"version": 1, "meta": {}, "devices": [
        {"id": "0181A2B3", "product": "ubiwizz/serfah60", "name": "Luminosité"}]}))
    app = Ocean2MQTT(Config(tmp_path).load())
    assert app.store.devices["0181A2B3"]["product"] == "eltako/fah60"
    saved = json.loads((tmp_path / "devices.json").read_text())
    assert saved["devices"][0]["product"] == "eltako/fah60"
