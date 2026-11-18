[Français](D%C3%A9pannage) · **English**

# Troubleshooting

- **"EnOcean stick not connected"**: check the port; a stick can only be used by **one program** (NodOcean for HA, another integration or container?). Ocean2MQTT retries every 15 s.
- **Device not recognised at pairing**: start pairing **before** pressing the device button, move it closer, check the **Telegrams** page; see [[Adding an unsupported device]].
- **Broken or replaced stick**: Ocean2MQTT detects the new stick; click **Take over Base ID … on this stick** (or Settings → EnOcean stick → Change the Base ID) to write the old Base ID into the new stick: actuators answer again without re-pairing. Limited number of writes per stick (10), range `FF800000`–`FFFFFF80` in steps of `80`, never two sticks with the same Base ID in service.
- **Actuator no longer responds**: was it paired with another stick? Power-cycle it; actuators are polled every 60 s.
- **No power / energy**: check in **Telegrams** that the device answers.
- **Remote Commissioning fails**: without a code, only within **5 minutes of power-up**; with a code, **Detect the code** or factory-reset (NodOn: ~8 s press, release, short press).
- **Nothing in Home Assistant**: the **MQTT** integration must be set up with discovery on; use log level `debug`.

[Open an issue](https://github.com/eHomeLabs/Ocean2MQTT/issues) with version, device, `debug` log and the telegrams CSV export.
