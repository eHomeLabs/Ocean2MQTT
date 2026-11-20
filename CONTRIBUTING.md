# Contributing to Ocean2MQTT

[English](#english) · [Français](#français)

## English

English and French contributions are welcome.

### Suggest or validate a device

1. Search the [catalog](https://ehomelabs.github.io/Ocean2MQTT/) and try [generic mode](docs/wiki/Adding-an-unsupported-device.md) if your device is missing.
2. Submit the [device form](https://github.com/eHomeLabs/Ocean2MQTT/issues/new?template=nouveau-produit.yml) with the exact model, EEP, pairing steps and tested features. Only attach photos you have permission to redistribute under MIT, as stated in the form. Remove credentials, Remote Commissioning codes and other secrets from diagnostic data.
3. A maintainer applies the `accepté` label after review. The workflow opens a pull request for the YAML sheet and optional photo. Once merged, the device enters the catalog as **Community** and ships in the next release.
4. After testing on real hardware, use **Information → Confirm this device works** or the [test report form](https://github.com/eHomeLabs/Ocean2MQTT/issues/new?template=retour-test.yml). A maintainer reviews the tested features and applies `validé` to generate the PR that marks it **Validated**.

### Contribute code

Open a focused PR against `main`. Use the [setup and test commands](#contribuer-au-code). Follow the [catalog schema](produits/schema.json) and keep the path of published device sheets stable. Review generated PRs and select **Approve workflows to run** if GitHub prompts for approval. Merge after all three required checks pass.

## Français

### Proposer un appareil EnOcean

1. Recherchez la marque et la référence dans le [catalogue](https://ehomelabs.github.io/Ocean2MQTT/). Si la fiche manque, essayez le [mode générique et l’identification du profil EEP](docs/wiki/Ajouter-un-produit-non-supporté.md).
2. Ouvrez le [formulaire de proposition](https://github.com/eHomeLabs/Ocean2MQTT/issues/new?template=nouveau-produit.yml). Indiquez la référence exacte, le profil EEP, les étapes d’appairage et les fonctions déjà testées. Ajoutez la notice et, si possible, une photo que vous êtes autorisé à faire redistribuer sous MIT. Le formulaire précise la licence de ces éléments. Le logiciel est sous [GPL v3](LICENSE).
3. Si vous joignez des télégrammes, limitez l’export à l’appareil concerné et indiquez l’action associée à chaque extrait. Retirez les codes Remote Commissioning, les identifiants de connexion MQTT et tout autre secret avant de publier.
4. Un mainteneur relit la proposition et ajoute l’étiquette `accepté`. Le workflow **Nouveau produit** ouvre une pull request pour la fiche YAML et la photo éventuelle. La fiche entre au catalogue en **Communauté** après fusion et sera incluse dans la prochaine version.
5. Après un essai sur l’appareil réel, ouvrez sa fiche dans Ocean2MQTT, puis **Informations → Confirmer que ce produit fonctionne**. Le [formulaire de retour](https://github.com/eHomeLabs/Ocean2MQTT/issues/new?template=retour-test.yml) permet d’indiquer la version utilisée et les fonctions réellement vérifiées. Après revue, l’étiquette `validé` génère une deuxième PR qui fait passer la fiche en **Validé**.

Un profil déjà pris en charge peut souvent être ajouté avec une fiche YAML seule. Si le profil ou une commande manque dans le moteur, précisez-le dans l’issue. Conservez le chemin YAML des fiches publiées, car il sert d’identifiant aux appareils existants.

### Contribuer au code

Travaillez sur une branche et ouvrez une PR ciblée vers `main`. Pour une nouvelle fiche, utilisez le [schéma du catalogue](produits/schema.json). Pour un changement radio ou MQTT, précisez le matériel, le profil concerné et le comportement vérifié.

```sh
python -m pip install -e ".[dev]"
python -m ocean2mqtt.library
ruff check src tests tools
pytest -q
```

Pour tester l’interface avec Node.js 22, lancez `npm ci` puis `npm run build` dans `frontend/`. Depuis la racine, `python tools/demo.py` lance la démo avec une clé et des appareils simulés.

### Vérifier une PR générée automatiquement

Le mainteneur contrôle que la fiche correspond à la référence et au profil, que les étapes d’appairage sont exploitables et que les droits de la photo sont établis. Sur la PR, cliquez sur **Approve workflows to run** si GitHub affiche ce bouton. Attendez les trois contrôles obligatoires de `main` (`tests (3.12)`, `tests (3.13)` et `frontend`). Pour la promotion en **Validé**, comparez la fiche au retour de test sur matériel.
