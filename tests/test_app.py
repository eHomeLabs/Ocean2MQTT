"""Service complet sans matériel : appairage, état, commandes, MQTT, WebSocket."""

from __future__ import annotations

import asyncio
import json
import socket
from types import SimpleNamespace

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
    assert [p["model"] for p in products] == ["600106", "SIN-2-FP-01", "UBICH009"]
    assert next(p for p in products if p["model"] == "SIN-2-FP-01")["image"] == "produits/nodon/sin-2-fp-01.png"
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


async def test_telegram_eep_rx_tx_and_history(app: Ocean2MQTT) -> None:
    # Commands use the gateway as sender, so resolve their destination instead.
    app.devices["050E1FEC"] = SimpleNamespace(title="Plug", eep_code="D2-01-0B")
    records = [
        {"dir": "rx", "sender": "050E1FEC", "destination": "FFFFFFFF"},
        {"dir": "tx", "sender": "FFE7CA02", "destination": "050E1FEC"},
        {"dir": "rx", "sender": "FFE7CA02", "destination": "FFFFFFFF"},
    ]
    try:
        for record in records:
            app._on_record(record)
        live = [payload for topic, payload in app.events if topic == "bridge/telegrams"]
        assert [r["eep"] for r in live] == ["D2-01-0B", "D2-01-0B", None]
        assert [r["name"] for r in live] == ["Plug", "Plug", None]
        app.gateway.history.extend(records)
        assert await app.request("telegrams", {}) == live
        assert all("eep" not in record for record in records)
    finally:
        app.devices.pop("050E1FEC")


async def test_generic_identity_and_decoded_telegram(app: Ocean2MQTT) -> None:
    added = await app.request("device/add", {
        "id": "0199AABB", "product": "generique/a5-04-03", "name": "Sensor",
    })
    before = app.devices["0199AABB"].product
    identity = {"brand": "Ubiwizz", "model": "TH-test", "photo": "https://example.com/photo.png",
                "pairing": "Appuyer sur LRN."}
    result = await app.request("device/identify", {"id": added["id"], **identity})
    assert result["identity"]["model"] == "TH-test"
    assert result["product"]["generic"]
    assert app.devices["0199AABB"].product is before
    other = Ocean2MQTT(app.config)
    other._add_device(other.store.devices[added["id"]])
    assert other.device_dict(other.devices[added["id"]])["identity"]["brand"] == "Ubiwizz"
    for photo in ("javascript:alert(1)", "http://example.com/x", "https://user:secret@example.com"):
        with pytest.raises(RequestError):
            await app.request("device/identify", {"id": added["id"], **identity, "photo": photo})
    record = {"dir": "rx", "sender": added["id"], "destination": "FFFFFFFF", "rorg": "A5",
              "data": "80 02 00 08", "status": "00", "dbm": -65}
    decoded = app._telegram_dict(record)["decoded"]
    assert decoded == {"temperature": 20.0, "humidity": 50.2}
    assert app._telegram_dict({**record, "dir": "tx", "destination": added["id"]})["decoded"] is None
    assert app._telegram_dict({**record, "rorg": "C5"})["decoded"] is None
    assert app._telegram_dict({**record, "data": "invalid"})["decoded"] is None


async def test_ui_entry_points_disable_cache(app: Ocean2MQTT, tmp_path, monkeypatch) -> None:
    from aiohttp import ClientSession

    import ocean2mqtt.web as web_module
    from ocean2mqtt import __version__

    (tmp_path / "index.html").write_text("<html>current build</html>")
    monkeypatch.setattr(web_module, "STATIC", tmp_path)
    port = _free_port()
    app.config.data["frontend"].update({"host": "127.0.0.1", "port": port})
    server = web_module.WebServer(app)
    await server.start()
    try:
        async with ClientSession() as session:
            for path in ("/", "/index.html", "/?ui=next", "/api/version"):
                async with session.get(f"http://127.0.0.1:{port}{path}") as response:
                    assert response.status == 200
                    assert "no-store" in response.headers["Cache-Control"]
                    if path == "/api/version":
                        assert await response.json() == {"version": __version__}
    finally:
        await server.stop()


async def test_insafe_manual_add_and_publish(app: Ocean2MQTT) -> None:
    from ocean2mqtt.core.convert import device_payload
    from ocean2mqtt.core.exposes import exposes

    await app.request("device/add", {
        "id": "81004CCD", "product": "nexelec/insafe-plus", "name": "Insafe",
    })
    app.dongle.inject(0xD2, bytes.fromhex("07 F8 7A C9 39 20"), 0x81004CCD)
    await asyncio.sleep(0.05)
    device = app.devices["81004CCD"]
    payload = device_payload(device)
    assert payload["temperature"] == 20.0
    assert payload["humidity"] == 78.0
    assert payload["smoke"] is False
    assert payload["air_quality"] == "high_humidity"
    assert payload["remaining_lifetime"] == 61
    assert "weeks_since_maintenance" not in payload
    exposed = {e.key for e in exposes(device.product)}
    assert set(payload) - {"rssi", "timeout"} <= exposed
    from ocean2mqtt.mqtt import discovery_configs

    configs = discovery_configs(app, device, "homeassistant", "ocean2mqtt")
    by_key = {topic.rsplit("/", 2)[1]: value for topic, value in configs.items()}
    assert by_key["81004CCD_smoke"]["device_class"] == "smoke"
    assert by_key["81004CCD_sensor_fault"]["device_class"] == "problem"
    assert by_key["81004CCD_battery_status"]["options"] == ["high", "medium", "low", "critical"]
    assert by_key["81004CCD_remaining_lifetime"]["unit_of_measurement"] == "months"


