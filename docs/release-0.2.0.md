# Ocean2MQTT 0.2.0 — stable release preparation

## Release notes

First stable release of the multi-brand EnOcean ↔ MQTT gateway, following
0.2.0b28. Available as a Home Assistant add-on, Docker image (amd64 / arm64)
and Python package.

- Guided pairing, device controls and settings, live telegrams and MQTT discovery.
- NodOcean migration, backup/restore and Remote Commissioning.
- French and English web interface with card and table device views.
- A5-04-03 temperature and humidity support; GPL v3 displayed in About.
- Product support remains specific to each entry: Validated, Community or Generic.
  Stable software does not mean that all catalog devices have been hardware-tested.

## Upgrade

1. Export an Ocean2MQTT backup; also back up Home Assistant for an add-on install.
2. Keep the same data directory / add-on slug and EnOcean stick.
3. Install 0.2.0 and check paired devices, MQTT discovery, measurements and one
   actuator command. Existing device identifiers and topics must be preserved.
4. To roll back, stop the service, install the previous exact version and restore
   the backup if needed. Do not run two services against the same stick.

## Publication order

1. Merge photo-permission PR #18 before tagging the stable release. Preserve
   existing photos, as requested by the maintainer. Image provenance follow-up
   remains tracked in #16.
2. Merge the stable preparation PR after Python 3.12 / 3.13, frontend build,
   package checks, and upgrades from published b27 and b28 pass.
3. Create GitHub release `v0.2.0` on the validated main commit, with pre-release
   disabled and these release notes. The tag must match `pyproject.toml`.
4. Wait for the Docker workflow: exact tag `v0.2.0` and channel `latest`,
   amd64 and arm64 images, and `ocean2mqtt-0.2.0-py3-none-any.whl` attached
   to the GitHub release. `main` continues to publish `edge`.
5. Only then merge the companion `hassio-ocean2mqtt` stable PR, because its
   Dockerfile downloads that exact published wheel. Check both add-on builds
   before updating the Home Assistant installation.
6. Synchronize the checked-in wiki sources to the GitHub wiki if published
   separately.

## Remaining hardware follow-up

FAH60 pairing on a second installation is tracked in #14. Automated checks use
a simulated USB stick; they do not replace that independent hardware test.
