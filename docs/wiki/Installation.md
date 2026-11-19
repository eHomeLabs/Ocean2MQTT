**Français** · [English](Installation-EN)

# Installation

Il faut :
- une **clé USB EnOcean** (USB 300, USB 500 ou compatible ESP3) ;
- un **serveur MQTT** (Mosquitto) ;
- Home Assistant avec l'intégration **MQTT** si vous voulez y retrouver vos produits.

> ⚠️ Une clé EnOcean ne peut être utilisée que par **un seul logiciel** à la fois. Si NodOcean for HA ou une autre intégration utilise la clé, désactivez-la d'abord (voir [[Migration depuis NodOcean]]).

## Home Assistant OS / Supervised : l'add-on

[![Ajouter le dépôt à Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FeHomeLabs%2Fhassio-ocean2mqtt)

1. Cliquez sur le bouton ci-dessus. Sans le bouton : **Paramètres → Applications → Boutique → ⋮ → Dépôts**, ajoutez `https://github.com/eHomeLabs/hassio-ocean2mqtt`.
2. Rafraîchissez la boutique et installez **Ocean2MQTT**.
3. Installez et démarrez l'add-on officiel **Mosquitto broker** si ce n'est pas déjà fait, et activez l'intégration **MQTT**. Ocean2MQTT récupère tout seul l'adresse et les identifiants de Mosquitto.
4. Onglet **Configuration** : choisissez la **clé EnOcean** dans la liste.
5. Démarrez l'add-on et ouvrez **Ocean2MQTT** dans la barre latérale.

Options de l'add-on : nom des topics (`name` ou `id`), niveau du journal, Remote Commissioning (activé / désactivé, réglable aussi dans **Réglages → Remote Commissioning**, qui l'emporte), serveur MQTT externe et mot de passe de l'accès direct (port 8080) facultatifs.

Architectures : amd64 et aarch64 (Raspberry Pi 4 / 5 en 64 bits).

## Docker

```bash
docker run -d --name ocean2mqtt --restart unless-stopped \
  -v $(pwd)/data:/app/data -p 8080:8080 \
  --device /dev/ttyUSB0:/dev/ttyUSB0 \
  -e OCEAN2MQTT_SERIAL_PORT=/dev/ttyUSB0 \
  -e OCEAN2MQTT_MQTT_HOST=192.168.1.10 \
  ghcr.io/ehomelabs/ocean2mqtt:latest
```

Un exemple avec Mosquitto est fourni : [`docker-compose.example.yml`](https://github.com/eHomeLabs/Ocean2MQTT/blob/main/docker-compose.example.yml). Interface : `http://<machine>:8080`.

Conseil : utilisez le chemin stable de la clé (`/dev/serial/by-id/usb-EnOcean_GmbH_…`) plutôt que `/dev/ttyUSB0`.

## Python

Python 3.12 ou plus :

```bash
# fichier .whl de la dernière release : https://github.com/eHomeLabs/Ocean2MQTT/releases
pip install ocean2mqtt-<version>-py3-none-any.whl
ocean2mqtt --data ./data
```

## Configuration

Le fichier `data/configuration.yaml` est créé au premier lancement. Chaque réglage peut être passé en variable d'environnement `OCEAN2MQTT_<SECTION>_<CLÉ>` :

| Variable | Rôle |
| --- | --- |
| `OCEAN2MQTT_SERIAL_PORT` | Port de la clé EnOcean |
| `OCEAN2MQTT_MQTT_HOST`, `_PORT`, `_USERNAME`, `_PASSWORD` | Serveur MQTT |
| `OCEAN2MQTT_MQTT_TOPIC_NAME` | `name` (ocean2mqtt/Salon) ou `id` |
| `OCEAN2MQTT_RECOM_ENABLED` | `false` pour désactiver le Remote Commissioning |
| `OCEAN2MQTT_FRONTEND_PASSWORD` | Mot de passe de l'interface web |

Le **serveur MQTT** et les **topics** se modifient aussi dans l'interface (**Réglages → Serveur MQTT → Modifier**, avec un bouton pour tester la connexion). Une valeur enregistrée dans l'interface l'emporte sur la variable d'environnement ou le réglage automatique de l'add-on ; « Revenir au serveur automatique » annule ce choix.

L'interface web n'accepte que les adresses du réseau local (`frontend.allow_remote` pour changer).

## Essayer sans clé

`python tools/demo.py` lance une démo avec une clé et des produits simulés : `http://127.0.0.1:8080`.
