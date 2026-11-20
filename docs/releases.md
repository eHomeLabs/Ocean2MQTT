# Publier Ocean2MQTT

| Référence Git | Tags Docker sur GHCR |
| --- | --- |
| Branche `main` | `edge` |
| Tag bêta, par exemple `v0.2.0b26` | `v0.2.0b26`, `beta` |
| Tag stable, par exemple `v0.2.0` | `v0.2.0`, `latest` |

Le tag doit correspondre à la version déclarée dans `pyproject.toml`. La CI
s'exécute sur le commit à publier avant la construction et la publication de
l'image. Créez les tags de version depuis un commit validé sur `main`.

Pour une release GitHub bêta, cochez **Set as a pre-release**. Le dépôt de
l'add-on Home Assistant référence un tag exact après publication de l'image.

## Protection de main

Dans **Settings → Rules → Rulesets**, créez une règle de branche active
ciblant `main`. Exigez une pull request avec les trois vérifications du
workflow **CI** (Python 3.12, Python 3.13 et `frontend`). Sélectionnez les
noms affichés dans GitHub après un passage de la CI sur une PR. Bloquez les
force-push et la suppression de la branche. Tant qu'un seul mainteneur peut
fusionner, laissez le nombre d'approbations exigées à zéro.

## Stable 0.2.0

See [release preparation and upgrade notes](release-0.2.0.md) for the publication
order across the service and Home Assistant add-on repositories.
