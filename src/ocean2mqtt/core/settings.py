"""Réglages des produits (onglet Réglages, MQTT /set, entités « config » de HA).

Chaque fiche liste ses réglages (`reglages`). Un réglage est soit envoyé au produit
(messages NodOn CMD 0x2 / 0xB, D2-05, MSC, Remote Commissioning), soit appliqué par
Ocean2MQTT lui-même (corrections de mesure, délai d'indisponibilité…).
Le produit ne permet pas de relire la plupart de ces réglages : on garde la
dernière valeur envoyée.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from . import eep
from .device import REPEATER_LEVELS, RS_CALIBRATION, RS_SWITCH_TYPES, Device

POWER_ON_STATES = ("previous", "on", "off")
BUTTON_MODES = ("4", "2")


class SettingError(ValueError):
    """Valeur refusée ou réglage inconnu."""


@dataclass(frozen=True)
class Setting:
    key: str  # clé JSON (MQTT /set, état publié)
    kind: str  # binary, enum, numeric, action
    group: str = "product"  # product (envoyé au produit), local (Ocean2MQTT), recom
    options: tuple[str, ...] = ()
    min: float | None = None
    max: float | None = None
    step: float | None = None
    unit: str | None = None
    channel: int | None = None  # réglage par canal (0, 1…)
    readable: bool = False  # relu sur le produit (sinon : dernière valeur envoyée)

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v not in (None, (), False)}


def _channels(device: Device, kind: str) -> list[Setting]:
    channels = device.product.channels
    return [
        Setting(f"{kind}_l{ch + 1}" if channels > 1 else kind, "numeric", min=0, max=3600,
                step=1, unit="s", channel=ch)
        for ch in range(channels)
    ]


def settings_for(device: Device) -> list[Setting]:
    """Réglages proposés pour ce produit, dans l'ordre d'affichage."""
    product = device.product
    has = product.settings
    out: list[Setting] = []
    for key in ("led", "local_control", "taught_in", "power_failure"):
        if key in has:
            out.append(Setting(key, "binary"))
    if "power_on_state" in has:
        out.append(Setting("power_on_state", "enum", options=POWER_ON_STATES))
    if "switch_type" in has:
        out.append(Setting("switch_type", "enum", options=tuple(eep.SWITCH_TYPES)))
    if "auto_off" in has:
        out += _channels(device, "auto_off")
    if "delay_off" in has:
        out += _channels(device, "delay_off")
    if "roller_shutter" in has:
        out.append(Setting("travel_time", "numeric", min=eep.TRAVEL_TIME_MIN,
                           max=eep.TRAVEL_TIME_MAX, step=0.1, unit="s"))
        if device.gateway.reman_enabled:  # réglages par Remote Commissioning
            out += [
                Setting("rs_switch_type", "enum", "recom", options=tuple(RS_SWITCH_TYPES),
                        readable=True),
                Setting("calibration", "action", "recom", options=tuple(RS_CALIBRATION)),
            ]
    if product.is_actuator and product.brand.lower() == "nodon":
        out.append(Setting("repeater", "enum", options=tuple(REPEATER_LEVELS), readable=True))
    if product.metering:
        out.append(Setting("energy_reset", "action", options=("reset",)))
    if "buttons" in has:
        out.append(Setting("buttons", "enum", "local", options=BUTTON_MODES))
    if "temperature_offset" in has:
        out.append(Setting("temperature_offset", "numeric", "local", min=-5, max=5, step=0.1,
                           unit="°C"))
    if "humidity_offset" in has:
        out.append(Setting("humidity_offset", "numeric", "local", min=-20, max=20, step=0.1,
                           unit="%"))
    if "timeout" in has or not product.is_actuator:
        out.append(Setting("timeout", "numeric", "local", min=0, max=1440, step=5, unit="min"))
    return out


def _internal_key(setting: Setting) -> str:
    """Nom du réglage dans Device.settings."""
    if setting.channel is not None:
        kind = setting.key.split("_l")[0] if "_l" in setting.key else setting.key
        return f"{kind}_{setting.channel}"
    return {"power_on_state": "default_state"}.get(setting.key, setting.key)


def setting_value(device: Device, setting: Setting) -> Any:
    if setting.kind == "action":
        return None
    if setting.key == "repeater":
        level = device.state.get("repeater")
        return REPEATER_LEVELS[level] if isinstance(level, int) and level < 3 else None
    if setting.key == "rs_switch_type":
        return device.state.get("rs_switch_type")
    value = device.settings.get(_internal_key(setting))
    if setting.key == "travel_time" and not value:
        return None
    return value


def settings_values(device: Device) -> dict[str, Any]:
    return {
        s.key: v for s in settings_for(device) if (v := setting_value(device, s)) is not None
    }


def describe(device: Device) -> list[dict[str, Any]]:
    """Réglages et valeurs courantes (interface web, bridge/request/device/settings)."""
    return [{**s.as_dict(), "value": setting_value(device, s)} for s in settings_for(device)]


def _coerce(setting: Setting, value: Any) -> Any:
    if setting.kind == "binary":
        if isinstance(value, bool):
            return value
        text = str(value).strip().upper()
        if text in ("ON", "TRUE", "1"):
            return True
        if text in ("OFF", "FALSE", "0"):
            return False
        raise SettingError(f"{setting.key} : ON ou OFF attendu")
    if setting.kind in ("enum", "action"):
        text = str(value).strip().lower()
        if text not in setting.options:
            raise SettingError(f"{setting.key} : valeur attendue parmi {', '.join(setting.options)}")
        return text
    try:
        number = float(value)
    except (TypeError, ValueError) as err:
        raise SettingError(f"{setting.key} : nombre attendu") from err
    if setting.min is not None and number < setting.min or (
        setting.max is not None and number > setting.max
    ):
        raise SettingError(f"{setting.key} : entre {setting.min:g} et {setting.max:g}")
    if setting.step and setting.step >= 1:
        number = round(number)
    return number


async def apply_setting(device: Device, key: str, value: Any) -> None:
    """Applique un réglage (envoi radio si besoin) ; lève SettingError / GatewayError."""
    setting = next((s for s in settings_for(device) if s.key == key), None)
    if setting is None:
        raise SettingError(f"Réglage inconnu pour ce produit : {key}")
    value = _coerce(setting, value)
    internal = _internal_key(setting)
    if key in ("led", "local_control", "taught_in", "power_failure", "power_on_state"):
        await device.apply_local_settings(**{internal: value})
    elif setting.channel is not None:
        kind = "auto_off" if key.startswith("auto_off") else "delay_off"
        await device.set_timer(setting.channel, kind, value)
    elif key == "switch_type":
        await device.set_switch_type(value)
    elif key == "travel_time":
        await device.set_travel_time(value)
    elif key == "rs_switch_type":
        await device.rs_set_switch_type(value)
    elif key == "calibration":
        await device.rs_calibrate(value)
    elif key == "repeater":
        await device.set_repeater(value)
    elif key == "energy_reset":
        await device.reset_energy()
    else:  # réglages appliqués par Ocean2MQTT
        device.settings[internal] = int(value) if key == "timeout" else value
    device.notify({internal})


def is_setting(device: Device, key: str) -> bool:
    return any(s.key == key for s in settings_for(device))
