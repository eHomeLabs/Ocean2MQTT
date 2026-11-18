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


# -- Migration NodOcean, sauvegarde, changement de clé --------------------------


def _ha_config(tmp_path, base_id: str, disabled: bool = False):
    """Configuration Home Assistant minimale avec NodOcean for HA (3 produits)."""
    storage = tmp_path / "ha" / ".storage"
    storage.mkdir(parents=True)
    entries = {"entries": [
        {"entry_id": "abc", "domain": "mqtt", "data": {}},
        {"entry_id": "e1", "domain": "nodon_enocean", "unique_id": base_id,
         "title": f"Clé EnOcean {base_id}", "data": {"device": "/dev/ttyUSB0"},
         "disabled_by": "user" if disabled else None,
         "subentries": [
             {"subentry_type": "device", "title": "Radiateur salon",
              "data": {"device_id": "051E575A", "model": "SIN-2-FP-01", "sender_offset": 3}},
             {"subentry_type": "device", "title": "Sonde chambre",
              "data": {"device_id": "0181A2B3", "model": "STPH-2", "sender_offset": None}},
             {"subentry_type": "device", "title": "Prise Ubiwizz",
              "data": {"device_id": "05AA0001", "model": "ASP-2-METERING", "sender_offset": 4}},
             {"subentry_type": "device", "title": "Inconnu",
              "data": {"device_id": "05AA0002", "model": "XYZ-9", "sender_offset": 5}},
         ]},
    ]}
    (storage / "core.config_entries").write_text(json.dumps({"data": entries}))
    (storage / "nodon_enocean.recom_codes.e1").write_text(json.dumps(
        {"data": {"051E575A": "1234ABCD"}}))
    (storage / "core.area_registry").write_text(json.dumps(
        {"data": {"areas": [{"id": "salon", "name": "Salon"}]}}))
    (storage / "core.device_registry").write_text(json.dumps({"data": {"devices": [
        {"identifiers": [["nodon_enocean", "051E575A"]], "area_id": "salon"}]}}))
    return tmp_path / "ha"


async def test_nodocean_import_same_key(app: Ocean2MQTT, tmp_path) -> None:  # noqa: F811
    base = app.info()["gateway"]["base_id"]
    app.config.data["homeassistant"]["config_dir"] = str(_ha_config(tmp_path, base))
    info = app.info()["migration"]["nodocean"][0]
    assert info["devices"] == 4 and info["active"] is True and info["base_id"] == base
    plan = await app.request("migration/preview", {"mode": "same"})
    status = {i["id"]: i["status"] for i in plan["items"]}
    assert status == {"051E575A": "ok", "0181A2B3": "ok", "05AA0001": "ok",
                      "05AA0002": "unknown"}
    assert not plan["key_mismatch"]
    result = await app.request("migration/import", {"mode": "same"})
    assert result == {"imported": 3, "repair": 0, "codes": 0, "skipped": 1,
                      "source": plan["source"]}
    fp = app.store.devices["051E575A"]
    assert fp["sender_offset"] == 3 and fp["recom_code"] == 0x1234ABCD and fp["room"] == "Salon"
    assert app.store.devices["05AA0001"]["product"] == "ubiwizz/ubid1501s"
    assert app.devices["051E575A"].recom_secured
    # Le radiateur répond tout de suite : commande envoyée avec Base ID + 3
    await app.request("device/set", {"id": "051E575A", "payload": {"mode": "eco"}})
    sent = app.dongle.sent[-1]
    assert sent.destination == 0x051E575A and sent.sender == app.gateway.sender_id(3)
    # Un second import ne duplique rien
    again = await app.request("migration/preview", {"mode": "same"})
    assert {i["status"] for i in again["items"]} == {"exists", "unknown"}


