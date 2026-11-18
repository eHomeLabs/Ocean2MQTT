[Français](MQTT-et-API) · **English**

# MQTT and API

Default prefix `ocean2mqtt`; Home Assistant discovery on by default (`homeassistant` prefix).

| Topic | Content |
| --- | --- |
| `ocean2mqtt/bridge/state` | `online` / `offline` |
| `ocean2mqtt/bridge/info`, `bridge/devices` | Gateway, paired devices |
| `ocean2mqtt/bridge/request/<command>` | Requests; answer on `bridge/response/<command>` |
| `ocean2mqtt/bridge/event` | Pairing, new device, suggestion, Remote Commissioning |
| `ocean2mqtt/bridge/unknown` | Heard but unpaired transmitters |
| `ocean2mqtt/<device>` | JSON state, settings included |
| `ocean2mqtt/<device>/set` | Command or setting (`ON`, `{"mode": "comfort"}`, `{"position": 50}`, `{"led": "OFF"}`) |
| `ocean2mqtt/<device>/get` | Refresh state |
| `ocean2mqtt/<device>/action` | Button presses |

Requests: `info`, `devices`, `library`, `pairing/start` (`{"product": "nodon/sin-2-fp-01"}`), `device/rename|remove|set|get`, `device/settings/set`, `device/change_product`, `device/recom/<action>` (`status`, `ping`, `assign`, `detect`, `unlock`, `code`, `links`…), `migration/*`, `backup/create`, `telegrams`. Full list on the [French page](MQTT-et-API). The web interface uses the same API over WebSocket (`/api`).
