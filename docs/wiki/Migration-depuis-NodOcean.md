**Français** · [English](Migrating-from-NodOcean)

# Migration depuis NodOcean for HA

Ocean2MQTT reprend vos produits NodOcean **sans les réappairer** : noms, pièces, adresses d'émission des actionneurs et codes Remote Commissioning.

## Avec l'add-on (même Home Assistant)

1. Gardez la **même clé EnOcean** : vos actionneurs la reconnaissent.
2. Installez l'add-on Ocean2MQTT (voir [[Installation]]).
3. **Désactivez NodOcean for HA** : Paramètres → Appareils et services → NodOcean for HA → ⋮ → Désactiver. Une clé ne peut servir qu'à un seul logiciel.
4. Démarrez Ocean2MQTT : le bandeau **« NodOcean for HA détecté »** lance l'assistant (aussi dans **Réglages → Migration et sauvegarde**).
5. Choisissez :
   - **même clé** (recommandé) : tout est repris ;
   - **autre clé** : les capteurs sont repris, les actionneurs gardent leur nom et sont à réappairer ;
   - **installation vierge**.
6. Vérifiez l'aperçu (fiche de chaque produit, en particulier pour les produits génériques de NodOcean) et importez.

## Ocean2MQTT sur une autre machine (Docker…)

Dans NodOcean for HA 0.8.6 ou plus : appareil **Clé EnOcean** → bouton **Exporter pour Ocean2MQTT**. Le fichier `nodocean_export_ocean2mqtt.json` est écrit dans le dossier de configuration de Home Assistant. Récupérez-le (Samba, File editor…) et importez-le dans **Réglages → Migration et sauvegarde → Importer un fichier**.

⚠️ Ce fichier contient les codes Remote Commissioning de vos produits : ne le partagez pas.

## Depuis une autre box (Jeedom…) avec la même clé

Un actionneur obéit à l'**adresse d'émission** qu'il a apprise : le Base ID de la clé plus un décalage de 0 à 127 (ex. clé `FFE56B80` → adresses `FFE56B80` à `FFE56BFF`). En gardant la même clé, Ocean2MQTT peut réutiliser l'adresse de chaque actionneur, sans nouvel appairage :

1. Arrêtez l'autre box et branchez sa clé sur Ocean2MQTT (ou donnez son Base ID à une nouvelle clé : **Réglages → Clé EnOcean → Changer le Base ID**).
2. **Ajouter un produit** → fiche de l'actionneur → **« Pas d'accès au bouton d'apprentissage ? »** → **« Déjà appairé avec une autre box ? »**.
3. Saisissez l'identifiant de l'actionneur et l'**adresse d'émission** que l'autre box utilisait pour lui, puis **Déclarer l'actionneur**.

Où trouver cette adresse : configuration de l'équipement ou logs (mode debug) du plugin EnOcean de l'autre box ; pour un module NodOn avec Remote Commissioning, **Lire la table** des télécommandes (onglet Remote Commissioning, juste après une remise sous tension) ; ou la page **Télégrammes** d'Ocean2MQTT avec une deuxième clé pendant que l'autre box commande l'actionneur.

Limite : si l'autre box a appairé l'actionneur avec l'identifiant de la puce de la clé (adresse hors de la plage du Base ID), il faut le réappairer.

## Après la migration

Les entités de NodOcean sont remplacées par les **entités MQTT** d'Ocean2MQTT : mettez à jour vos automatisations et tableaux de bord, puis supprimez l'intégration NodOcean. L'historique (énergie notamment) reste attaché aux anciennes entités.
