**Français** · [English](MQTT-and-API)

# MQTT et API

Préfixe par défaut : `ocean2mqtt`. La découverte Home Assistant est activée par défaut (préfixe `homeassistant`).

## Topics

| Topic | Contenu |
| --- | --- |
| `ocean2mqtt/bridge/state` | `online` / `offline` |
| `ocean2mqtt/bridge/info`, `bridge/devices` | Passerelle, produits appairés (JSON) |
| `ocean2mqtt/bridge/request/<commande>` | Requêtes ; réponse sur `bridge/response/<commande>` |
| `ocean2mqtt/bridge/event` | Appairage, nouveau produit, suggestion, Remote Commissioning |
| `ocean2mqtt/bridge/unknown` | Émetteurs entendus mais pas appairés |
| `ocean2mqtt/bridge/telegrams` | Télégrammes bruts (option `mqtt.telegrams`) |
| `ocean2mqtt/<produit>` | État JSON, réglages compris |
| `ocean2mqtt/<produit>/availability` | `online` / `offline` |
| `ocean2mqtt/<produit>/set` | Commande ou réglage |
| `ocean2mqtt/<produit>/get` | Relecture de l'état |
| `ocean2mqtt/<produit>/action` | Appuis de boutons |

Exemples de commandes sur `/set` : `ON`, `{"state_l2": "OFF"}`, `{"mode": "comfort"}`, `{"position": 50}`, `{"setpoint": 21}`, `{"led": "OFF"}`, `{"auto_off_l1": 300}`.

## Requêtes

| Requête | Rôle |
| --- | --- |
| `info`, `devices`, `library`, `library/generic` | Passerelle, produits, bibliothèque, profils génériques |
| `pairing/start`, `pairing/stop` | Appairage : `{"product": "nodon/sin-2-fp-01"}` ou `{"product": "generique/a5-04-01"}` |
| `device/rename`, `device/remove`, `device/set`, `device/get` | Gestion et commande d'un produit |
| `device/settings`, `device/settings/set` | Réglages : `{"id": "…", "key": "led", "value": false}` |
| `device/compatible`, `device/change_product` | Changer de fiche sans réappairer |
| `unknown`, `unknown/clear`, `device/add` | Émetteurs inconnus, ajout en un clic |
| `device/recom/<action>`, `recom/log` | Remote Commissioning : `status`, `ping`, `assign` (`{"mode": "auto"}`), `detect`, `unlock`, `code`, `links`, `links/add`, `links/delete`, `config` |
| `migration/sources`, `migration/preview`, `migration/import` | Reprise NodOcean ou fichier |
| `backup/create` | Sauvegarde |
| `telegrams` | Derniers télégrammes |

L'interface web utilise exactement la même API par WebSocket (`/api`).