async def test_unknown_senders_exclude_only_gateway_ids(app: Ocean2MQTT) -> None:
    from ocean2mqtt.core.esp3 import RadioTelegram

    info = app.gateway.info
    for sender in (info.base_id, info.base_id + 1, info.base_id + 127, info.chip_id):
        app._on_any_telegram(RadioTelegram(rorg=0xD2, payload=b"\x00", sender=sender))
        assert f"{sender:08X}" not in app.unknown
    for sender in (info.base_id - 1, info.base_id + 128, 0x81004CCD):
        app._on_any_telegram(RadioTelegram(rorg=0xD2, payload=b"\x00", sender=sender, status=0x81))
        assert f"{sender:08X}" in app.unknown


async def test_avidsen_sensor_received_setpoint_is_read_only(app: Ocean2MQTT) -> None:
    from ocean2mqtt.core.convert import apply_command, device_payload
    from ocean2mqtt.core.exposes import exposes
    from ocean2mqtt.mqtt import discovery_configs

    await app.request("device/add", {
        "id": "0199AACC", "product": "avidsen/101012", "name": "Avidsen",
    })
    app.dongle.inject(0xA5, bytes.fromhex("80 7D 7D 08"), 0x0199AACC)
    await asyncio.sleep(0.05)
    device = app.devices["0199AACC"]
    state = device_payload(device)
    assert (state["temperature"], state["humidity"], state["setpoint_raw"]) == (20, 50, 128)
    exposed = {e.key: e for e in exposes(device.product)}
    assert exposed["setpoint_raw"].access == "r"
    assert exposed["setpoint_raw"].unit is None
    assert "battery_low" not in exposed
    assert await apply_command(device, {"setpoint_raw": 100}) == ["setpoint_raw"]
    configs = discovery_configs(app, device, "ocean2mqtt", "homeassistant")
    sp = next(c for topic, c in configs.items() if "0199AACC_setpoint_raw/" in topic)
    assert "command_topic" not in sp
    assert sp["unit_of_measurement"] is None


async def test_avidsen_4bs_teach_in(app: Ocean2MQTT) -> None:
    await _pair(app, "avidsen/101012", 0xA5, _4bs_teach(0x10, 0x12), 0x0199AACD)
    device = app.devices["0199AACD"]
    assert device.product.eep == "A5-10-12"
    assert "temperature" not in device.state
    app.dongle.inject(0xA5, bytes.fromhex("22 96 7D 08"), 0x0199AACD)
    assert device.state["temperature"] == 20.0
    assert device.state["humidity"] == 60.0


@pytest.mark.parametrize("ref,rorg,teach,frame,expected", [
    ("600104", 0xA5, _4bs_teach(0x04, 0x01, 0x06F), "00 96 7D 0A",
     {"temperature": 20.0, "humidity": 60.0}),
    ("600102", 0xD5, "00", "08", {"open": True}),
    ("970221", 0xD5, "00", "09", {"open": False}),
    ("600105", 0xD4, "A0 01 6F 00 08 01 D2", "04 00 64", {"state": "ON"}),
    ("600106", 0xD4, "A0 01 6F 00 0C 01 D2", "0A 02", {"mode": "eco"}),
    ("970292", 0xD4, "A0 02 6F 00 12 01 D2", "04 01 64", {"state_l2": "ON"}),
])
async def test_avidsen_range_pairing_and_state(app, ref, rorg, teach, frame, expected):
    from ocean2mqtt.core.convert import device_payload
    from ocean2mqtt.core.exposes import exposes

    sender = 0x0199AADD
    await _pair(app, f"avidsen/{ref}", rorg, teach, sender)
    device = app.devices["0199AADD"]
    assert device.product.support == "communaute"
    assert not device.product.recom
    assert not any(x.rorg == 0xD1 for x in app.dongle.sent)  # no NodOn MSC queries
    app.dongle.inject(0xD2 if rorg == 0xD4 else rorg, bytes.fromhex(frame), sender)
    state = device_payload(device)
    for key, value in expected.items():
        assert state[key] == value
    if ref in ("600105", "600106"):
        app.dongle.inject(0xD2, bytes.fromhex("07 60 00 00 04 D2"), sender)
        app.dongle.inject(0xD2, bytes.fromhex("07 20 00 00 3C 8C"), sender)
        state = device_payload(device)
        assert state["power"] == 1234.0
        assert state["energy"] == 15.5
        assert {"power", "energy"} <= {x.key for x in exposes(device.product)}
    if ref == "600105":
        await app.request("device/set", {"id": device.id_str, "payload": {"state": "OFF"}})
        assert app.dongle.sent[-1].payload == bytes.fromhex("01 00 00")
    if ref == "600106":
        for mode, code in (("off", 0), ("frost_protection", 3), ("eco", 2),
                           ("comfort", 1), ("comfort_1", 4), ("comfort_2", 5)):
            await app.request("device/set", {"id": device.id_str, "payload": {"mode": mode}})
            assert app.dongle.sent[-1].payload == bytes([0x08, code])
    if ref == "970292":
        await app.request("device/set", {"id": device.id_str, "payload": {"state_l1": "ON"}})
        assert app.dongle.sent[-1].payload == bytes.fromhex("01 00 64")
        await app.request("device/set", {"id": device.id_str, "payload": {"state_l2": "OFF"}})
        assert app.dongle.sent[-1].payload == bytes.fromhex("01 01 00")
        assert not device.product.metering
