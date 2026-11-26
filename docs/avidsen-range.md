# Gamme Avidsen EnOcean

Six références ajoutées à partir des notices officielles. Les interrupteurs 600100 et 600101 sont exclus de cet ajout. Les fiches restent en **Communauté** jusqu’aux essais matériels ; les visuels génériques existants sont utilisés.

| Référence | EEP | Fonctions | Notice |
| --- | --- | --- | --- |
| 600104 | A5-04-01 | Température, humidité | https://pim.avidsen.com/documentsproduits/fr/600104-notice.pdf |
| 600102 | D5-00-01 | Contact magnétique | https://pim.avidsen.com/documentsproduits/fr/600102-notice.pdf |
| 970221 | D5-00-01 | Contact géomagnétique/magnétique | https://pim.avidsen.com/documentsproduits/fr/970221-notice.pdf |
| 600105 | D2-01-08 | Marche/arrêt, puissance, énergie | https://pim.avidsen.com/documentsproduits/fr/600105-notice.pdf |
| 600106 | D2-01-0C | Fil pilote 6 ordres, puissance, énergie | https://pim.avidsen.com/documentsproduits/fr/600106-notice.pdf |
| 970292 | D2-01-12 | Éclairage 2 sorties | https://pim.avidsen.com/documentsproduits/fr/970292-notice-v8.pdf |

Les profils et conversions sont déjà implémentés. Les demandes UTE et données des actionneurs doivent encore être contrôlées sur matériel Avidsen ; les tests logiciels utilisent les télégrammes standard du profil, pas des captures constructeur.

Aucun réglage propriétaire NodOn ni Remote Commissioning n’est activé. Le 970292 ne déclare pas de mesure électrique. Pour le 600106, la notice décrit des mesures de consommation ; la disponibilité effective doit être vérifiée sur chaque révision matérielle.

Le 970221 nécessite une calibration en position fermée pour une ouverture à battant. Le sabotage et le niveau de pile ne sont pas exposés sans codage documenté. Les fonctions Lora/Wifi des matériels à module interchangeable sont hors de cet ajout. Pour les caractéristiques électriques du 970292, la notice V8 et la fiche commerciale donnent des limites différentes : aucun seuil de puissance universel n’est intégré dans le logiciel.

Le code fabricant Avidsen est 111 (0x06F), selon le [registre EnOcean](https://enoceanwiki.atlassian.net/wiki/spaces/IEC/pages/260669482). Il sert aux suggestions ; il ne garantit pas que chaque révision émet ce même identifiant.
