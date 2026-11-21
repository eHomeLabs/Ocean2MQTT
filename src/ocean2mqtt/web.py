"""Serveur de l'interface web : fichiers statiques + WebSocket (même API que MQTT).

Messages WebSocket (JSON), comme Zigbee2MQTT :
- serveur -> navigateur : {"topic": "bridge/devices", "payload": [...]}, états des produits…
- navigateur -> serveur : {"topic": "bridge/request/pairing/start",
                           "payload": {"product": "nodon/sin-2-fp-01", "transaction": 3}}
  réponse : {"topic": "bridge/response/pairing/start",
             "payload": {"status": "ok", "data": {...}, "transaction": 3}}
- commande d'un produit : {"topic": "<produit>/set", "payload": {"state": "ON"}}
"""

from __future__ import annotations

import asyncio
import base64
import hmac
import ipaddress
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aiohttp import WSMsgType, web

from . import __version__

if TYPE_CHECKING:
    from .app import Ocean2MQTT

_LOGGER = logging.getLogger(__name__)

STATIC = Path(__file__).parent / "frontend"

PLACEHOLDER = """<!doctype html><html lang="fr"><meta charset="utf-8"><title>Ocean2MQTT</title>
<body style="font-family:sans-serif;padding:40px;color:#0B2E4A">
<h1>Ocean2MQTT</h1><p>Le service fonctionne, mais l'interface web n'est pas construite.
Lancez <code>npm run build</code> dans <code>frontend/</code>.</p></body></html>"""


def _is_local(remote: str | None) -> bool:
    try:
        ip = ipaddress.ip_address((remote or "").split("%")[0])
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local


class WebServer:
    def __init__(self, app: Ocean2MQTT) -> None:
        self.app = app
        self.settings = app.config["frontend"]
        self.clients: set[web.WebSocketResponse] = set()
        self._runner: web.AppRunner | None = None
        self._unsub = None

    def build(self) -> web.Application:
        server = web.Application(middlewares=[self._guard])
        server.router.add_get("/api", self._websocket)
        server.router.add_get("/api/version", self._version)
        server.router.add_get("/index.html", self._index)
        server.router.add_get("/produits/{brand}/{name}", self._product_image)
        server.router.add_get("/", self._index)
        if STATIC.is_dir():
            server.router.add_static("/", STATIC, follow_symlinks=False)
        return server

    async def start(self) -> None:
        self._unsub = self.app.subscribe(self._on_emit)
        self._runner = web.AppRunner(self.build(), access_log=None)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.settings["host"], int(self.settings["port"]))
        await site.start()
        _LOGGER.info("Interface web sur http://%s:%s", self.settings["host"],
                     self.settings["port"])

    async def stop(self) -> None:
        if self._unsub:
            self._unsub()
        for ws in list(self.clients):
            await ws.close()
        if self._runner:
            await self._runner.cleanup()

    # -- Sécurité ------------------------------------------------------------

    @web.middleware
    async def _guard(self, request: web.Request, handler):
        if not self.settings.get("allow_remote") and not _is_local(request.remote):
            raise web.HTTPForbidden(text="Ocean2MQTT : accès limité au réseau local")
        password = self.settings.get("password")
        if password:
            header = request.headers.get("Authorization", "")
            ok = False
            if header.startswith("Basic "):
                try:
                    _, _, given = base64.b64decode(header[6:]).decode().partition(":")
                    ok = hmac.compare_digest(given, str(password))
                except ValueError:
                    ok = False
            if not ok:
                raise web.HTTPUnauthorized(headers={"WWW-Authenticate": 'Basic realm="Ocean2MQTT"'})
        return await handler(request)

    # -- Pages ---------------------------------------------------------------

    async def _version(self, _request: web.Request) -> web.Response:
        return web.json_response({"version": __version__}, headers={"Cache-Control": "no-store"})

    async def _index(self, _request: web.Request) -> web.StreamResponse:
        index = STATIC / "index.html"
        if index.is_file():
            return web.FileResponse(index, headers={"Cache-Control": "no-store, max-age=0"})
        return web.Response(text=PLACEHOLDER, content_type="text/html",
                            headers={"Cache-Control": "no-store"})

    async def _product_image(self, request: web.Request) -> web.StreamResponse:
        root = self.app.library.root
        path = (root / request.match_info["brand"] / request.match_info["name"]).resolve()
        if root.resolve() not in path.parents or path.suffix not in (".png", ".jpg", ".webp"):
            raise web.HTTPNotFound()
        if not path.is_file():
            raise web.HTTPNotFound()
        return web.FileResponse(path, headers={"Cache-Control": "max-age=86400"})

    # -- WebSocket -----------------------------------------------------------

    async def _websocket(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)
        self.clients.add(ws)
        try:
            for topic, payload in list(self.app.retained.items()):
                await ws.send_str(json.dumps({"topic": topic, "payload": payload},
                                             ensure_ascii=False))
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await self._handle(ws, msg.data)
        finally:
            self.clients.discard(ws)
        return ws

    async def _handle(self, ws: web.WebSocketResponse, text: str) -> None:
        from .app import RequestError

        try:
            msg = json.loads(text)
            topic = str(msg["topic"])
            payload = msg.get("payload") or {}
        except (ValueError, KeyError, TypeError):
            return
        if topic.startswith("bridge/request/"):
            command = topic.removeprefix("bridge/request/")
            data = dict(payload) if isinstance(payload, dict) else {"value": payload}
            transaction = data.pop("transaction", None)
            try:
                result: dict[str, Any] = {"status": "ok",
                                          "data": await self.app.request(command, data)}
            except RequestError as err:
                result = {"status": "error", "error": str(err)}
            except Exception as err:
                _LOGGER.exception("Requête %s", command)
                result = {"status": "error", "error": f"Erreur interne : {err}"}
            if transaction is not None:
                result["transaction"] = transaction
            await ws.send_str(json.dumps({"topic": f"bridge/response/{command}",
                                          "payload": result}, ensure_ascii=False))
            return
        name, _, verb = topic.rpartition("/")
        device = self.app.device_by_topic(name)
        if device is not None and verb == "set":
            try:
                await self.app.request("device/set", {"id": device.id_str, "payload": payload})
            except RequestError as err:
                await ws.send_str(json.dumps({"topic": "bridge/event", "payload": {
                    "type": "error", "data": {"message": str(err)}}}, ensure_ascii=False))

    def _on_emit(self, topic: str, payload: Any, _retain: bool) -> None:
        if not self.clients:
            return
        text = json.dumps({"topic": topic, "payload": payload}, ensure_ascii=False)
        for ws in list(self.clients):
            if not ws.closed:
                asyncio.get_running_loop().create_task(ws.send_str(text))
