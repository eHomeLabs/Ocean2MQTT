# Ocean2MQTT 0.2.3

Delivers the catalog, update detection, generic identification and diagnostics
described in release-0.2.2.md.

The frontend Docker stage uses BUILDPLATFORM so Node/npm compile static assets
on the native build host, without ARM emulation. The architecture-neutral assets
are copied into the separate amd64 and arm64 Python runtime images.

Also wraps long public model references on small screens and uses saved generic
photo links in the device table as well as cards/details.
