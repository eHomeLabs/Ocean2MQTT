<p align="center">
  <img src="docs/logo/ocean2mqtt-logo.svg" alt="Ocean2MQTT" width="420">
</p>

<p align="center"><strong>Passerelle EnOcean ↔ MQTT multi-marques</strong> · <em>Multi-brand EnOcean ↔ MQTT gateway</em></p>

---

> 🚧 **Projet en démarrage** — rien n'est encore utilisable. Le cahier des charges est en cours de validation.
> **Early-stage project** — nothing is usable yet. The specification is being reviewed.

## Français

Ocean2MQTT fait pour EnOcean ce que Zigbee2MQTT fait pour Zigbee : une clé USB, une interface web, et tous vos produits EnOcean publiés sur MQTT, quelle que soit leur marque.

- **Bibliothèque de produits** : vous choisissez votre produit (par marque, type ou EEP), Ocean2MQTT affiche sa photo et sa procédure d'appairage, puis répond automatiquement.
- **Mode générique** pour les produits absents de la bibliothèque.
- **Pont MQTT** compatible Home Assistant (découverte automatique), Jeedom, Node-RED, openHAB…
- **Réglages et Remote Commissioning** des produits qui le gèrent.
- **Contributions ouvertes** : un produit = une fiche YAML + une photo, sans écrire de code.

Clés prises en charge : clés ESP3 en USB ou série (USB300, USB500, TCM310 / EnOcean Pi).

Ocean2MQTT s'appuie sur le code de [NodOcean for HA](https://github.com/eHomeLabs/NodOcean-for-HA), validé sur produits réels.

### Organisation du dépôt

| Dossier | Contenu |
| --- | --- |
| `src/ocean2mqtt/core/` | Cœur radio : clé ESP3, profils EEP, appairage, Remote Commissioning (sans Home Assistant ni MQTT) |
| `src/ocean2mqtt/library/` | Chargement et contrôle des fiches produits |
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
