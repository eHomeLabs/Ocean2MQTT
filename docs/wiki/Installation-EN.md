[Français](Installation) · **English**

# Installation

You need an **EnOcean USB stick** (USB 300, USB 500 or any ESP3 stick), an **MQTT broker** (Mosquitto) and, for Home Assistant, the **MQTT** integration.

> ⚠️ A stick can only be used by **one program** at a time. Disable NodOcean for HA or any other EnOcean integration using it first.

## Home Assistant OS / Supervised: the add-on

[![Add the repository to Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FeHomeLabs%2Fhassio-ocean2mqtt)

1. Click the button (or **Settings → Apps → Store → ⋮ → Repositories** and add `https://github.com/eHomeLabs/hassio-ocean2mqtt`).
2. Install **Ocean2MQTT** from the store.
3. Install and start the official **Mosquitto broker** add-on if needed; Ocean2MQTT finds it automatically.
4. **Configuration** tab: pick your EnOcean stick.
5. Start the add-on and open **Ocean2MQTT** from the sidebar.

Architectures: amd64, aarch64 (64-bit Raspberry Pi 4 / 5).

## Docker

```bash
docker run -d --name ocean2mqtt --restart unless-stopped \
  -v $(pwd)/data:/app/data -p 8080:8080 \
  --device /dev/ttyUSB0:/dev/ttyUSB0 \
  -e OCEAN2MQTT_SERIAL_PORT=/dev/ttyUSB0 \
  -e OCEAN2MQTT_MQTT_HOST=192.168.1.10 \
  ghcr.io/ehomelabs/ocean2mqtt:latest
```

See [`docker-compose.example.yml`](https://github.com/eHomeLabs/Ocean2MQTT/blob/main/docker-compose.example.yml). Web interface: `http://<host>:8080`.

## Python

Python 3.12+: download the `.whl` file of the latest [release](https://github.com/eHomeLabs/Ocean2MQTT/releases), `pip install ocean2mqtt-<version>-py3-none-any.whl`, then `ocean2mqtt --data ./data`.

## Configuration

`data/configuration.yaml` is created on first start. Every key can be set with `OCEAN2MQTT_<SECTION>_<KEY>` environment variables (`OCEAN2MQTT_SERIAL_PORT`, `OCEAN2MQTT_MQTT_HOST`, `OCEAN2MQTT_RECOM_ENABLED`, `OCEAN2MQTT_FRONTEND_PASSWORD`…).

Demo without hardware: `python tools/demo.py`.
