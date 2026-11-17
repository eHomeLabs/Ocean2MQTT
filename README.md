<p align="center">
  <img src="docs/logo/ocean2mqtt-logo.svg" alt="Ocean2MQTT" width="420">
</p>

<p align="center"><strong>Passerelle EnOcean ↔ MQTT multi-marques</strong> · <em>Multi-brand EnOcean ↔ MQTT gateway</em></p>

---

> 🧪 **Version alpha (0.1.0a1)** — à tester, pas encore pour une installation en production.
> **Alpha release** — for testing, not yet for production use.

## Français

Ocean2MQTT fait pour EnOcean ce que Zigbee2MQTT fait pour Zigbee : une clé USB, une interface web, et tous vos produits EnOcean publiés sur MQTT, quelle que soit leur marque.

- **Bibliothèque de produits** : vous choisissez votre produit (par marque, type ou EEP), Ocean2MQTT affiche sa photo et sa procédure d'appairage, puis répond automatiquement.
- **Mode générique** pour les produits absents de la bibliothèque.
- **Pont MQTT** compatible Home Assistant (découverte automatique), Jeedom, Node-RED, openHAB…
- **Réglages et Remote Commissioning** des produits qui le gèrent.
- **Contributions ouvertes** : un produit = une fiche YAML + une photo, sans écrire de code.

Clés prises en charge : clés ESP3 en USB ou série (USB300, USB500, TCM310 / EnOcean Pi).

Ocean2MQTT s'appuie sur le code de [NodOcean for HA](https://github.com/eHomeLabs/NodOcean-for-HA), validé sur produits réels.

### Démarrage rapide

**Docker** (amd64, arm64 — Raspberry Pi 4 / 5 en 64 bits) :

```bash
docker run -d --name ocean2mqtt --restart unless-stopped \
  -v $(pwd)/data:/app/data -p 8080:8080 \
  --device /dev/ttyUSB0:/dev/ttyUSB0 \
  -e OCEAN2MQTT_MQTT_HOST=192.168.1.10 \
  ghcr.io/ehomelabs/ocean2mqtt:edge
```

Exemple avec Mosquitto : `docker-compose.example.yml`. Ouvrez ensuite `http://<machine>:8080`.

**Python** (3.12 ou plus) : `pip install .` puis `ocean2mqtt --data ./data --port /dev/ttyUSB0`.

**Sans clé EnOcean** (démo, clé simulée) : `python tools/demo.py`, puis `http://127.0.0.1:8080`.

La configuration est dans `data/configuration.yaml` (créée au premier lancement) ; chaque réglage peut aussi être passé en variable d'environnement : `OCEAN2MQTT_SERIAL_PORT`, `OCEAN2MQTT_MQTT_HOST`, `OCEAN2MQTT_MQTT_USERNAME`, `OCEAN2MQTT_FRONTEND_PASSWORD`… L'interface web n'accepte que les adresses du réseau local (`frontend.allow_remote` pour changer).

### MQTT

| Topic | Contenu |
| --- | --- |
| `ocean2mqtt/bridge/state` | `online` / `offline` |
| `ocean2mqtt/bridge/info`, `bridge/devices` | Passerelle, produits appairés (JSON) |
| `ocean2mqtt/bridge/request/<commande>` | Requêtes, réponse sur `bridge/response/<commande>` : `devices`, `library`, `pairing/start` (`{"product": "nodon/sin-2-fp-01"}`), `pairing/stop`, `device/rename`, `device/remove`, `device/set`, `device/get` |
| `ocean2mqtt/<produit>` | État JSON (ex. `{"mode": "eco", "power": 610}`) |
| `ocean2mqtt/<produit>/set` | Commande (ex. `{"mode": "comfort"}`, `ON`, `{"position": 50}`, `{"setpoint": 21}`) |
| `ocean2mqtt/<produit>/action` | Appuis de boutons |

La découverte automatique Home Assistant est activée par défaut (préfixe `homeassistant`).

### Organisation du dépôt

| Dossier | Contenu |
| --- | --- |
| `src/ocean2mqtt/core/` | Cœur radio : clé ESP3, profils EEP, appairage, Remote Commissioning (sans Home Assistant ni MQTT) |
| `src/ocean2mqtt/library/` | Chargement et contrôle des fiches produits |
| `src/ocean2mqtt/` | Service : `app.py` (API commune), `mqtt.py` (pont MQTT + découverte HA), `web.py` (interface web + WebSocket) |
| `frontend/` | Interface web (TypeScript / React), construite avec `npm run build` |
| `produits/<marque>/` | Une fiche YAML + une photo par produit (`schema.json` décrit le format) |
| `tests/` | Tests, avec une clé USB300 simulée |

Contrôler les fiches : `python -m ocean2mqtt.library` · lancer les tests : `pytest`.

## English

Ocean2MQTT does for EnOcean what Zigbee2MQTT does for Zigbee: one USB stick, a web interface, and all your EnOcean devices published to MQTT, whatever their brand.

- **Device library**: pick your device (by brand, type or EEP); Ocean2MQTT shows its picture and pairing steps, then answers automatically.
- **Generic mode** for devices not yet in the library.
- **MQTT bridge** with Home Assistant discovery; works with Jeedom, Node-RED, openHAB…
- **Settings and Remote Commissioning** for devices that support it.
- **Open contributions**: one device = one YAML file + one picture, no code needed.

## Licence / License

[MIT](LICENSE) · Projet [eHomeLabs](https://github.com/eHomeLabs).

EnOcean® est une marque déposée d'EnOcean GmbH. Ocean2MQTT est un projet indépendant, compatible EnOcean, sans lien avec EnOcean GmbH ni l'EnOcean Alliance.
EnOcean® is a registered trademark of EnOcean GmbH. Ocean2MQTT is an independent EnOcean-compatible project, not affiliated with EnOcean GmbH or the EnOcean Alliance.
