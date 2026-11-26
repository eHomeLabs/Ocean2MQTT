# Ocean2MQTT 0.2.5

- Add Avidsen 101012 temperature/humidity sensor with digital display and local set point, including its product image and FR/EN onboarding.
- Implement A5-10-12 decoding and a generic profile. Temperature and humidity are exposed alongside the read-only, unitless 0–255 local set point. No arbitrary Celsius conversion or remote set-point command is introduced.
- Add Avidsen 600104, 600102, 970221, 600105, 600106 and 970292 using existing profiles: temperature/humidity, contacts, metering on/off heating, six-mode pilot-wire heating and two-channel lighting.
- Include official manual links, FR/EN pairing instructions, 970221 calibration guidance and explicit hardware-validation limits. No wall switches are added.

All seven products remain Community pending hardware validation. Undocumented battery/tamper extensions and NodOn-specific configuration are not assumed. Generic artwork is used for the six additional references.

Validation: 162 tests passed in GitHub CI, 44 product sheets validated, catalog generation and frontend build passed. See PRs #27 and #28.

Existing devices, pairing, configuration and MQTT topics are preserved.
