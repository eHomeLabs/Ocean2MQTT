[Français](Premiers-pas) · **English**

# Getting started

1. **Add a device**: search by brand, reference or EEP profile.
2. Open its sheet (picture, profile, pairing procedure) and **start pairing**.
3. Follow the procedure shown (press the device button, power it on…).
4. Give the device a **name** and a **room**; its MQTT topic (`ocean2mqtt/<name>`) is shown.
5. For devices supporting Remote Commissioning, choose the **security code** (see [[Remote Commissioning|Remote-Commissioning-EN]]).

The device appears in **My devices** and in Home Assistant under **Settings → Devices & services → MQTT**.

**No access to the learn button?** For a **sensor or switch**, open its sheet and use **"Add with the EnOcean ID"** (8 hex characters, on the label, box or QR code, or in the Telegrams page). Not possible for an actuator, which must learn Ocean2MQTT's address through its pairing procedure.

Ocean2MQTT listens all the time: when an unknown device sends its teach-in, a **"This device looks like"** banner suggests matching sheets; sensors and switches are then added in one click.

Device sheet tabs: **Control**, **Settings** (LED, power-on state, auto-off… also through MQTT `/set`), **Remote Commissioning**, **Telegrams**, **Information** (ID, topic, EEP, manual, **change sheet** without re-pairing, rename, remove).

**Backup**: Settings → Migration and backup → Download a backup (devices, names, rooms, settings and Remote Commissioning codes). Keep it safe.