async def test_nodocean_import_new_key(app: Ocean2MQTT, tmp_path) -> None:  # noqa: F811
    app.config.data["homeassistant"]["config_dir"] = str(_ha_config(tmp_path, "FF000080"))
    plan = await app.request("migration/preview", {"mode": "same"})
    assert plan["key_mismatch"]  # la clé branchée n'est pas celle de NodOcean
    assert {i["id"]: i["status"] for i in plan["items"]}["051E575A"] == "repair"
    result = await app.request("migration/import", {"mode": "new"})
    assert result["imported"] == 3 and result["repair"] == 2
    devices = {d["id"]: d for d in await app.request("devices")}
    assert devices["051E575A"]["needs_pairing"] and not devices["0181A2B3"]["needs_pairing"]
    # Réappairage du radiateur : nom, pièce et code ReCom gardés, drapeau effacé
    data = await _pair(app, "nodon/sin-2-fp-01", 0xD4, "A0 01 46 00 0C 01 D2", 0x051E575A)
    assert data["name"] == "Radiateur salon" and not data["needs_pairing"]
    assert app.store.devices["051E575A"]["recom_code"] == 0x1234ABCD


async def test_export_file_and_backup_restore(app: Ocean2MQTT, tmp_path) -> None:  # noqa: F811
    base = app.info()["gateway"]["base_id"]
    export = {"format": "ocean2mqtt-import", "version": 1, "source": "NodOcean for HA 0.8.6",
              "gateway": {"base_id": base, "port": "/dev/ttyUSB0"},
              "devices": [{"id": "051E575A", "model": "SIN-2-FP-01", "name": "Radiateur",
                           "area": "Salon", "sender_offset": 3, "recom_code": "1234ABCD"}]}
    plan = await app.request("migration/preview", {"file": export, "mode": "same"})
    assert plan["items"][0]["status"] == "ok"
    await app.request("migration/import", {"file": json.dumps(export), "mode": "same"})
    backup = await app.request("backup/create")
    assert backup["format"] == "ocean2mqtt-backup" and backup["devices"][0]["recom_code"] == \
        "1234ABCD"
    # Restauration sur une installation vierge
    other = Ocean2MQTT(app.config)
    other.store.devices.clear()
    other.gateway = app.gateway
    other.gateway_ok = True
    result = await other.request("migration/import", {"file": backup, "mode": "same"})
    assert result["imported"] == 1 and other.store.devices["051E575A"]["recom_code"] == \
        0x1234ABCD
    with pytest.raises(RequestError, match="Format inconnu"):
        await app.request("migration/preview", {"file": {"hello": 1}})


async def test_gateway_change_flags_actuators(app: Ocean2MQTT) -> None:  # noqa: F811
    await _pair(app, "nodon/sin-2-fp-01", 0xD4, "A0 01 46 00 0C 01 D2", 0x051E575A)
    await _pair(app, "nodon/stph-2", 0xA5, _4bs_teach(0x04, 0x01), STPH)
    assert app.store.meta["base_id"] == app.info()["gateway"]["base_id"]
    app.store.meta["base_id"] = "FF000080"  # appairés avec une autre clé
    app._check_base_id()
    devices = {d["id"]: d for d in await app.request("devices")}
    assert devices["051E575A"]["needs_pairing"] and not devices["0181A2B3"]["needs_pairing"]
    assert app.info()["migration"]["previous_base_id"] == "FF000080"
    assert any(t == "bridge/event" and p["type"] == "gateway_changed" for t, p in app.events)


async def test_import_recovers_recom_code_of_existing(app: Ocean2MQTT, tmp_path) -> None:  # noqa: F811
    """Produit réappairé dans Ocean2MQTT avant la reprise : seul le code ReCom est repris."""
    base = app.info()["gateway"]["base_id"]
    await _pair(app, "nodon/sin-2-fp-01", 0xD4, "A0 01 46 00 0C 01 D2", 0x051E575A)
    entry = app.store.devices["051E575A"]
    entry["recom_code"], entry["recom_pending"] = 0x0BADC0DE, True  # candidat jamais confirmé
    app.devices["051E575A"].recom_code = 0x0BADC0DE
    app.config.data["homeassistant"]["config_dir"] = str(_ha_config(tmp_path, base))
    plan = await app.request("migration/preview", {"mode": "same"})
    assert {i["id"]: i["status"] for i in plan["items"]}["051E575A"] == "code"
    result = await app.request("migration/import", {"mode": "same"})
    assert result["codes"] == 1 and result["imported"] == 2
    assert app.store.devices["051E575A"]["recom_code"] == 0x1234ABCD
    assert not app.store.devices["051E575A"]["recom_pending"]
    assert app.devices["051E575A"].recom_code == 0x1234ABCD
    assert app.store.devices["051E575A"]["name"] != "Radiateur salon"  # nom gardé


