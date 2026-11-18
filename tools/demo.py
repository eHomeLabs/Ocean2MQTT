"""Démo sans matériel : clé USB300 simulée, quelques produits qui émettent.

Usage : python tools/demo.py [--port 8080] [--data /tmp/ocean2mqtt-demo]
Puis ouvrez http://localhost:8080. Le MQTT est désactivé (pas de broker nécessaire).
Pour essayer l'appairage : choisissez un produit simulé (SIN-2-FP-01, STPH-2…) et
lancez l'appairage, la clé simulée envoie la demande au bout de 3 s.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import random
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from fake_dongle import FakeDongle

from ocean2mqtt.app import Ocean2MQTT
from ocean2mqtt.config import Config
from ocean2mqtt.web import WebServer

# Produits simulés : identifiant, fiche, nom, pièce, demande d'appairage (RORG, trame)
DEMO = [
    (0x051E575A, "nodon/sin-2-fp-01", "Radiateur salon", "Salon", (0xD4, "A0 01 46 00 0C 01 D2")),
    (0x0181A2B3, "nodon/stph-2", "Sonde chambre", "Chambre", (0xA5, "10 08 46 80")),
    (0x05A1B2C3, "nodon/sin-2-rs-01", "Volet cuisine", "Cuisine", (0xD4, "A0 01 46 00 00 05 D2")),
    (0x01A3C4D5, "nodon/msp-2", "Lave-linge", "Cuisine", (0xD4, "A0 01 46 00 0E 01 D2")),
    (0x05B2C3D4, "nodon/sin-2-2-01", "Éclairage entrée", "Entrée", (0xD4, "A0 02 46 00 12 01 D2")),
    (0x002C3D4E, "nodon/cws-2-1", "Interrupteur salon", "Salon", (0xF6, "30")),
]


async def main(port: int, data: Path, empty: bool) -> None:
    if data.exists():
        shutil.rmtree(data)
    config = Config(data).load()
    config.data["mqtt"]["enabled"] = False
    config.data["frontend"].update({"port": port, "host": "127.0.0.1"})
    app = Ocean2MQTT(config)
    dongle = FakeDongle()
    dongle.attach(app.gateway)
    app.gateway.connect = lambda: app.gateway.connect_transport(dongle)
    await app.start()
    web = WebServer(app)
    await web.start()

    # Appairage simulé : quand on lance l'appairage d'un produit de la démo, la clé
    # reçoit sa demande 3 s plus tard.
    async def watch_pairing() -> None:
        while True:
            await asyncio.sleep(0.5)
            pairing = app.pairing
            if pairing:
                for dev_id, product, *_rest, teach in DEMO:
                    if product == pairing["product"]:
                        await asyncio.sleep(3)
                        dongle.inject(teach[0], bytes.fromhex(teach[1]), dev_id)
                        await asyncio.sleep(1)

    if not empty:
        for dev_id, product, name, room, teach in DEMO:
            await app.request("pairing/start", {"product": product, "timeout": 10})
            await asyncio.sleep(0.05)
            dongle.inject(teach[0], bytes.fromhex(teach[1]), dev_id)
            await asyncio.sleep(0.1)
            entry = next(e for e in app.store.devices.values() if e["product"] == product)
            await app.request("device/rename", {"id": entry["id"], "name": name, "room": room})
        dongle.inject(0xD2, bytes.fromhex("0A 01"), 0x051E575A)  # fil pilote : Confort
        dongle.inject(0xD2, bytes.fromhex("07 60 00 00 02 62"), 0x051E575A)
        dongle.inject(0xD2, bytes.fromhex("04 1E 00"), 0x05B2C3D4)

    app._task(watch_pairing())

    # Remote Commissioning simulé (la clé de démo ne répond pas aux messages ReMan)
    async def ping(*_args) -> bool:
        await asyncio.sleep(0.3)
        return True

    app.gateway.ping = ping
    for device in app.devices.values():
        if not device.product.recom:
            continue

        def fake(device=device):
            links = [{"index": 0, "id": "FEFC1234", "eep": "F6-02-01", "channel": 0},
                     {"index": 1, "id": "0029ABCD", "eep": "D5-00-01", "channel": 255}]

            async def read_links():
                await asyncio.sleep(0.4)
                device.state["links"], device.state["links_max"] = list(links), 22
                device.notify({"links"})
                return links

            async def unlock():
                await asyncio.sleep(0.4)
                device.recom_code, device.recom_pending = 0x1234ABCD, False
                return "assigned"

            async def add_link(link_id, link_type):
                links.append({"index": len(links), "id": f"{link_id:08X}", "eep": "F6-02-01"})
                return await read_links() and len(links) - 1

            async def delete_link(index):
                links[:] = [x for x in links if x["index"] != index]
                await read_links()

            device.read_links, device.unlock_recom = read_links, unlock
            device.add_link, device.delete_link = add_link, delete_link

        fake()

    # Émetteurs du voisinage pas encore appairés (suggestion automatique)
    async def neighbours() -> None:
        await asyncio.sleep(2)
        dongle.inject(0xD5, bytes([0x00]), 0x0193E1F2, dbm=72)  # contact : teach-in 1BS
        dongle.inject(0xA5, bytes.fromhex("24 20 46 80"), 0x0195C0FE, dbm=66)  # A5-09-04
        while True:
            await asyncio.sleep(20)
            dongle.inject(0xF6, bytes([0x10]), 0xFEF0A1B2, dbm=80)

    if not empty:
        app._task(neighbours())

    async def life() -> None:
        while True:
            hum = random.randint(130, 150)
            temp = random.randint(118, 132)
            dongle.inject(0xA5, bytes([0, hum, temp, 0x0A]), 0x0181A2B3, dbm=random.randint(55, 75))
            dongle.inject(0xD2, bytes.fromhex("07 60 00 00") + random.randint(1700, 1900).to_bytes(2,
                          "big"), 0x01A3C4D5)
            await asyncio.sleep(5)

    if not empty:
        app._task(life())
    print(f"Démo Ocean2MQTT : http://127.0.0.1:{port}  (Ctrl+C pour arrêter)")
    try:
        await asyncio.Event().wait()
    finally:
        await web.stop()
        await app.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--data", type=Path, default=Path("/tmp/ocean2mqtt-demo"))
    parser.add_argument("--empty", action="store_true", help="démarrer sans produit appairé")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s : %(message)s")
    asyncio.run(main(args.port, args.data, args.empty))
