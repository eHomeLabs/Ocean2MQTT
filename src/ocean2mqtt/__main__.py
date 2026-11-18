"""Lancement : ocean2mqtt [--data DOSSIER] [--port /dev/ttyUSB0] [--verbose]."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
from pathlib import Path

from . import __version__
from .app import Ocean2MQTT
from .config import Config

_LOGGER = logging.getLogger("ocean2mqtt")


async def run(config: Config) -> None:
    app = Ocean2MQTT(config)
    await app.start()
    services = []
    if config["mqtt"]["enabled"]:
        from .mqtt import MqttBridge, restart_bridge

        app.mqtt_bridge = MqttBridge(app)
        app.mqtt_restart = lambda: restart_bridge(app)
    if config["frontend"]["enabled"]:
        from .web import WebServer

        services.append(WebServer(app))
    if app.mqtt_bridge is not None:
        await app.mqtt_bridge.start()
    for service in services:
        await service.start()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # Windows
            pass
    await stop.wait()
    _LOGGER.info("Arrêt d'Ocean2MQTT…")
    await app.stop()
    if app.mqtt_bridge is not None:
        await app.mqtt_bridge.stop()
    for service in reversed(services):
        await service.stop()


def main() -> None:
    parser = argparse.ArgumentParser(prog="ocean2mqtt", description="Passerelle EnOcean <-> MQTT")
    parser.add_argument("--data", default=os.environ.get("OCEAN2MQTT_DATA", "data"),
                        help="dossier de configuration et des produits appairés")
    parser.add_argument("--port", help="port série de la clé EnOcean (ex. /dev/ttyUSB0)")
    parser.add_argument("--verbose", "-v", action="store_true", help="journal détaillé")
    parser.add_argument("--version", action="version", version=f"Ocean2MQTT {__version__}")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s : %(message)s",
    )
    config = Config(Path(args.data)).load()
    if args.port:
        config.data["serial"]["port"] = args.port
    _LOGGER.info("Ocean2MQTT %s, données : %s", __version__, config.data_dir.resolve())
    asyncio.run(run(config))


if __name__ == "__main__":
    main()