async def test_recom_disabled(app: Ocean2MQTT) -> None:  # noqa: F811
    """recom.enabled = false : aucune commande ReMan, pas de réglages ReCom ni d'onglet."""
    rs = await _pair(app, "nodon/sin-2-rs-01", 0xD4, "A0 01 46 00 00 05 D2", 0x05A1B2C3)
    keys = {s["key"] for s in rs["settings"]}
    assert {"rs_switch_type", "calibration"} <= keys and rs["recom"]["session_until"] == 0
    app.config.data["recom"]["enabled"] = False
    app.gateway.reman_enabled = False
    assert app.info()["recom_enabled"] is False
    devices = {d["id"]: d for d in await app.request("devices")}
    rs = devices["05A1B2C3"]
    assert rs["recom"] is None
    assert not {"rs_switch_type", "calibration"} & {s["key"] for s in rs["settings"]}
    assert "travel_time" in {s["key"] for s in rs["settings"]}
    before = len(app.dongle.sent)
    with pytest.raises(RequestError, match="désactivé"):
        await app.request("device/recom/unlock", {"id": "05A1B2C3"})
    with pytest.raises(RequestError):
        await app.request("device/set", {"id": "05A1B2C3", "payload": {"calibration": "classic"}})
    # Garde au plus bas niveau : rien n'est émis, même en appelant la clé directement
    assert not await app.gateway.unlock(0x05A1B2C3, app.gateway.sender_id(1), 0x1234)
    assert len(app.dongle.sent) == before


def test_nodocean_generic_models() -> None:
    """Produits génériques de NodOcean (« EEP-F6-02-01 ») -> mode générique d'Ocean2MQTT."""
    from ocean2mqtt.library import load_library
    from ocean2mqtt.migration import product_id

    assert product_id("EEP-F6-02-01") == "generique/f6-02-01"
    assert product_id("eep-d2-01-12") == "generique/d2-01-12"
    assert product_id("SIN-2-FP-01") == "nodon/sin-2-fp-01"
    library = load_library()
    assert library.get(product_id("EEP-F6-02-01")).eep == "F6-02-01"
    assert library.get(product_id("EEP-D2-01-12")).channels == 2


async def test_change_product_same_eep(app: Ocean2MQTT) -> None:  # noqa: F811
    """Générique F6-02-01 -> NodOn CWS-2-1 sans réappairage ; EEP différent refusé."""
    data = await _pair(app, "generique/f6-02-01", 0xF6, "30", 0xFECDB2CC)
    await app.request("device/rename", {"id": data["id"], "name": "Inter labo", "room": "Labo"})
    compatible = {p["id"] for p in await app.request("device/compatible", {"id": data["id"]})}
    assert {"nodon/cws-2-1", "nodon/crc-2", "nodon/cfs-2"} <= compatible
    assert "nodon/stph-2" not in compatible
    result = await app.request("device/change_product", {"id": data["id"],
                                                         "product": "nodon/cws-2-1"})
    assert result["product"]["id"] == "nodon/cws-2-1"
    assert result["name"] == "Inter labo" and result["room"] == "Labo"
    assert app.store.devices[data["id"]]["product"] == "nodon/cws-2-1"
    app.dongle.inject(0xF6, bytes([0x30]), 0xFECDB2CC)  # toujours reçu
    assert app.devices[data["id"]].product.model == "CWS-2-1"
    # Retour possible vers la fiche générique ; EEP différent refusé
    back = {p["id"] for p in await app.request("device/compatible", {"id": data["id"]})}
    assert "generique/f6-02-01" in back
    with pytest.raises(RequestError, match="incompatible"):
        await app.request("device/change_product", {"id": data["id"],
                                                    "product": "nodon/stph-2"})


