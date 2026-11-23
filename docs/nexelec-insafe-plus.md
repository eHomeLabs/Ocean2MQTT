# Nexelec INSAFE+ Origin (I870EO)

Support communautaire du profil **D2-14-30**, ajouté à partir du retour de Philippe dans [l’issue #24](https://github.com/eHomeLabs/Ocean2MQTT/issues/24).

## Ajout

Dans les émetteurs inconnus, sélectionner l’identifiant du détecteur puis la fiche **Nexelec INSAFE+ Origin**. Il est également possible de l’ajouter manuellement avec son identifiant EnOcean et cette fiche. Aucune autre fiche D2-14 ne doit être utilisée comme substitut. Le télégramme périodique ordinaire ne contient pas le profil EEP : l’application ne peut pas deviner le modèle à partir de sa longueur.

Les émissions périodiques ont été observées toutes les vingt minutes environ. Le déclenchement physique du teach-in n’est pas documenté dans les sources retrouvées et reste à confirmer ; aucune séquence de bouton n’est supposée. Le mode UTE unidirectionnel permet de traiter un véritable teach-in D2-14-30 si le produit en émet un.

## Données

Fumée, défaut capteur, entretien requis, conditions de température/humidité hors plage, semaines depuis entretien, durée de vie restante (mois), température, humidité, état de pile, confort hygrothermique et analyse d’air basée sur température/humidité sont publiés sur MQTT et exposés à Home Assistant. L’analyse d’air ne mesure ni CO2 ni COV. Les quatre niveaux d’énergie ne sont pas convertis en pourcentage de batterie.

Les valeurs réservées ou en erreur sont indisponibles et ne deviennent pas des mesures. Les conditions environnementales et les défauts ne masquent jamais le bit d’alarme fumée.

Trame fournie : `07 F8 7A C9 39 20` → **20 °C**, **78 %**, aucune alarme ni défaut, pile élevée, durée restante **61 mois**, confort mauvais, humidité élevée. Le compteur d’entretien vaut 255 (erreur), donc n’est pas publié comme durée valide.

## À confirmer sur matériel

- Réception des valeurs et des entités Home Assistant sur l’installation de Philippe.
- Procédure physique de teach-in, identifiant fabricant et photo autorisée.
- Tests des états signalés par le détecteur, selon les consignes du fabricant.

La fiche reste en **Communauté** en attendant cette validation matérielle.

## Sources

- [Fiche officielle EnOcean Alliance : INSAFE+ Origin, I870EO, TX-EEP D2-14-30](https://www.enocean-alliance.org/product/indoor-air-quality-monitor-and-smoke-detector-insafe-origin/).
- [Spécification EEP 2.6.8, pages 266–268](https://www.enocean-alliance.org/wp-content/uploads/2019/10/EEP268_R3_Feb022018_public.pdf) : disposition MSB des 48 bits et plages valides.
- [Notice de la gamme publiée par EnOcean Alliance](https://www.enocean-alliance.org/wp-content/uploads/2018/03/Notice-D526A_FND.pdf).
