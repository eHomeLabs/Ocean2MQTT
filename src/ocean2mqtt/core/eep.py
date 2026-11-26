"""Décodage / encodage des profils EEP (produits NodOn d'origine, puis autres marques).

Chaque décodeur reçoit un `RadioTelegram` et renvoie un dict d'états
(clés = « state keys » utilisées par les entités), ou None si le
télégramme n'est pas pertinent. Aucune dépendance Home Assistant.
"""

from __future__ import annotations

from typing import Any

from .esp3 import RORG_1BS, RORG_4BS, RORG_MSC, RORG_RPS, RORG_VLD, RadioTelegram

# --- Teach-in ------------------------------------------------------------------


def is_1bs_teach_in(t: RadioTelegram) -> bool:
    return t.rorg == RORG_1BS and len(t.payload) == 1 and not t.payload[0] & 0x08


def is_4bs_teach_in(t: RadioTelegram) -> bool:
    return t.rorg == RORG_4BS and len(t.payload) == 4 and not t.payload[3] & 0x08


def parse_4bs_teach_in_eep(t: RadioTelegram) -> tuple[int, int, int] | None:
    """Teach-in 4BS variante 2 : renvoie (func, type, fabricant) si présent."""
    p = t.payload
    if not is_4bs_teach_in(t) or not p[3] & 0x80:  # bit LRN type = EEP inclus
        return None
    func = p[0] >> 2
    type_ = ((p[0] & 0x03) << 5) | (p[1] >> 3)
    manufacturer = ((p[1] & 0x07) << 8) | p[2]
    return func, type_, manufacturer


# --- D2-01-xx : actionneurs on/off (+ mesure) -----------------------------------

D201_ALL_CHANNELS = 0x1E

UNIT_FACTORS = {
    # unité -> (type, facteur vers W ou Wh)
    0: ("energy", 1 / 3600),  # Ws
    1: ("energy", 1.0),  # Wh
    2: ("energy", 1000.0),  # kWh
    3: ("power", 1.0),  # W
    4: ("power", 1000.0),  # kW
}
# Valeurs de mesure invalides (débordement ou « non disponible »)
INVALID_MEASUREMENTS = frozenset({0xFFFFFFFF, 0x00FFFFFF})


def d201_set_output(channel: int, on: bool) -> bytes:
    """CMD 0x1 Actuator Set Output."""
    return bytes([0x01, channel & 0x1F, 0x64 if on else 0x00])


def d201_status_query(channel: int = D201_ALL_CHANNELS) -> bytes:
    """CMD 0x3 Actuator Status Query."""
    return bytes([0x03, channel & 0x1F])


def d201_measurement_query(channel: int = 0, power: bool = True) -> bytes:
    """CMD 0x6 Actuator Measurement Query (power=False : énergie)."""
    return bytes([0x06, (0x20 if power else 0x00) | (channel & 0x1F)])


def d201_pilot_wire_set(mode: int) -> bytes:
    """CMD 0x8 Actuator Set Pilot Wire Mode."""
    return bytes([0x08, mode & 0x07])


def d201_pilot_wire_query() -> bytes:
    """CMD 0x9 Actuator Pilot Wire Mode Query."""
    return bytes([0x09])


# Réglages des actionneurs D2-01 ---------------------------------------------------

DEFAULT_STATES = {"off": 0, "on": 1, "previous": 2}


def d201_set_local(
    *,
    led: bool = True,
    default_state: str = "previous",
    power_failure: bool = False,
    local_control: bool = True,
    taught_in: bool = True,
) -> bytes:
    """CMD 0x2 Actuator Set Local : tous les réglages en une trame, tous canaux.

    Octet 1 : bit 7 = télécommandes appairées actives, CMD = 2.
    Octet 2 : bit 5 = commande locale, bits 4-0 = canal (0x1E = tous).
    Octet 3 : rampes de variation (non utilisées par les relais).
    Octet 4 : bit 7 = mode nuit (LED éteinte), bit 6 = détection de coupure,
              bits 5-4 = état après coupure (0 OFF, 1 ON, 2 précédent).
    """
    return bytes(
        [
            (0x80 if taught_in else 0) | 0x02,
            (0x20 if local_control else 0) | D201_ALL_CHANNELS,
            0x00,
            (0 if led else 0x80)
            | (0x40 if power_failure else 0)
            | (DEFAULT_STATES[default_state] << 4),
        ]
    )


