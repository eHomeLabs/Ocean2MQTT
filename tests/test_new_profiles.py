"""Profils EEP ajoutés pour Ocean2MQTT (valeurs calculées d'après la spécification EEP)."""

from ocean2mqtt.core import eep
from ocean2mqtt.core.esp3 import RadioTelegram


def t(rorg: int, payload: str) -> RadioTelegram:
    return RadioTelegram(rorg=rorg, payload=bytes.fromhex(payload), sender=0x05112233)


def test_a50601_light_sensor() -> None:
    # Plage ILL1 (DB0 bit 0 = 0) : 255 -> 60 000 lx, tension 255 -> 5,1 V
    assert eep.decode_a50601(t(0xA5, "FF 00 FF 08")) == {"illuminance": 60000, "voltage": 5.1}
    # Plage ILL2 (DB0 bit 0 = 1) : 0 -> 300 lx
    assert eep.decode_a50601(t(0xA5, "00 00 00 09"))["illuminance"] == 300
    assert eep.decode_a50601(t(0xA5, "00 00 00 00")) is None  # apprentissage


def test_a50904_co2() -> None:
    # 120/2 = 60 %, 45*10 = 450 ppm, 128*51/255 = 25,6 °C, HSN + TSN présents
    assert eep.decode_a50904(t(0xA5, "78 2D 80 0E")) == {
        "co2": 450,
        "humidity": 60.0,
        "temperature": 25.6,
    }
    assert eep.decode_a50904(t(0xA5, "78 2D 80 08")) == {"co2": 450}


def test_a50905_voc() -> None:
    # 0x04D2 = 1234, multiplicateur 1 (DB0 bits 0-1 = 2)
    assert eep.decode_a50905(t(0xA5, "04 D2 00 0A")) == {"voc": 1234}
    assert eep.decode_a50905(t(0xA5, "04 D2 00 08")) == {"voc": 12.34}


def test_f60501_water_leak() -> None:
    assert eep.decode_f60501(t(0xF6, "11")) == {"water_leak": True}
    assert eep.decode_f60501(t(0xF6, "00")) == {"water_leak": False}


def test_f610_window_handle() -> None:
    assert eep.decode_f610(t(0xF6, "F0")) == {"handle": "closed"}
    assert eep.decode_f610(t(0xF6, "C0")) == {"handle": "open"}
    assert eep.decode_f610(t(0xF6, "E0")) == {"handle": "open"}
    assert eep.decode_f610(t(0xF6, "D0")) == {"handle": "tilt"}
    assert eep.decode_f610(t(0xF6, "10")) is None


def test_decoder_registry() -> None:
    assert eep.find_decoder("D2-01-0C") is eep.decode_d201
    assert eep.find_decoder("A5-09-05") is eep.decode_a50905
    assert eep.find_decoder("A5-20-01") is None  # vanne thermostatique : phase 2
    assert eep.supported("soft_remote")
