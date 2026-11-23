# Ocean2MQTT 0.2.4

- Add Nexelec INSAFE+ Origin / I870EO support (D2-14-30): smoke alarm, sensor fault, maintenance and environmental diagnostics, temperature, humidity, energy status, remaining lifetime, hygrothermal comfort and temperature/humidity air analysis.
- Add the product sheet, generic D2-14-30 profile, FR/EN labels and manual-ID onboarding instructions. The product remains Community pending hardware validation.
- Ignore the gateway chip ID and its 128 Base ID sender addresses in unknown senders, preserving external repeated telegrams and the raw journal.

Validation: 146 tests passed; product sheets, lint, frontend build and GitHub CI passed. See PR #25 and issue #24.

Existing devices and settings are preserved. Add the INSAFE+ using its EnOcean ID and the Nexelec INSAFE+ Origin sheet. Air analysis is based on temperature/humidity, not CO2 or VOC measurements. Manufacturer ID, authorised photo and physical teach-in procedure remain to be confirmed.
