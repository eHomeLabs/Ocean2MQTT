# Produits à ajouter

Produits prévus pour la v1 dont la fiche n'est pas encore possible.

| Marque | Référence | Produit | EEP | Ce qui manque |
| --- | --- | --- | --- | --- |
| Ubiwizz | MICITRV004 | Vanne thermostatique EnOcean (sans pile, effet Seebeck) | A5-20-01 | Profil bidirectionnel : la passerelle doit répondre à chaque télégramme de la vanne (consigne). Prévu en phase 2. |
| Ubiwizz | à préciser | Télécommande 1 canal EnOcean | à préciser | Référence et EEP (page produit non lisible automatiquement). |

## Ajouter un produit

1. Créez `produits/<marque>/<référence>.yaml` (marque et référence en minuscules), à partir d'une fiche existante.
2. Ajoutez la photo à côté (`<référence>.png`, fond transparent, 400 × 400 px) si vous en avez le droit.
3. Vérifiez la fiche : `python -m ocean2mqtt.library`.
4. Une nouvelle fiche entre en `support: communaute`. Elle passe en `valide` après un essai sur produit réel (rapport de test joint à la demande de fusion).
