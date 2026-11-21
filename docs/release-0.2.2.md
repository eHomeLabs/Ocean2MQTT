# Ocean2MQTT 0.2.2

- Public FR/EN catalog, generated from actual library sheets and generic EEPs.
  Search by brand/model/EEP, family and support filters, pairing steps,
  capabilities, manuals, contribution links and shareable product links.
- UI update banner compares the installed UI version to the running service.
  A read-only version endpoint, polled every minute and on app resume, bypasses
  browser caching. Reload is user-triggered to preserve unsaved forms.
  HTML entry points disable caching; hashed assets remain reusable.
  Existing older interfaces must load this version once before they can use the banner.
- Identify a generic device locally: brand, exact model, photo/manual links and
  tested pairing instructions. Stored with the device and retained after restart.
  The EEP, device topic and commands remain unchanged. Test reports use these
  details without automatically declaring the generic profile validated.
- Device diagnostics show availability, last seen, observed signal and intervals,
  last known values and recent telegrams. Radio statistics cover only the current
  recent-history buffer.
- Received application telegrams show decoded measurements/states, using the
  device's existing decoder and an exposed-field allowlist. Outgoing commands,
  Remote Management and unknown devices are not interpreted as sensor readings.
  CSV export includes decoded values.

The public catalog does not include installation data. Product photo links supplied
for contributions require maintainer review before publication.
