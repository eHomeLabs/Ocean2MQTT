[Français](Ajouter-un-produit-non-support%C3%A9) · **English**

# Adding an unsupported device

| Situation | Solution |
| --- | --- |
| The device uses a standard EEP profile already supported | **1. Generic mode**: works right away |
| You don't know its profile | **2. Identify it** with the radio log |
| It works in generic mode and should be in the list for everyone | **3. Submit a device sheet** |
| Its profile is not supported | **4. Request a new profile** |

## 1. Generic mode

Most EnOcean devices follow a standard **EEP profile** (`RORG-FUNC-TYPE`, e.g. `A5-02-05` for a temperature sensor). **Add a device → Generic**, pick the profile (see the device manual or datasheet), start pairing and put the device in learn mode.

Generic profiles: F6-02-01 (2-rocker switch), F6-04-01 (key card), F6-05-01 (water leak), F6-05-02 (smoke detector), F6-10-00 (window handle), D5-00-01 (contact), A5-02-05 (temperature), A5-04-01 (temperature + humidity), A5-06-01 (light), A5-07-03 (motion + light), A5-09-04 (CO2), A5-09-05 (VOC), A5-20-01 (radiator valve), D2-01-xx (on/off, dimmer, metering plug), D2-05-00 (roller shutter).

Once a sheet exists for your device: **Information → Change sheet**, no re-pairing needed.

## 2. Identify the device with the radio log

Open **Add a device** and make the device transmit. With a full teach-in (UTE, or 4BS with profile), Ocean2MQTT shows **"This device looks like"** and lists it among **heard transmitters** with its ID, manufacturer code and profile. Otherwise, open **Telegrams**, filter on the device ID and look at the **RORG** (`F6` RPS, `D5` 1BS, `A5` 4BS, `D2` VLD, `D4` UTE) and the data sent for each action. **Export to CSV**.

An RPS switch (F6-02-01) sends neither its brand nor its reference: use the generic 2-rocker switch.

## 3. Submit a device sheet

Easiest: check the **[online catalogue](https://ehomelabs.github.io/Ocean2MQTT/)**, then click **Suggest a new EnOcean device** (in the catalogue, or in Ocean2MQTT: **Add a device** → last tile; for a heard but unknown transmitter, **Suggest this device** pre-fills its profile and manufacturer code). The [form](https://github.com/eHomeLabs/Ocean2MQTT/issues/new?template=nouveau-produit.yml) asks for brand, reference, names, type, EEP, pairing steps, picture… Once approved by the maintainer, the sheet is created automatically in a pull request and the device appears in the next version (free GitHub account required).

Contributors: one YAML file `produits/<brand>/<reference>.yaml` + a square transparent PNG picture (400 × 400 px recommended). Keys are in French: see the example and field list on the [French page](Ajouter-un-produit-non-support%C3%A9#pour-les-contributeurs--la-fiche-yaml) and [`produits/schema.json`](https://github.com/eHomeLabs/Ocean2MQTT/blob/main/produits/schema.json). Check with `python -m ocean2mqtt.library` and `pytest`, then open a pull request. New sheets are **Community**; they become **Validated** after a real-device test report.

## 4. Request a new EEP profile

[Open a "New device" issue](https://github.com/eHomeLabs/Ocean2MQTT/issues/new?template=nouveau-produit.yml) with the EEP profile, the **CSV export of telegrams** (noting what you did for each one) and the manufacturer datasheet if possible.
