[Français](Remote-Commissioning) · **English**

# Remote Commissioning

**Remote Commissioning** (EnOcean Remote Management, "ReMan / ReCom") lets you configure a device remotely: read and edit its linked remotes, read shutter parameters… Supported by NodOn modules.

## Security code

- **Without a code**, the device only accepts remote commands during the **5 minutes after it is powered on**.
- **With a code**, it accepts them at any time once unlocked with the code. An unlock lasts 5 minutes; Ocean2MQTT sends the code again after 4 minutes when needed.

At pairing (or later, within 5 minutes of a power-up) choose:
- **Automatic code** (recommended): derived from the device ID and a **secret unique to your installation**; always the same, impossible to guess, recoverable from the backup;
- **Entered code**: the QR code (`11Z…`) or your own (8 hex characters);
- **No code**.

Device already has a code? Enter it, or **Detect the code** (tries the stored, automatic and entered codes). **Lost code?** Factory-reset the device (NodOn: press the button for about **8 s**, release, then **press briefly**), pair it again and choose a code.

## Security

Remote Management is **not encrypted**: the code is sent in clear over the air when unlocking. Ocean2MQTT only sends it on your action, **asks for confirmation** each time, never shows it, and can **disable Remote Commissioning entirely** (add-on option or `recom.enabled: false`). Backups and `devices.json` contain the codes: keep them safe.
