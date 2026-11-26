# Avidsen 101012 — A5-10-12

Sonde à écran, pile CR2450 ou micro-USB 5 V. La [fiche constructeur](https://pim.avidsen.com/documentsproduits/fr/101012V1-fiche-produit.pdf) confirme le profil A5-10-12 et l’association par appui supérieur à trois secondes sur le bouton arrière. Température annoncée : 0–38 °C ; humidité : 20–90 % HR. Le rythme de mesure d’une minute ne garantit pas une émission radio chaque minute.

## Décodage

Selon la [spécification officielle EEP 2.6.8](https://www.enocean-alliance.org/wp-content/uploads/2019/10/EEP268_R3_Feb022018_public.pdf), page 56 :

| Octet | Valeur | Conversion |
| --- | --- | --- |
| DB3 | Consigne locale | `setpoint_raw`, 0–255 sans unité |
| DB2 | Humidité | 0–250 → 0–100 % |
| DB1 | Température | 0–250 → 0–40 °C, échelle croissante |
| DB0 bit 3 | LRN | 0 : apprentissage, 1 : données |

Les valeurs température/humidité 251–255 sont indisponibles. Contrairement à A5-04-01, le bit DB0.1 n’indique pas ici la présence de température. Aucun bit réservé n’est décodé.

La consigne est une **mesure reçue**, sans commande MQTT vers la sonde. Le standard ne définit pas sa correspondance en degrés. Aucune conversion arbitraire ni pilotage de chauffage n’est ajouté.

La fiche annonce la remontée radio de pile faible, mais A5-10-12 ne réserve aucun champ à cette fonction. Il faut des trames réelles et/ou une documentation Avidsen pour compléter cette extension. L’état de pile reste donc non exposé plutôt que supposé.

Support **Communauté** : à confirmer sur produit réel (teach-in, mesures, boutons +/−, pile faible). La photo est celle fournie pour l’ajout par le mainteneur. Aucune équivalence avec une autre référence Avidsen n’est supposée.
