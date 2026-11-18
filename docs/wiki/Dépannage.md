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

## Clé EnOcean HS ou remplacée : ne pas tout réappairer

Les actionneurs (modules, prises, volets) ont appris l'**adresse d'émission** de la clé, calculée à partir de son **Base ID**. Avec une nouvelle clé, ils ne la reconnaissent plus… sauf si vous lui donnez le Base ID de l'ancienne.

1. Branchez la nouvelle clé et démarrez Ocean2MQTT : il détecte le changement et affiche « Nouvelle clé EnOcean détectée ».
2. Cliquez sur **Reprendre le Base ID … sur cette clé** (ou **Réglages → Clé EnOcean → Changer le Base ID** et saisissez l'ancien Base ID).
3. Confirmez : les actionneurs répondent à nouveau, sans réappairage.

L'ancien Base ID est mémorisé par Ocean2MQTT ; il figure aussi dans vos **sauvegardes** et dans l'**export NodOcean**. Pensez-y si la machine elle-même est perdue.

⚠️ À savoir :
- le Base ID d'une clé ne peut être changé qu'un **nombre limité de fois** (10, affiché dans Réglages), sans remise à zéro possible ;
- il doit être compris entre `FF800000` et `FFFFFF80`, par pas de `80` ;
- **n'utilisez jamais deux clés avec le même Base ID** en même temps : jetez ou mettez de côté l'ancienne ;
- l'**identifiant de la puce** (Chip ID) ne peut pas être copié : seuls les appairages par Base ID (ceux d'Ocean2MQTT et de NodOcean) sont repris.

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
