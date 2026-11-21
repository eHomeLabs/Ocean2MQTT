**Français** · [English](Home-EN)

# Ocean2MQTT

Ocean2MQTT est une passerelle **EnOcean ↔ MQTT** multimarque, façon Zigbee2MQTT. Elle pilote une clé USB EnOcean (USB 300, USB 500…), propose une bibliothèque de produits avec la procédure d'appairage de chacun et publie les produits dans MQTT, avec la découverte automatique de Home Assistant.

> Version stable : 0.2.2. Consultez le niveau de support de chaque fiche produit : Validé, Communauté ou Générique.

## Par où commencer

1. [[Installation]] : add-on Home Assistant, Docker ou Python.
2. [[Premiers pas]] : appairer un produit, le renommer, le retrouver dans Home Assistant.
3. Votre produit n'est pas dans la liste ? → **[[Ajouter un produit non supporté]]**.

**[Catalogue en ligne des produits compatibles](https://ehomelabs.github.io/Ocean2MQTT/)** · **[Proposer un nouveau produit EnOcean](https://github.com/eHomeLabs/Ocean2MQTT/issues/new?template=nouveau-produit.yml)**

## Pour aller plus loin

- [[Remote Commissioning]] : réglages à distance des produits NodOn (ReMan / ReCom), codes de sécurité.
- [[Migration depuis NodOcean]] : reprendre les produits de NodOcean for HA sans les réappairer.
- [[MQTT et API]] : topics, commandes, requêtes.
- [[Dépannage]] : clé introuvable, produit qui ne répond pas, journal radio.

## Produits

La bibliothèque compte les produits NodOn (validés sur produit réel) et des produits Ubiwizz, ainsi qu'un **mode générique** par profil EEP pour tout produit EnOcean standard. Liste à jour : [README](https://github.com/eHomeLabs/Ocean2MQTT#produits) ou dossier [`produits/`](https://github.com/eHomeLabs/Ocean2MQTT/tree/main/produits).

Projet eHomeLabs, licence GPL v3 (GPL-3.0-only). Ocean2MQTT est un projet indépendant.
