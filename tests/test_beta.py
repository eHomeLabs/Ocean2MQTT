"""Bêta : réglages, mode générique, émetteurs inconnus, journal radio, Remote Commissioning."""

from __future__ import annotations

import asyncio
import json

import pytest
from test_app import _4bs_teach, _pair, app  # noqa: F401 (fixture)

from ocean2mqtt.app import Ocean2MQTT, RequestError
from ocean2mqtt.mqtt import discovery_configs

RELAY2 = 0x05112233
FP = 0x051E575A
STPH = 0x0181A2B3
UNKNOWN = 0x0199AABB


async def test_actuator_settings(app: Ocean2MQTT, tmp_path) -> None:  # noqa: F811
    data = await _pair(app, "nodon/sin-2-2-01", 0xD4, "A0 02 46 00 12 01 D2", RELAY2)
    keys = [s["key"] for s in data["settings"]]
    assert keys[:2] == ["led", "local_control"]
    assert {"power_on_state", "switch_type", "auto_off_l1", "auto_off_l2", "delay_off_l2",
            "repeater"} <= set(keys)
    # Réglage par MQTT /set, mélangé à une commande
    before = len(app.dongle.sent)
    await app.request("device/set", {"id": data["id"], "payload": {"led": "OFF",
                                                                   "state_l1": "ON"}})
    sent = app.dongle.sent[before:]
    assert len(sent) == 2 and all(t.rorg == 0xD2 and t.destination == RELAY2 for t in sent)
    assert sent[0].payload[0] & 0x0F == 0x02  # CMD 0x2 : réglages locaux
    state = app.retained[data["topic"]]
    assert state["led"] == "OFF" and state["state_l1"] == "ON"
    stored = json.loads((tmp_path / "devices.json").read_text())["devices"][0]
    assert stored["settings"]["led"] is False
    # Temporisation du canal 2 (CMD 0xB)
    result = await app.request("device/settings/set", {"id": data["id"], "key": "auto_off_l2",
                                                       "value": 30})
    assert next(s for s in result if s["key"] == "auto_off_l2")["value"] == 30
    frame = app.dongle.sent[-1].payload
    assert frame[0] & 0x0F == 0x0B and frame[1] & 0x1F == 1
    # Valeurs refusées
    with pytest.raises(RequestError):
        await app.request("device/settings/set", {"id": data["id"], "key": "power_on_state",
                                                  "value": "maybe"})
    with pytest.raises(RequestError):
        await app.request("device/settings/set", {"id": data["id"], "key": "auto_off_l1",
                                                  "value": 9999})
    # Entités « configuration » de Home Assistant
    configs = discovery_configs(app, app.devices[data["id"]], "ocean2mqtt", "homeassistant")
    led = next(c for t, c in configs.items() if t.endswith(f"{data['id']}_led/config"))
    assert led["entity_category"] == "config" and "/switch/" in next(
        t for t in configs if t.endswith(f"{data['id']}_led/config"))
    assert any("/number/" in t and t.endswith("_auto_off_l2/config") for t in configs)


async def test_sensor_local_settings(app: Ocean2MQTT) -> None:  # noqa: F811
    data = await _pair(app, "nodon/stph-2", 0xA5, _4bs_teach(0x04, 0x01), STPH)
    await app.request("device/set", {"id": data["id"], "payload": {"temperature_offset": -1.5}})
    app.dongle.inject(0xA5, bytes.fromhex("00 96 7D 0A"), STPH)
    state = app.retained[data["topic"]]
    assert state["temperature"] == 18.5 and state["temperature_offset"] == -1.5
    with pytest.raises(RequestError):  # une commande reste refusée sur un capteur
        await app.request("device/set", {"id": data["id"], "payload": {"state": "ON"}})


async def test_generic_pairing(app: Ocean2MQTT) -> None:  # noqa: F811
    generics = await app.request("library/generic")
    assert {"generique/f6-02-01", "generique/d2-01-00"} <= {p["id"] for p in generics}
    # Actionneur générique : le type exact vient de la demande UTE (2 canaux)
    data = await _pair(app, "generique/d2-01-00", 0xD4, "A0 02 46 00 12 01 D2", RELAY2)
    assert data["product"]["id"] == "generique/d2-01-12" and data["product"]["generic"]
    assert [e["key"] for e in data["product"]["exposes"]][:2] == ["state_l1", "state_l2"]
    reply = next(t for t in reversed(app.dongle.sent) if t.destination == RELAY2)
    assert reply.rorg == 0xD4
    # Rechargé après redémarrage
    other = Ocean2MQTT(app.config)
    other._add_device(other.store.devices[data["id"]])
    assert other.devices[data["id"]].product.channels == 2


