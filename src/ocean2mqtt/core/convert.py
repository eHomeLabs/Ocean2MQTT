"""Conversion entre l'état interne d'un produit et le JSON publié / les commandes reçues."""

from __future__ import annotations

from typing import Any

from .device import PILOT_WIRE_MODES, REPEATER_LEVELS, Device

_ON = {"ON", "1", "TRUE"}
_OFF = {"OFF", "0", "FALSE"}
# Clés de l'état reprises telles quelles dans le JSON
_COPY = (
    "power", "energy", "illuminance", "voltage", "battery", "firmware", "motion", "card",
    "co2", "voc", "water_leak", "smoke", "handle", "valve_position", "window_open", "battery_low",
    "setpoint", "sensor_fault", "maintenance_required", "humidity_out_of_range",
    "temperature_out_of_range", "weeks_since_maintenance", "battery_status",
    "remaining_lifetime", "hygrothermal_comfort", "air_quality",
)  # fmt: skip


class CommandError(ValueError):
    """Commande incomprise ou impossible pour ce produit."""


def device_payload(device: Device) -> dict[str, Any]:
    """État d'un produit tel que publié sur MQTT et envoyé à l'interface web."""
    product = device.product
    state = device.state
    out: dict[str, Any] = {}
    if product.eep.startswith("D2-01") and product.eep != "D2-01-0C":
        if product.channels > 1:
            for ch in range(product.channels):
                if (value := state.get(f"output_{ch}")) is not None:
                    out[f"state_l{ch + 1}"] = "ON" if value else "OFF"
        elif (value := state.get("output_0")) is not None:
            out["state"] = "ON" if value else "OFF"
    if product.eep == "D2-05-00" and "position" in state:
        pos = state["position"]
        out["position"] = pos
        if pos is not None:
            out["state"] = "CLOSED" if pos == 0 else "OPEN"
    if (mode := state.get("pilot_wire_mode")) is not None and mode < len(PILOT_WIRE_MODES):
        out["mode"] = PILOT_WIRE_MODES[mode]
    for key in _COPY:
        if state.get(key) is not None:
            out[key] = state[key]
    for key, offset in (("temperature", "temperature_offset"), ("humidity", "humidity_offset")):
        if state.get(key) is not None:
            out[key] = round(state[key] + (device.settings.get(offset) or 0), 1)
    if state.get("opening") is not None:
        out["open"] = bool(state["opening"])
    if (level := state.get("repeater")) is not None and level < len(REPEATER_LEVELS):
        out["repeater"] = REPEATER_LEVELS[level]
    if device.last_dbm is not None:
        out["rssi"] = device.last_dbm
    # Réglages (comme Zigbee2MQTT : publiés avec l'état, modifiables par /set)
    from .settings import settings_values

    for key, value in settings_values(device).items():
        out.setdefault(key, ("ON" if value else "OFF") if isinstance(value, bool) else value)
    return out


def _parse_switch(value: Any, current: bool | None) -> bool | None:
    if isinstance(value, bool):
        return value
    text = str(value).strip().upper()
    if text in _ON:
        return True
    if text in _OFF:
        return False
    if text == "TOGGLE":
        return not current
    return None


def text_command(device: Device, text: str) -> dict[str, Any]:
    """Commande texte simple (« ON », « 50 », « eco »…) -> commande JSON."""
    eep = device.product.eep
    if eep == "D2-05-00":
        return {"position": int(text)} if text.isdigit() else {"state": text}
    if eep == "D2-01-0C":
        return {"mode": text}
    if eep == "A5-20-01":
        return {"setpoint": float(text)}
    return {"state": text}


async def apply_command(device: Device, command: dict[str, Any]) -> list[str]:
    """Exécute une commande /set. Renvoie la liste des clés ignorées."""
    product = device.product
    ignored: list[str] = []
    for key, value in command.items():
        if product.eep == "D2-05-00":
            if key == "position":
                await device.cover_position(max(0, min(100, int(value))))
                continue
            if key == "state":
                action = str(value).strip().upper()
                if action == "OPEN":
                    await device.cover_position(100)
                elif action == "CLOSE":
                    await device.cover_position(0)
                elif action == "STOP":
                    await device.cover_stop()
                else:
                    ignored.append(key)
                continue
        if product.eep == "D2-01-0C" and key == "mode":
            if value in PILOT_WIRE_MODES:
                await device.set_pilot_wire(value)
            else:
                ignored.append(key)
            continue
        if product.eep == "A5-20-01" and key == "setpoint":
            await device.set_setpoint(float(value))
            continue
        channel: int | None = None
        if product.eep.startswith("D2-01") and product.eep != "D2-01-0C":
            if key == "state" and product.channels == 1:
                channel = 0
            elif key.startswith("state_l") and key[7:].isdigit():
                channel = int(key[7:]) - 1
                if not 0 <= channel < product.channels:
                    channel = None
        if channel is not None:
            on = _parse_switch(value, device.state.get(f"output_{channel}"))
            if on is None:
                ignored.append(key)
            else:
                await device.set_output(channel, on)
            continue
        ignored.append(key)
    return ignored
