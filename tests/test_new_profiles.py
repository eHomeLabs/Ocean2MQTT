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


def test_f60502_smoke() -> None:
    assert eep.decode_f60502(t(0xF6, "10")) == {"smoke": True}
    assert eep.decode_f60502(t(0xF6, "00")) == {"smoke": False}
    assert eep.decode_f60502(t(0xF6, "30")) == {"battery_low": True}
    assert eep.decode_f60502(t(0xF6, "50")) is None


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
    assert eep.find_decoder("A5-20-01") is eep.decode_a52001
    assert eep.find_decoder("A5-99-01") is None
    assert eep.supported("soft_remote")


def test_a52001_valve() -> None:
    # 40 % ouverte, fenêtre ouverte détectée, 128 -> 20,1 °C
    state = eep.decode_a52001(t(0xA5, "28 02 80 08"))
    assert state == {
        "valve_position": 40,
        "temperature": 20.1,
        "window_open": True,
        "battery_low": False,
        "valve_error": False,
    }
    # Consigne 21 °C -> 134, SPS, données
    assert eep.a52001_setpoint(21) == bytes([134, 0, 0x04, 0x08])
    assert eep.a52001_setpoint(20, room_temperature=20)[1:3] == bytes([127, 0x05])
    teach = t(0xA5, "80 08 49 80")
    assert eep.teach_in_4bs_response(teach) == bytes([0x80, 0x08, 0x49, 0xF0])


def test_a50403_temperature_and_humidity() -> None:
    decode = eep.find_decoder("A5-04-03")
    assert decode(t(0xA5, "00 00 00 08")) == {"temperature": -20.0, "humidity": 0.0}
    assert decode(t(0xA5, "FF 03 FF 09")) == {"temperature": 60.0, "humidity": 100.0}
    assert decode(t(0xA5, "80 02 00 08")) == {"temperature": 20.0, "humidity": 50.2}
    assert decode(t(0xA5, "80 02 00 00")) is None
    assert decode(t(0xA5, "80 02 08")) is None


def test_a51012_temperature_humidity_local_setpoint():
    assert eep.find_decoder("A5-10-12") is eep.decode_a51012
    # DB0 contains only LRN: no A5-04 temperature-presence bit required.
    assert eep.decode_a51012(t(0xA5, "80 7D 7D 08")) == {
        "setpoint_raw": 128, "humidity": 50.0, "temperature": 20.0,
    }
    assert eep.decode_a51012(t(0xA5, "00 00 00 08")) == {
        "setpoint_raw": 0, "humidity": 0.0, "temperature": 0.0,
    }
    assert eep.decode_a51012(t(0xA5, "FF FA FA 08")) == {
        "setpoint_raw": 255, "humidity": 100.0, "temperature": 40.0,
    }
    for invalid in range(251, 256):
        result = eep.decode_a51012(t(0xA5, f"01 {invalid:02X} {invalid:02X} 08"))
        assert result == {"setpoint_raw": 1, "humidity": None, "temperature": None}
    assert eep.decode_a51012(t(0xA5, "40 90 00 80")) is None
    assert eep.decode_a51012(t(0xD2, "80 7D 7D 08")) is None
    for frame in ("", "00 00 08", "00 00 00 08 00"):
        assert eep.decode_a51012(t(0xA5, frame)) is None


def test_avidsen_101012_screen_setpoint_mapping_is_model_specific():
    for raw, screen in ((68, 11.0), (125, 20.0), (209, 33.5), (218, 35.0)):
        frame = t(0xA5, f"{raw:02X} 7D 7D 08")
        decoded = eep.decode_avidsen_101012(frame)
        assert decoded == {"setpoint_raw": raw, "setpoint": screen,
                           "temperature": 20.0, "humidity": 50.0}
        assert "setpoint" not in eep.decode_a51012(frame)
    assert eep.decode_avidsen_101012(t(0xA5, "40 90 00 80")) is None
    assert eep.decode_avidsen_101012(t(0xD2, "44 7D 7D 08")) is None
    for raw in range(256):
        value = eep.decode_avidsen_101012(t(0xA5, f"{raw:02X} 7D 7D 08"))["setpoint"]
        assert value * 2 == int(value * 2)
        assert abs(value - (raw * 0.16 + 0.12)) <= 0.25