async def test_unknown_suggestion_and_one_click(app: Ocean2MQTT) -> None:  # noqa: F811
    # Teach-in 4BS d'un capteur NodOn hors appairage : suggestion automatique
    app.dongle.inject(0xA5, bytes.fromhex(_4bs_teach(0x04, 0x01)), UNKNOWN)
    unknown = await app.request("unknown")
    assert unknown[0]["id"] == "0199AABB" and unknown[0]["eep"] == "A5-04-01"
    assert unknown[0]["suggestions"] == ["nodon/stph-2"]
    assert any(t == "bridge/event" and p["type"] == "suggestion" for t, p in app.events)
    # Un actionneur ne s'ajoute pas en un clic
    with pytest.raises(RequestError):
        await app.request("device/add", {"id": "0199AABB", "product": "nodon/sin-2-fp-01"})
    added = await app.request("device/add", {"id": "0199AABB", "product": "nodon/stph-2",
                                             "name": "Chambre"})
    assert added["topic"] == "chambre" and "0199AABB" not in app.unknown
    app.dongle.inject(0xA5, bytes.fromhex("00 96 7D 0A"), UNKNOWN)
    assert app.retained["chambre"]["temperature"] == 20.0
    with pytest.raises(RequestError):
        await app.request("device/add", {"id": "0199AABB", "product": "nodon/stph-2"})


async def test_telegram_log(app: Ocean2MQTT) -> None:  # noqa: F811
    app.dongle.inject(0xF6, bytes([0x30]), UNKNOWN)
    live = [p for t, p in app.events if t == "bridge/telegrams"]
    assert live[-1]["sender"] == "0199AABB" and live[-1]["rorg"] == "F6"
    history = await app.request("telegrams")
    assert history[-1]["data"] == "30"


async def test_recom_api(app: Ocean2MQTT, monkeypatch) -> None:  # noqa: F811
    data = await _pair(app, "nodon/sin-2-fp-01", 0xD4, "A0 01 46 00 0C 01 D2", FP)
    assert data["recom"]["secured"] is False and "contact" in data["recom"]["link_types"]
    device = app.devices[data["id"]]

    async def fake_links():
        device.state["links"] = [{"index": 0, "id": "FEDCBA98", "eep": "F6-02-01"}]
        device.state["links_max"] = 22
        return device.state["links"]

    monkeypatch.setattr(device, "read_links", fake_links)
    status = await app.request("device/recom/links", {"id": data["id"]})
    assert status["links"][0]["id"] == "FEDCBA98" and status["links_max"] == 22

    async def no_answer(*_args):
        return False

    monkeypatch.setattr(app.gateway, "ping", no_answer)
    with pytest.raises(RequestError, match="Ping"):
        await app.request("device/recom/ping", {"id": data["id"]})
    with pytest.raises(RequestError, match="Code invalide"):
        await app.request("device/recom/code", {"id": data["id"], "code": "12"})
    log = await app.request("recom/log")
    assert [(e["action"], e["ok"]) for e in log] == [("links", True), ("ping", False)]
    # Produit sans ReCom
    stph = await _pair(app, "nodon/stph-2", 0xA5, _4bs_teach(0x04, 0x01), STPH)
    with pytest.raises(RequestError):
        await app.request("device/recom/status", {"id": stph["id"]})
    await asyncio.sleep(0)


MSP2 = 0x05AB0E01


async def test_metering_reporting_and_poll(app: Ocean2MQTT, monkeypatch) -> None:  # noqa: F811
    """Après l'appairage : rapport automatique réglé (CMD 0x5) puis puissance/énergie lues."""
    import ocean2mqtt.app as app_module

    data = await _pair(app, "nodon/msp-2", 0xD4, "A0 01 46 00 0E 01 D2", MSP2)
    await asyncio.sleep(2.5)
    to_plug = [t.payload for t in app.dongle.sent if t.destination == MSP2 and t.rorg == 0xD2]
    cmds = [p[0] & 0x0F for p in to_plug]
    assert cmds.count(0x05) == 2  # puissance + énergie
    assert 0x06 in cmds  # interrogation des mesures
    # Réponses du produit : 150 W puis 1,25 kWh
    app.dongle.inject(0xD2, bytes.fromhex("07 60 00 00 00 96"), MSP2)
    app.dongle.inject(0xD2, bytes.fromhex("07 20 00 00 04 E2"), MSP2)  # 1250 Wh
    state = app.retained[data["topic"]]
    assert state["power"] == 150
    assert state["energy"] == pytest.approx(1.25)
    # Interrogation périodique
    monkeypatch.setattr(app_module, "POLL_INTERVAL", 0.05)
    before = len(app.dongle.sent)
    task = asyncio.get_running_loop().create_task(app._poll_loop())
    await asyncio.sleep(1.2)
    task.cancel()
    assert any(t.destination == MSP2 for t in app.dongle.sent[before:])
