"""Compare a real released installation before and after an upgrade."""

import asyncio
import json
import sys
from pathlib import Path

from fake_dongle import FakeDongle
from test_app import STPH, _4bs_teach, _pair

from ocean2mqtt import __version__
from ocean2mqtt.app import Ocean2MQTT
from ocean2mqtt.config import Config
from ocean2mqtt.mqtt import discovery_configs

DEVICE = "0181A2B3"


async def check(directory: Path, phase: str) -> None:
    assert phase != "before" or __version__ == "0.2.0b27"
    config = Config(directory).load()
    config.data["mqtt"]["enabled"] = False
    service = Ocean2MQTT(config)
    dongle = FakeDongle()
    dongle.attach(service.gateway)
    service.gateway.connect = lambda: service.gateway.connect_transport(dongle)
    service.dongle = dongle
    service.events = []
    service.subscribe(lambda topic, payload, retain: service.events.append((topic, payload)))
    await service.start()
    try:
        if phase == "before":
            await _pair(service, "nodon/stph-2", 0xA5, _4bs_teach(0x04, 0x01), STPH)
            await service.request(
                "device/rename", {"id": DEVICE, "name": "Sonde salon", "room": "Salon"}
            )
            dongle.inject(0xA5, bytes.fromhex("00 96 7D 0A"), STPH)
            service.save_states()

        device = service.devices[DEVICE]
        topic = service.topic_name(DEVICE)
        state = service.retained[topic]
        discoveries = discovery_configs(service, device, "ocean2mqtt", "homeassistant")
        assert topic == "sonde_salon"
        assert state["temperature"] == 20.0 and state["humidity"] == 60.0
        assert discoveries
        snapshot = {
            "devices": sorted(service.devices),
            "topic": topic,
            "discovery": {
                key: {field: cfg[field] for field in ("unique_id", "state_topic")}
                for key, cfg in discoveries.items()
            },
        }
        snapshot_file = directory / "upgrade-expected.json"
        if phase == "before":
            snapshot_file.write_text(json.dumps(snapshot), encoding="utf-8")
        else:
            assert snapshot == json.loads(snapshot_file.read_text(encoding="utf-8"))
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(check(Path(sys.argv[1]), sys.argv[2]))