def _timer(seconds: float) -> int:
    return max(0, min(0xFFFE, round(seconds * 10)))


def d201_set_ext_interface(
    channel: int,
    auto_off: float = 0,
    delay_off: float = 0,
    switch_mode: int = 0,
    two_state: bool = False,
) -> bytes:
    """CMD 0xB Actuator Set External Interface Settings.

    Temporisations en secondes (pas de 0,1 s, 0 = désactivée).
    switch_mode : 0 non modifié, 1 interrupteur, 2 poussoir, 3 auto-détection.
    two_state : interrupteur 2 états (contact fermé = ON, ouvert = OFF), utile
    seulement avec switch_mode = 1.
    """
    return (
        bytes([0x0B, channel & 0x1F])
        + _timer(auto_off).to_bytes(2, "big")
        + _timer(delay_off).to_bytes(2, "big")
        + bytes([((switch_mode & 0x03) << 6) | (0x20 if two_state else 0x00)])
    )


# Type d'entrée filaire des SIN-2-1-01 / SIN-2-2-01 (CMD 0xB) : (mode, 2 états)
SWITCH_TYPES = {
    "auto": (3, False),
    "switch": (1, False),
    "switch_2_state": (1, True),
    "push_button": (2, False),
}


def d201_measurement_config(
    *,
    power: bool,
    delta: int,
    max_interval: int,
    min_interval: int,
    reset: bool = False,
    channel: int = 0,
) -> bytes:
    """CMD 0x5 Actuator Set Measurement : rapport automatique (+ remise à zéro).

    delta : variation minimale à signaler (W pour la puissance, Wh pour l'énergie).
    max_interval : secondes (pas de 10 s) ; min_interval : secondes (pas de 1 s).
    """
    delta = max(0, min(4095, int(delta)))
    unit = 3 if power else 1  # W ou Wh
    return bytes(
        [
            0x05,
            0x80 | (0x40 if reset else 0) | (0x20 if power else 0) | (channel & 0x1F),
            ((delta & 0x0F) << 4) | unit,
            (delta >> 4) & 0xFF,
            max(0, min(255, max_interval // 10)),
            max(0, min(255, min_interval)),
        ]
    )


# Messages fabricant NodOn (MSC, RORG D1, fabricant 0x046) -----------------------

MSC_HEADER = bytes([0x00, 0x46])


def msc_set_repeater(level: int) -> bytes:
    level = max(0, min(2, level))
    return MSC_HEADER + bytes([0x08, 1 if level else 0, level])


def msc_query_repeater() -> bytes:
    return MSC_HEADER + bytes([0x09])


def msc_query_firmware() -> bytes:
    return MSC_HEADER + bytes([0x02])


def decode_msc(t: RadioTelegram) -> dict[str, Any] | None:
    """Réponses NodOn : niveau du répéteur (0x0A) et version firmware (0x03)."""
    p = t.payload
    if t.rorg != RORG_MSC or len(p) < 4 or p[:2] not in (b"\x00\x46", b"\x46\x00"):
        return None
    cmd = p[2]
    if cmd == 0x0A:
        if len(p) >= 5:
            level = p[4] if p[3] else 0
        else:
            level = p[3]
        return {"repeater": level if level <= 2 else None}
    if cmd == 0x03:
        return {"firmware": ".".join(f"{b:02d}" for b in p[3:])}
    return None


def decode_d201(t: RadioTelegram, channels: int = 1) -> dict[str, Any] | None:
    """Décode les réponses D2-01 (status 0x4, mesure 0x7, fil pilote 0xA)."""
    p = t.payload
    if t.rorg != RORG_VLD or not p:
        return None
    cmd = p[0] & 0x0F
    if cmd == 0x04 and len(p) >= 3:
        channel = p[1] & 0x1F
        value = p[2] & 0x7F
        is_on = value > 0
        if channels == 1:
            return {"output_0": is_on}
        if channel == D201_ALL_CHANNELS:
            return {f"output_{c}": is_on for c in range(channels)}
        if channel < channels:
            return {f"output_{channel}": is_on}
        return None
    if cmd == 0x07 and len(p) >= 6:
        unit = (p[1] >> 5) & 0x07
        value = int.from_bytes(p[2:6], "big")
        if value in INVALID_MEASUREMENTS:
            return None  # valeur invalide / non disponible
        kind_factor = UNIT_FACTORS.get(unit)
        if kind_factor is None:
            return None
        kind, factor = kind_factor
        if kind == "energy":
            return {"energy": round(value * factor / 1000, 3)}  # kWh
        return {"power": round(value * factor, 1)}  # W
    if cmd == 0x0A and len(p) >= 2:
        return {"pilot_wire_mode": p[1] & 0x07}
    return None


# --- D2-05-00 : volets roulants -------------------------------------------------
# Côté appareil : 0 % = ouvert (haut), 100 % = fermé (bas).
# Côté Home Assistant : 100 = ouvert, 0 = fermé.


def d205_go_to(ha_position: int) -> bytes:
    dev = max(0, min(100, 100 - int(ha_position)))
    return bytes([dev, 0x00, 0x00, 0x01])


def d205_stop() -> bytes:
    return bytes([0x02])


def d205_query() -> bytes:
    return bytes([0x03])


TRAVEL_TIME_MIN = 5.0  # s (guide expert SIN-2-RS-01)
TRAVEL_TIME_MAX = 300.0


def d205_set_travel_time(seconds: float) -> bytes:
    """CMD 0x5 Set Parameters : temps de course montée = descente (pas de 10 ms).

    Exemple NodOn : 60,32 s -> 17 90 00 00 05. Le module remet sa position à 0 %.
    """
    seconds = max(TRAVEL_TIME_MIN, min(TRAVEL_TIME_MAX, float(seconds)))
    value = round(seconds * 100) & 0x7FFF
    return value.to_bytes(2, "big") + bytes([0x00, 0x00, 0x05])


def decode_d205(t: RadioTelegram) -> dict[str, Any] | None:
    p = t.payload
    if t.rorg != RORG_VLD or not p:
        return None
    if len(p) == 4 and p[3] & 0x0F == 0x04:
        pos = p[0]
        if pos > 100:  # 127 = position inconnue
            return {"position": None}
        return {"position": 100 - pos}
    return None


# --- D5-00-01 : contact d'ouverture ---------------------------------------------


def decode_d50001(t: RadioTelegram) -> dict[str, Any] | None:
    if t.rorg != RORG_1BS or len(t.payload) != 1:
        return None
    db0 = t.payload[0]
    if not db0 & 0x08:  # télégramme d'apprentissage : pas d'état fiable
        return None
    # CO : 1 = contact fermé. Pour HA, binary_sensor « ouverture » : True = ouvert.
    return {"opening": not bool(db0 & 0x01)}


# --- A5-02-05 : température 0..40 °C --------------------------------------------


def decode_a50205(t: RadioTelegram) -> dict[str, Any] | None:
    if t.rorg != RORG_4BS or len(t.payload) != 4 or not t.payload[3] & 0x08:
        return None
    raw = t.payload[2]
    # Spécification EEP : 255 = 0 °C, 0 = +40 °C (échelle inversée)
    return {"temperature": round(40 - raw * 40 / 255, 1)}


# --- A5-10-12: temperature, humidity and raw local set point --------------------


def decode_a51012(t: RadioTelegram) -> dict[str, Any] | None:
    """EEP 2.6.8 p.56: DB3 set point has no standard Celsius conversion."""
    if t.rorg != RORG_4BS or len(t.payload) != 4 or not t.payload[3] & 0x08:
        return None
    setpoint, humidity, temperature, _ = t.payload
    return {
        "setpoint_raw": setpoint,
        "humidity": round(humidity * 100 / 250, 1) if humidity <= 250 else None,
        "temperature": round(temperature * 40 / 250, 1) if temperature <= 250 else None,
    }


def decode_avidsen_101012(t: RadioTelegram) -> dict[str, Any] | None:
    """101012 screen mapping, calibrated from four user-reported hardware readings."""
    state = decode_a51012(t)
    if state is not None:
        # Celsius = raw * 0.16 + 0.12, rounded to the screen's half-degree steps.
        state["setpoint"] = round((state["setpoint_raw"] * 32 + 24) / 100) / 2
    return state


# --- A5-04-01 : température 0..40 °C + humidité ---------------------------------


def _decode_a504(t: RadioTelegram, t_min: float, t_max: float) -> dict[str, Any] | None:
    if t.rorg != RORG_4BS or len(t.payload) != 4 or not t.payload[3] & 0x08:
        return None
    hum_raw, temp_raw, db0 = t.payload[1], t.payload[2], t.payload[3]
    state: dict[str, Any] = {}
    if hum_raw <= 250:
        state["humidity"] = round(hum_raw * 100 / 250, 1)
    if db0 & 0x02 and temp_raw <= 250:  # TSN : capteur de température présent
        state["temperature"] = round(t_min + temp_raw * (t_max - t_min) / 250, 1)
    return state or None


def decode_a50401(t: RadioTelegram) -> dict[str, Any] | None:
    return _decode_a504(t, 0, 40)


# --- A5-04-02 : température -20..+60 °C + humidité (capteurs extérieurs) --------


def decode_a50402(t: RadioTelegram) -> dict[str, Any] | None:
    return _decode_a504(t, -20, 60)


def decode_a50403(t: RadioTelegram) -> dict[str, Any] | None:
    if t.rorg != RORG_4BS or len(t.payload) != 4 or not t.payload[3] & 0x08:
        return None
    db3, db2, db1, _ = t.payload
    temperature_raw = ((db2 & 0x03) << 8) | db1
    return {
        "temperature": round(-20 + temperature_raw * 80 / 1023, 1),
        "humidity": round(db3 * 100 / 255, 1),
    }


# --- F6-02-01 : interrupteur 2 rockers ------------------------------------------
# R1 : 0 = AI (bas gauche), 1 = A0 (haut gauche), 2 = BI (bas droite), 3 = B0 (haut droite)

ROCKER_NAMES = {0: "left_down", 1: "left_up", 2: "right_down", 3: "right_up"}
# Soft Remote CRC-2 (Quick User Guide) : 10 haut droite, 30 bas droite, 50 haut gauche, 70 bas gauche
SOFT_REMOTE_NAMES = {0: "right_up", 1: "right_down", 2: "left_up", 3: "left_down"}


def decode_single_button(t: RadioTelegram) -> dict[str, Any] | None:
    """Interrupteur 1 bouton (CFS-2) : appui / relâchement."""
    if t.rorg != RORG_RPS or len(t.payload) != 1:
        return None
    return {"event": "press" if t.payload[0] & 0x10 else "release"}


def decode_f60401(t: RadioTelegram) -> dict[str, Any] | None:
    """Interrupteur à carte (CCS-2) : 30 (ou 70) = carte insérée, 00 = retirée."""
    if t.rorg != RORG_RPS or len(t.payload) != 1:
        return None
    return {"card": t.payload[0] != 0}


def decode_a50703(t: RadioTelegram) -> dict[str, Any] | None:
    """Détecteur de mouvement PIR-2 : tension pile, luminosité, mouvement."""
    if t.rorg != RORG_4BS or len(t.payload) != 4 or not t.payload[3] & 0x08:
        return None
    supply, lux_hi, lux_lo, db0 = t.payload
    state: dict[str, Any] = {"motion": bool(db0 & 0x80)}
    if supply <= 250:
        state["voltage"] = round(supply * 0.02, 2)
    lux = (lux_hi << 2) | (lux_lo >> 6)
    if lux <= 1000:
        state["illuminance"] = lux
    return state


def decode_f60201(t: RadioTelegram, names: dict[int, str] = ROCKER_NAMES) -> dict[str, Any] | None:
    if t.rorg != RORG_RPS or len(t.payload) != 1:
        return None
    db0 = t.payload[0]
    pressed = bool(db0 & 0x10)
    if not pressed:
        return {"event": "release"}
    if t.status and not t.status & 0x10:
        # NU = 0 : appui de 3 boutons ou plus, non géré
        return None
    first = names[(db0 >> 5) & 0x07 & 0x03]
    if db0 & 0x01:  # seconde action simultanée
        second = names[(db0 >> 1) & 0x03]
        return {"event": "_".join(sorted((first, second)))}
    return {"event": first}


# --- D2-03-0A : Soft Button (appui + batterie) ----------------------------------

SOFT_BUTTON_ACTIONS = {1: "single", 2: "double", 3: "long", 4: "long_release"}


def decode_d2030a(t: RadioTelegram) -> dict[str, Any] | None:
    p = t.payload
    if t.rorg != RORG_VLD or len(p) != 2:
        return None
    state: dict[str, Any] = {}
    if 1 <= p[0] <= 100:
        state["battery"] = p[0]
    action = SOFT_BUTTON_ACTIONS.get(p[1])
    if action:
        state["event"] = action
    return state or None


# --- Profils ajoutés pour Ocean2MQTT (Ubiwizz…) ---------------------------------
# Implémentés d'après la spécification EEP ; à confirmer sur produit réel.


def decode_a50601(t: RadioTelegram) -> dict[str, Any] | None:
    """Capteur de luminosité 300..60 000 lx (DB0 bit 0 = plage utilisée)."""
    if t.rorg != RORG_4BS or len(t.payload) != 4 or not t.payload[3] & 0x08:
        return None
    supply, ill2, ill1, db0 = t.payload
    if db0 & 0x01:  # plage ILL2 : 300..30 000 lx
        lux = 300 + ill2 * (30000 - 300) / 255
    else:  # plage ILL1 : 600..60 000 lx
        lux = 600 + ill1 * (60000 - 600) / 255
    return {"illuminance": round(lux), "voltage": round(supply * 5.1 / 255, 2)}


def decode_a50904(t: RadioTelegram) -> dict[str, Any] | None:
    """Capteur CO2 (0..2 550 ppm) avec humidité et température optionnelles."""
    if t.rorg != RORG_4BS or len(t.payload) != 4 or not t.payload[3] & 0x08:
        return None
    hum, conc, temp, db0 = t.payload
    state: dict[str, Any] = {"co2": conc * 10}
    if db0 & 0x04 and hum <= 200:
        state["humidity"] = round(hum / 2, 1)
    if db0 & 0x02:
        state["temperature"] = round(temp * 51 / 255, 1)
    return state


VOC_SCALE = {0: 0.01, 1: 0.1, 2: 1, 3: 10}


def decode_a50905(t: RadioTelegram) -> dict[str, Any] | None:
    """Capteur de COV : concentration en ppb (DB1 = identifiant, 0 = COV totaux)."""
    if t.rorg != RORG_4BS or len(t.payload) != 4 or not t.payload[3] & 0x08:
        return None
    hi, lo, voc_id, db0 = t.payload
    value = ((hi << 8) | lo) * VOC_SCALE[db0 & 0x03]
    if voc_id != 0:
        return {f"voc_{voc_id}": value}
    return {"voc": round(value, 2)}


def decode_f60501(t: RadioTelegram) -> dict[str, Any] | None:
    """Détecteur de fuite d'eau autonome : 0x11 = eau détectée."""
    if t.rorg != RORG_RPS or len(t.payload) != 1:
        return None
    return {"water_leak": t.payload[0] == 0x11}


def decode_f60502(t: RadioTelegram) -> dict[str, Any] | None:
    """Détecteur de fumée (F6-05-02) : 0x10 = alarme, 0x00 = repos, 0x30 = pile faible."""
    if t.rorg != RORG_RPS or len(t.payload) != 1:
        return None
    value = t.payload[0]
    if value == 0x30:
        return {"battery_low": True}
    if value in (0x00, 0x10):
        return {"smoke": value == 0x10}
    return None


HANDLE_POSITIONS = {0xC0: "open", 0xE0: "open", 0xF0: "closed", 0xD0: "tilt"}


def decode_f610(t: RadioTelegram) -> dict[str, Any] | None:
    """Poignée de fenêtre (F6-10-00 / F6-10-01) : fermée, ouverte ou en oscillo-battant."""
    if t.rorg != RORG_RPS or len(t.payload) != 1:
        return None
    position = HANDLE_POSITIONS.get(t.payload[0] & 0xF0)
    return {"handle": position} if position else None


# --- A5-20-01 : tête thermostatique (bidirectionnelle) ---------------------------
# La vanne émet régulièrement son état ; la passerelle doit répondre aussitôt avec
# la consigne (sinon la vanne garde la précédente). Consigne en °C (bit SPS = 1).


def decode_a52001(t: RadioTelegram) -> dict[str, Any] | None:
    if t.rorg != RORG_4BS or len(t.payload) != 4 or not t.payload[3] & 0x08:
        return None
    cv, flags, temp, _ = t.payload
    return {
        "valve_position": min(cv, 100),
        "temperature": round(temp * 40 / 255, 1),
        "window_open": bool(flags & 0x02),
        "battery_low": bool(flags & 0x10),
        "valve_error": bool(flags & 0x01 or flags & 0x04),
    }


def a52001_setpoint(setpoint: float, room_temperature: float | None = None) -> bytes:
    """Réponse à la vanne : consigne en °C (0..40), température pièce facultative."""
    sp = round(max(0.0, min(40.0, setpoint)) * 255 / 40)
    db1 = 0x04  # SPS : la consigne est une température
    tmp = 0
    if room_temperature is not None:
        tmp = 255 - round(max(0.0, min(40.0, room_temperature)) * 255 / 40)
        db1 |= 0x01  # RCU : utiliser la température fournie par la passerelle
    return bytes([sp, tmp, db1, 0x08])


def teach_in_4bs_response(t: RadioTelegram) -> bytes:
    """Réponse au teach-in 4BS bidirectionnel : même EEP / fabricant, statut accepté."""
    p = t.payload
    return bytes([p[0], p[1], p[2], 0xF0])


# --- A5-07-01 : détecteur de présence (PIR) ------------------------------------


def decode_a50701(t: RadioTelegram) -> dict[str, Any] | None:
    """DB3 tension (si DB0.0), DB1 ≥ 128 = mouvement."""
    if t.rorg != RORG_4BS or len(t.payload) != 4 or not t.payload[3] & 0x08:
        return None
    supply, _db2, pir, db0 = t.payload
    state: dict[str, Any] = {"motion": pir >= 128}
    if db0 & 0x01 and supply <= 250:
        state["voltage"] = round(supply * 5 / 250, 2)
    return state


# --- A5-08-01/02/03 : luminosité, température, présence -------------------------
# DB3 tension 0..5,1 V, DB2 luminosité, DB1 température, DB0.1 PIRS (0 = mouvement),
# DB0.0 bouton de présence (0 = appuyé).

_A508_RANGES = {
    "A5-08-01": (510, 0, 51),
    "A5-08-02": (1020, 0, 51),
    "A5-08-03": (1530, -30, 50),
}


def _decode_a508(t: RadioTelegram, lux_max: float, t_min: float, t_max: float):
    if t.rorg != RORG_4BS or len(t.payload) != 4 or not t.payload[3] & 0x08:
        return None
    supply, ill, temp, db0 = t.payload
    return {
        "motion": not db0 & 0x02,
        "illuminance": round(ill * lux_max / 255),
        "temperature": round(t_min + temp * (t_max - t_min) / 255, 1),
        "voltage": round(supply * 5.1 / 255, 2),
        "occupancy_button": not db0 & 0x01,
    }


def _a508(eep_code: str):
    lux_max, t_min, t_max = _A508_RANGES[eep_code]
    return lambda t: _decode_a508(t, lux_max, t_min, t_max)


# --- A5-30-03 : entrées numériques, réveil et température ----------------------


def decode_a53003(t: RadioTelegram) -> dict[str, Any] | None:
    """DB2 température 255..0 = 0..40 °C, DB1 bit 4 = réveil (WA0), bits 3..0 = DI3..DI0."""
    if t.rorg != RORG_4BS or len(t.payload) != 4 or not t.payload[3] & 0x08:
        return None
    temp, inputs = t.payload[1], t.payload[2]
    state: dict[str, Any] = {
        "temperature": round((255 - temp) * 40 / 255, 1),
        "wake": bool(inputs & 0x10),
    }
    for i in range(4):
        state[f"input_{i}"] = bool(inputs & (1 << i))
    return state


# --- F6-01-01 : bouton-poussoir (1 contact) -------------------------------------


def decode_f60101(t: RadioTelegram) -> dict[str, Any] | None:
    """0x10 = appui, 0x00 = relâchement (Eltako FPE-1…)."""
    if t.rorg != RORG_RPS or len(t.payload) != 1:
        return None
    return {"event": "press" if t.payload[0] & 0x10 else "release"}


# --- D2-14-30: smoke detector with temperature/humidity monitoring --------------


def decode_d21430(t: RadioTelegram) -> dict[str, Any] | None:
    """EEP 2.6.8, D2-14-30: 48 bits, MSB first; reserved values are unavailable."""
    if t.rorg != RORG_VLD or len(t.payload) != 6:
        return None
    bits = int.from_bytes(t.payload, "big")

    def field(offset: int, size: int) -> int:
        return (bits >> (48 - offset - size)) & ((1 << size) - 1)

    energy = field(13, 2)
    comfort = field(39, 2)
    air = field(41, 3)
    return {
        "smoke": bool(field(0, 1)),
        "sensor_fault": bool(field(1, 1)),
        "maintenance_required": bool(field(2, 1)),
        "humidity_out_of_range": bool(field(3, 1)),
        "temperature_out_of_range": bool(field(4, 1)),
        "weeks_since_maintenance": value if (value := field(5, 8)) <= 250 else None,
        "battery_status": ("high", "medium", "low", "critical")[energy],
        "battery_low": energy >= 2,
        "remaining_lifetime": value if (value := field(15, 8)) <= 120 else None,
        "temperature": value / 5 if (value := field(23, 8)) <= 250 else None,
        "humidity": value / 2 if (value := field(31, 8)) <= 200 else None,
        "hygrothermal_comfort": ("good", "medium", "bad")[comfort] if comfort < 3 else None,
        "air_quality": ("optimal", "dry", "high_humidity", "high_temperature_and_humidity",
                        "out_of_analysis_range")[air] if air < 5 else None,
    }


# --- D2-14-41 : multicapteur (STM 550) -----------------------------------------
# Température 10 bits (0..1000 = -40..+60 °C), humidité 8 bits (0..200 = 0..100 %),
# luminosité 17 bits (lx), état d'accélération 2 bits, accélération X/Y/Z 10 bits
# (0..1000 = -2,5..+2,5 g), contact 1 bit (1 = fermé). 68 bits sur 9 octets.

ACCELERATION_STATUS = ("periodic", "threshold_1", "threshold_2", "reserved")


def decode_d21441(t: RadioTelegram) -> dict[str, Any] | None:
    if t.rorg != RORG_VLD or len(t.payload) < 9:
        return None
    bits = int.from_bytes(t.payload[:9], "big")

    def field(offset: int, size: int) -> int:
        return (bits >> (72 - offset - size)) & ((1 << size) - 1)

    state: dict[str, Any] = {}
    if (tmp := field(0, 10)) <= 1000:
        state["temperature"] = round(tmp / 10 - 40, 1)
    if (hum := field(10, 8)) <= 200:
        state["humidity"] = round(hum / 2, 1)
    if (ill := field(18, 17)) <= 100000:
        state["illuminance"] = ill
    state["acceleration_status"] = ACCELERATION_STATUS[field(35, 2)]
    for name, offset in (("x", 37), ("y", 47), ("z", 57)):
        if (acc := field(offset, 10)) <= 1000:
            state[f"acceleration_{name}"] = round(acc / 200 - 2.5, 2)
    state["open"] = not field(67, 1)
    return state


# --- Eltako : luminosité A5-06-01 « exceptions by Eltako » (FAH60, FHD60SB…) ---


def decode_eltako_brightness(t: RadioTelegram) -> dict[str, Any] | None:
    """DB3 = 0..100 lx (si DB2 = 0), DB2 = 300..30 000 lx (0..255)."""
    if t.rorg != RORG_4BS or len(t.payload) != 4 or not t.payload[3] & 0x08:
        return None
    db3, db2 = t.payload[0], t.payload[1]
    lux = min(db3, 100) if db2 == 0 else 300 + db2 * (30000 - 300) / 255
    return {"illuminance": round(lux)}


# --- Choix du décodeur ----------------------------------------------------------
# Clé = EEP complet, préfixe « RR-FF » ou nom de décodeur particulier (champ
# « decodeur » d'une fiche produit).

DECODERS = {
    "D2-01": decode_d201,
    "D2-05-00": decode_d205,
    "D5-00-01": decode_d50001,
    "A5-02-05": decode_a50205,
    "A5-10-12": decode_a51012,
    "avidsen_101012": decode_avidsen_101012,
    "A5-04-01": decode_a50401,
    "A5-04-02": decode_a50402,
    "A5-04-03": decode_a50403,
    "A5-06-01": decode_a50601,
    "A5-07-01": decode_a50701,
    "A5-07-03": decode_a50703,
    "A5-08-01": _a508("A5-08-01"),
    "A5-08-02": _a508("A5-08-02"),
    "A5-08-03": _a508("A5-08-03"),
    "A5-30-03": decode_a53003,
    "D2-14-30": decode_d21430,
    "D2-14-41": decode_d21441,
    "F6-01-01": decode_f60101,
    "A5-09-04": decode_a50904,
    "A5-09-05": decode_a50905,
    "F6-02-01": decode_f60201,
    "F6-04-01": decode_f60401,
    "F6-05-01": decode_f60501,
    "F6-05-02": decode_f60502,
    "F6-10-00": decode_f610,
    "F6-10-01": decode_f610,
    "D2-03-0A": decode_d2030a,
    "A5-20-01": decode_a52001,
    "soft_remote": lambda t: decode_f60201(t, SOFT_REMOTE_NAMES),
    "single_button": decode_single_button,
    "eltako_brightness": decode_eltako_brightness,
}


def find_decoder(key: str):
    """Décodeur pour un EEP (« A5-04-01 ») ou un nom de décodeur particulier."""
    if key in DECODERS:
        return DECODERS[key]
    return DECODERS.get(key[:5])


def decode_by_name(key: str, t: RadioTelegram) -> dict[str, Any] | None:
    decoder = find_decoder(key)
    if decoder is None:
        return None
    if decoder is decode_d201:
        return decode_d201(t)
    return decoder(t)


def supported(key: str) -> bool:
    return find_decoder(key) is not None
