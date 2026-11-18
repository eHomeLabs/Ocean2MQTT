**Français** · [English](Troubleshooting)

# Dépannage

## « Clé EnOcean non connectée »
- Vérifiez le port choisi (add-on : onglet Configuration ; Docker : `--device` et `OCEAN2MQTT_SERIAL_PORT`).
- Une clé ne sert qu'à **un seul logiciel** : NodOcean for HA, une autre intégration EnOcean ou un autre conteneur l'utilisent peut-être.
- Ocean2MQTT réessaie toutes les 15 secondes : rebranchez la clé si besoin.

## Le produit n'est pas reconnu à l'appairage
- Respectez la procédure de la fiche et lancez l'appairage **avant** d'appuyer sur le bouton du produit.
- Rapprochez le produit de la clé pour l'appairage.
- Regardez la page **Télégrammes** : si rien n'arrive, le produit n'émet pas (pile, portée) ; si des télégrammes arrivent, voir [[Ajouter un produit non supporté]].

## Un actionneur ne répond plus
- A-t-il été appairé avec une autre clé ? Ocean2MQTT signale « à réappairer » quand la clé a changé.
- Coupez et remettez le courant du module ; Ocean2MQTT interroge les actionneurs toutes les 60 secondes.

## Pas de puissance / énergie
Ocean2MQTT règle le rapport automatique des mesures à l'appairage et au démarrage, puis interroge les actionneurs toutes les 60 secondes. Vérifiez dans **Télégrammes** que le produit répond.

## Remote Commissioning en échec
- Sans code : le produit n'accepte les commandes que **5 minutes après sa mise sous tension**.
- Avec un code : **Détecter le code** (volet « Le produit a déjà un code ? »), ou reset usine (NodOn : appui d'environ 8 s, relâcher, appui bref). Voir [[Remote Commissioning]].

## Rien dans Home Assistant
- L'intégration **MQTT** doit être configurée et la découverte activée.
- Journal de l'add-on : niveau `debug` pour voir toutes les trames.

## Signaler un problème
[Ouvrez une issue](https://github.com/eHomeLabs/Ocean2MQTT/issues) avec la version, le produit, le journal (niveau `debug`) et l'export CSV des télégrammes.
