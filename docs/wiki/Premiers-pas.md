**Français** · [English](Getting-started)

# Premiers pas

## Appairer un produit

1. **Ajouter un produit** : cherchez votre produit par marque, référence ou profil EEP.
2. Ouvrez sa fiche : photo, profil, procédure d'appairage.
3. **Lancer l'appairage** : Ocean2MQTT écoute pendant le compte à rebours. Suivez la procédure affichée (appui sur le bouton du produit, mise sous tension…).
4. Une fois le produit reconnu : donnez-lui un **nom** et une **pièce**. Le topic MQTT (`ocean2mqtt/<nom>`) est affiché.
5. Pour un produit qui gère le Remote Commissioning, choisissez son **code de sécurité** (voir [[Remote Commissioning]]).

Le produit apparaît dans **Mes produits** et, dans Home Assistant, dans **Paramètres → Appareils et services → MQTT**.

### Sans accès au bouton d'apprentissage : par l'identifiant EnOcean

Pour un **capteur ou un interrupteur** (produit déjà installé, bouton inaccessible…), ouvrez sa fiche puis **« Pas d'accès au bouton d'apprentissage ? Ajouter avec l'identifiant EnOcean »** : saisissez son identifiant (8 caractères hexadécimaux, ex. `0512ABCD`, sur l'étiquette, l'emballage ou le QR code du produit, ou dans la page **Télégrammes** s'il a déjà émis). Il est reconnu dès son télégramme suivant.

Pour un **actionneur NodOn qui gère le Remote Commissioning** (SIN-2-x…), le même volet propose l'**appairage à distance** : saisissez l'identifiant du module, coupez puis remettez son courant, et cliquez sur **Appairer à distance** dans les 5 minutes. Ocean2MQTT le met en mode appairage par radio, puis l'appairage se termine comme avec le bouton. Si le module a déjà un code Remote Commissioning, saisissez-le aussi. Voir [[Remote Commissioning]].

Un actionneur **déjà appairé par une autre box avec la même clé** se déclare avec l'adresse d'émission qu'il a apprise : voir [[Migration depuis NodOcean]] (« Depuis une autre box »). Sinon, la procédure d'appairage reste nécessaire.

### Capteurs et interrupteurs déjà entendus

Ocean2MQTT écoute en permanence. Quand un émetteur inconnu envoie sa demande d'appairage, un bandeau **« Ce produit ressemble à »** propose les fiches qui correspondent (code fabricant + profil EEP). Les capteurs et interrupteurs s'ajoutent alors en un clic.

### Actionneurs (modules, prises, volets)

Un actionneur apprend l'**adresse de la clé** qui l'a appairé. Ocean2MQTT lui attribue une adresse d'émission propre (Base ID + décalage). Si vous changez de clé, il faudra le réappairer (Ocean2MQTT le détecte et vous le signale).

## La fiche d'un produit

- **Contrôle** : commandes et mesures en direct.
- **Réglages** : LED, état au retour du courant, extinction automatique, type d'interrupteur… selon le produit. Aussi modifiables par MQTT (`{"led": "OFF"}` sur `ocean2mqtt/<nom>/set`).
- **Remote Commissioning** : pour les produits NodOn qui le gèrent.
- **Télégrammes** : ce que le produit a envoyé et reçu.
- **Informations** : identifiant, topic, profil EEP, notice, **Changer de fiche** (une autre fiche du même profil, sans réappairer), renommer, retirer.

## Sauvegarde

**Réglages → Migration et sauvegarde → Télécharger une sauvegarde** : produits, noms, pièces, réglages et codes Remote Commissioning dans un fichier JSON. Gardez-le en lieu sûr : il contient les codes de sécurité de vos produits.