async def test_import_choose_product_for_generic(app: Ocean2MQTT, tmp_path) -> None:  # noqa: F811
    base = app.info()["gateway"]["base_id"]
    export = {"format": "ocean2mqtt-import", "gateway": {"base_id": base},
              "devices": [{"id": "FECDB2CC", "model": "EEP-F6-02-01", "name": "Inter",
                           "sender_offset": None}]}
    plan = await app.request("migration/preview", {"file": export, "mode": "same"})
    item = plan["items"][0]
    assert item["product"] == "generique/f6-02-01" and "nodon/cws-2-1" in item["alternatives"]
    # Choix non autorisé ignoré, choix valide appliqué
    await app.request("migration/import", {"file": export, "mode": "same",
                                           "choices": {"FECDB2CC": "nodon/cws-2-1"}})
    assert app.store.devices["FECDB2CC"]["product"] == "nodon/cws-2-1"


async def test_recom_code_modes(app: Ocean2MQTT, monkeypatch) -> None:  # noqa: F811
    """b8 : code auto (dérivé du secret de l'installation), saisi, aucun ; détection."""
    from ocean2mqtt.core import recom

    secret = app.store.meta["recom_secret"]
    assert len(secret) == 32
    auto = recom.derive_code(secret, FP)
    assert auto == recom.derive_code(secret, FP) != recom.derive_code(secret, RELAY2)
    assert recom.derive_code(recom.new_secret(), FP) != auto

    data = await _pair(app, "nodon/sin-2-fp-01", 0xD4, "A0 01 46 00 0C 01 D2", FP)
    device = app.devices[data["id"]]
    sent: list[tuple[str, int]] = []

    async def set_code(_dev, _sender, code):
        sent.append(("set", code))
        return True

    monkeypatch.setattr(app.gateway, "set_code", set_code)
    status = await app.request("device/recom/assign", {"id": data["id"], "mode": "auto"})
    assert status["secured"] and status["mode"] == "auto" and sent == [("set", auto)]
    assert app.store.devices[data["id"]]["recom_mode"] == "auto"
    assert device.recom_code == auto

    # Détection : le code stocké est perdu, on retrouve le code auto
    device.recom_code, device.recom_mode = None, None
    tried: list[int] = []

    async def unlock(_dev, _sender, code):
        tried.append(code)
        return code == auto

    monkeypatch.setattr(app.gateway, "unlock", unlock)
    status = await app.request("device/recom/detect", {"id": data["id"], "code": "11Z0A0B0C0D"})
    assert status["mode"] == "auto" and status["secured"] and tried == [auto]

    # Aucun code accepté
    async def refuse(_dev, _sender, code):
        tried.append(code)
        return False

    async def pong(*_a):
        return True

    monkeypatch.setattr(app.gateway, "unlock", refuse)
    monkeypatch.setattr(app.gateway, "ping", pong)
    with pytest.raises(RequestError, match="Aucun code connu"):
        await app.request("device/recom/detect", {"id": data["id"], "code": "0A0B0C0D"})
    assert tried[-2:] == [auto, 0x0A0B0C0D]  # code stocké = auto, pas de doublon

    # « Aucun » refusé quand le produit a déjà un code
    with pytest.raises(RequestError, match="reset usine"):
        await app.request("device/recom/assign", {"id": data["id"], "mode": "none"})

    # Autre produit : code saisi puis « aucun »
    relay = await _pair(app, "nodon/sin-2-2-01", 0xD4, "A0 02 46 00 12 01 D2", RELAY2)
    with pytest.raises(RequestError, match="Code invalide"):
        await app.request("device/recom/assign", {"id": relay["id"], "mode": "custom",
                                                   "code": "XYZ"})
    status = await app.request("device/recom/assign", {"id": relay["id"], "mode": "none"})
    assert status["mode"] == "none" and not status["has_code"]
    status = await app.request("device/recom/assign", {"id": relay["id"], "mode": "custom",
                                                        "code": "11Z12345678"})
    assert status["mode"] == "custom" and sent[-1] == ("set", 0x12345678)

    # La sauvegarde contient le secret et le mode
    backup = await app.request("backup/create", {})
    assert backup["recom_secret"] == secret
    assert {d["id"]: d["recom_mode"] for d in backup["devices"]}[data["id"]] == "auto"
    await asyncio.sleep(0)
