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

## Example: react to illuminance

In Home Assistant, add this YAML automation (replace the topic and light entity):

```yaml
alias: Turn on the entrance light when it gets dark
triggers:
  - trigger: mqtt
    topic: ocean2mqtt/entrance_sensor
conditions:
  - condition: template
    value_template: >-
      {{ trigger.payload_json is mapping
         and is_number(trigger.payload_json.get('illuminance'))
         and (trigger.payload_json['illuminance'] | float) < 50 }}
actions:
  - action: light.turn_on
    target:
      entity_id: light.entrance
```

Use the device topic shown in Ocean2MQTT instead of `ocean2mqtt/entrance_sensor`,
including your configured MQTT prefix. Replace `light.entrance` with your light
entity and `50` with your threshold in lux. The device must publish the
`illuminance` measurement. The automation runs on every qualifying update;
it does not switch the light off when brightness increases.
