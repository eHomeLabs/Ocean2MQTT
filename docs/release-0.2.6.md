# Ocean2MQTT 0.2.6

- Add a read-only local set-point sensor in °C for the Avidsen 101012, alongside the existing raw value.
- Calibrate conversion against user hardware readings: raw 68 → 11.0°C, 125 → 20.0°C, 209 → 33.5°C, 218 → 35.0°C. Formula: round(raw × 0.32 + 0.24) / 2.
- Scope conversion to the 101012 product sheet; generic A5-10-12 remains unitless. Room-temperature offsets do not affect the local set point; no remote set-point command is added.
- Clarify pairing: long press in the rear pinhole, short press toggles °C/°F.
- Update README, Docker example and FR/EN wiki version references.

Existing pairing, devices, settings and MQTT topics are preserved. For an already paired Avidsen 101012, Home Assistant discovers the additional sensor after upgrading and receiving a new telegram. Re-pairing is not required. Generic devices must use the Avidsen 101012 product sheet to enable its model-specific conversion.

Validation: hardware calibration regression tests, read-only MQTT discovery and offset isolation; CI on Python 3.12/3.13, frontend and product-sheet validation. See PR #31.
