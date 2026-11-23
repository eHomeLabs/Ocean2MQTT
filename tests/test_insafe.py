"""D2-14-30 vectors from EEP 2.6.8 and Philippe's issue #24."""

import pytest

from ocean2mqtt.core.eep import decode_d21430, find_decoder
from ocean2mqtt.core.esp3 import RadioTelegram


def telegram(payload):
    return RadioTelegram(rorg=0xD2, payload=payload, sender=0x81004CCD)


def vector(**overrides):
    fields = [("smoke", 1, 0), ("fault", 1, 0), ("maintenance", 1, 0),
              ("humidity_range", 1, 0), ("temperature_range", 1, 0),
              ("weeks", 8, 0), ("energy", 2, 0), ("lifetime", 8, 120),
              ("temperature", 8, 100), ("humidity", 8, 100),
              ("comfort", 2, 0), ("air", 3, 0), ("reserved", 4, 0)]
    bits = "".join(format(overrides.get(key, default), f"0{size}b")
                   for key, size, default in fields)
    return telegram(int(bits, 2).to_bytes(6, "big"))


def test_reported_frame():
    assert find_decoder("D2-14-30") is decode_d21430
    assert decode_d21430(telegram(bytes.fromhex("07 F8 7A C9 39 20"))) == {
        "smoke": False, "sensor_fault": False, "maintenance_required": False,
        "humidity_out_of_range": False, "temperature_out_of_range": False,
        "weeks_since_maintenance": None, "battery_status": "high", "battery_low": False,
        "remaining_lifetime": 61, "temperature": 20.0, "humidity": 78.0,
        "hygrothermal_comfort": "bad", "air_quality": "high_humidity",
    }


@pytest.mark.parametrize("energy,status,low", [
    (0, "high", False), (1, "medium", False), (2, "low", True), (3, "critical", True),
])
def test_energy_levels(energy, status, low):
    state = decode_d21430(vector(energy=energy))
    assert state["battery_status"] == status
    assert state["battery_low"] is low
    assert "battery" not in state


def test_limits_errors_and_independent_smoke_alarm():
    state = decode_d21430(vector(temperature=250, humidity=200, weeks=250, lifetime=120))
    assert (state["temperature"], state["humidity"]) == (50, 100)
    state = decode_d21430(vector(smoke=1, fault=1, maintenance=1, humidity_range=1,
                                temperature_range=1, temperature=251, humidity=201,
                                weeks=251, lifetime=121, comfort=3, air=7))
    assert state["smoke"] is True
    assert all(state[k] is True for k in (
        "sensor_fault", "maintenance_required", "humidity_out_of_range", "temperature_out_of_range"))
    assert all(state[k] is None for k in (
        "temperature", "humidity", "weeks_since_maintenance", "remaining_lifetime",
        "hygrothermal_comfort", "air_quality"))
    for raw in (254, 255):
        state = decode_d21430(vector(temperature=raw, humidity=raw, weeks=raw, lifetime=raw))
        assert all(state[k] is None for k in (
            "temperature", "humidity", "weeks_since_maintenance", "remaining_lifetime"))
    for length in (0, 5, 7, 9):
        assert decode_d21430(telegram(bytes(length))) is None
    assert decode_d21430(RadioTelegram(rorg=0xA5, payload=bytes(6), sender=1)) is None
