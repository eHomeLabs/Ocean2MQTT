"""Ce que publie chaque produit (« exposes », comme dans Zigbee2MQTT).

Une seule description sert au pont MQTT, à la découverte Home Assistant et à
l'interface web : les cartes de l'interface sont construites à partir d'elle.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .device import PILOT_WIRE_MODES
from .product import Product

WALL_SWITCH_EVENTS = (
    "left_up", "left_down", "right_up", "right_down",
    "left_up_right_up", "left_down_right_down", "left_up_right_down", "left_down_right_up",
    "release",
)  # fmt: skip
SOFT_BUTTON_EVENTS = ("single", "double", "long", "long_release")
SINGLE_BUTTON_EVENTS = ("press", "release")
HANDLE_POSITIONS = ("closed", "open", "tilt")


@dataclass(frozen=True)
class Expose:
    key: str  # clé JSON publiée sur <base>/<produit>
    kind: str  # switch, light, cover, select, number, sensor, binary_sensor, enum, event
    access: str = "r"  # « r » lecture, « rw » commandable par /set
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = None
    category: str | None = None  # « diagnostic » : informations secondaires
    options: tuple[str, ...] = ()
    min: float | None = None
    max: float | None = None
    step: float | None = None

    def as_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v not in (None, ())}


def _sensor(key, unit, device_class, state_class="measurement", category=None) -> Expose:
    return Expose(key, "sensor", "r", unit, device_class, state_class, category)


TEMPERATURE = _sensor("temperature", "°C", "temperature")
HUMIDITY = _sensor("humidity", "%", "humidity")
ILLUMINANCE = _sensor("illuminance", "lx", "illuminance")
VOLTAGE = _sensor("voltage", "V", "voltage", category="diagnostic")
POWER = _sensor("power", "W", "power")
ENERGY = _sensor("energy", "kWh", "energy", "total_increasing")
BATTERY = _sensor("battery", "%", "battery", category="diagnostic")
LINKQUALITY = _sensor("rssi", "dBm", "signal_strength", category="diagnostic")


def exposes(product: Product) -> list[Expose]:
    eep = product.eep
    decoder = product.decoder
    out: list[Expose] = []
    if eep == "D2-01-0C":
        out.append(Expose("mode", "select", "rw", options=tuple(PILOT_WIRE_MODES)))
    elif eep.startswith("D2-01"):
        if product.channels > 1:
            out += [Expose(f"state_l{ch}", "light", "rw") for ch in range(1, product.channels + 1)]
        else:
            dclass = "outlet" if product.type == "prise" else "switch"
            out.append(Expose("state", "switch", "rw", device_class=dclass))
    if eep.startswith("D2-01") and product.metering:
        out += [POWER, ENERGY]
    if eep == "D2-05-00":
        out.append(Expose("position", "cover", "rw", "%", "shutter", min=0, max=100, step=1))
    if eep == "D5-00-01":
        out.append(Expose("open", "binary_sensor", device_class="opening"))
    if eep == "A5-02-05":
        out.append(TEMPERATURE)
    if eep in ("A5-04-01", "A5-04-02"):
        out += [TEMPERATURE, HUMIDITY]
    if eep == "A5-06-01":
        out += [ILLUMINANCE, VOLTAGE]
    if eep == "A5-07-03":
        out += [Expose("motion", "binary_sensor", device_class="motion"), ILLUMINANCE, VOLTAGE]
    for code in (eep, *product.extra_eeps):
        if code == "A5-09-04":
            out += [_sensor("co2", "ppm", "carbon_dioxide"), HUMIDITY, TEMPERATURE]
        if code == "A5-09-05":
            out.append(_sensor("voc", "ppb", "volatile_organic_compounds_parts"))
    if eep == "A5-20-01":
        out += [
            Expose("setpoint", "number", "rw", "°C", "temperature", min=5, max=30, step=0.5),
            TEMPERATURE,
            _sensor("valve_position", "%", None),
            Expose("window_open", "binary_sensor", device_class="window"),
            Expose("battery_low", "binary_sensor", device_class="battery", category="diagnostic"),
        ]
    if decoder == "single_button":
        out.append(Expose("action", "event", options=SINGLE_BUTTON_EVENTS))
    elif eep == "F6-02-01":
        out.append(Expose("action", "event", options=WALL_SWITCH_EVENTS))
    if eep == "F6-04-01":
        out.append(Expose("card", "binary_sensor", device_class="presence"))
    if eep == "F6-05-01":
        out.append(Expose("water_leak", "binary_sensor", device_class="moisture"))
    if eep == "F6-05-02":
        out += [
            Expose("smoke", "binary_sensor", device_class="smoke"),
            Expose("battery_low", "binary_sensor", device_class="battery", category="diagnostic"),
        ]
    if eep.startswith("F6-10"):
        out.append(Expose("handle", "enum", device_class="enum", options=HANDLE_POSITIONS))
    if eep == "D2-03-0A":
        out += [Expose("action", "event", options=SOFT_BUTTON_EVENTS), BATTERY]
    # Doublons possibles (CO2 + température d'un autre profil) : on garde le premier
    unique: dict[str, Expose] = {}
    for item in out:
        unique.setdefault(item.key, item)
    return [*unique.values(), LINKQUALITY]
