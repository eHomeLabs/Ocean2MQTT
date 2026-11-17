"""Le cœur fonctionne sans Home Assistant : clé simulée, appairage, réception d'état."""

import asyncio

from fake_dongle import BASE_ID, FakeDongle

from ocean2mqtt.core.device import Device
from ocean2mqtt.core.gateway import Gateway
from ocean2mqtt.core.pairing import wait_for_teach_in
from ocean2mqtt.library import load_library

FP = 0x051E575A


async def _gateway() -> tuple[Gateway, FakeDongle]:
    dongle = FakeDongle()
    gateway = Gateway("/dev/null")
    dongle.attach(gateway)
    info = await gateway.connect_transport(dongle)
    assert info.base_id == BASE_ID
    return gateway, dongle


async def test_pairing_and_state_without_home_assistant() -> None:
    gateway, dongle = await _gateway()
    product = load_library().products["nodon/sin-2-fp-01"]

    pairing = asyncio.create_task(
        wait_for_teach_in(gateway, product, sender_offset=1, timeout=2, exclude=set())
    )
    await asyncio.sleep(0)
    # Demande UTE bidirectionnelle du module fil pilote (D2-01-0C, fabricant NodOn)
    dongle.inject(0xD4, bytes.fromhex("A0 01 46 00 0C 01 D2"), FP)
    result = await pairing
    assert result is not None and result.device_id == FP and result.eep == "D2-01-0C"
    # La passerelle a répondu (UTE, émetteur Base ID + 1, destinataire = le module)
    reply = dongle.sent[-1]
    assert reply.rorg == 0xD4 and reply.sender == BASE_ID + 1 and reply.destination == FP

    device = Device(gateway, product, FP, 1, "test", "Radiateur salon")
    changes: list[set[str]] = []
    device.add_listener(changes.append)
    device.start()
    dongle.inject(0xD2, bytes.fromhex("0A 01"), FP)  # fil pilote : mode Éco
    assert device.state["pilot_wire_mode"] == 1
    assert changes
    device.stop()
    gateway.close()
