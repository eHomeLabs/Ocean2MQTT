[Français](Migration-depuis-NodOcean) · **English**

# Migrating from NodOcean for HA

Ocean2MQTT takes over NodOcean devices **without re-pairing**: names, rooms, actuator sender addresses and Remote Commissioning codes.

**Add-on (same Home Assistant)**: keep the **same stick**, install the add-on, **disable NodOcean for HA** (Settings → Devices & services → NodOcean for HA → ⋮ → Disable), start Ocean2MQTT and follow the **"NodOcean for HA detected"** wizard (same stick / other stick / fresh install).

**Ocean2MQTT on another machine**: in NodOcean for HA 0.8.6+, **EnOcean stick** device → **Export for Ocean2MQTT** button; import `nodocean_export_ocean2mqtt.json` in **Settings → Migration and backup**. The file contains your Remote Commissioning codes: don't share it.

Afterwards, NodOcean entities are replaced by Ocean2MQTT **MQTT entities**: update automations and dashboards, then remove the NodOcean integration.
