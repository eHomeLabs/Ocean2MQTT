# Generic device artwork

Devices without a product photo use a shared set of twelve unbranded illustrations.
Each illustration includes a “générique” badge to distinguish it from a manufacturer's
product photo. A failed photo request also falls back to the generic illustration.

The library is stored as a regular 4-column, 3-row PNG atlas in
`frontend/src/assets/generic-devices.png`. `ProductImage.tsx` selects a square tile
without downloading twelve separate images. Vite bundles the asset locally; no
external image service is needed at runtime.

| Tile | Illustration |
| --- | --- |
| 0 | Temperature / humidity sensor |
| 1 | Smart plug |
| 2 | Motion / occupancy detector |
| 3 | Illuminance sensor |
| 4 | Air quality sensor |
| 5 | Door / window contact |
| 6 | Relay |
| 7 | Roller shutter |
| 8 | Wall switch |
| 9 | Thermostat |
| 10 | Radiator valve |
| 11 | Water leak detector |

Selection uses EEP, exposed capabilities and product type, in that order where
appropriate. A generic D2-01 actuator stays a relay unless its product type identifies
it as a plug. Combined occupancy / light sensors use the motion illustration;
air quality sensors take precedence over their temperature measurement.
The generic artwork does not indicate validation status.

The original illustrations were generated for Ocean2MQTT and have no manufacturer
branding. Product photos remain the first choice when provided.
