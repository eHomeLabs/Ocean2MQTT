**Français** · [English](Adding-an-unsupported-device)

# Ajouter un produit non supporté

Votre produit EnOcean n'est pas dans la bibliothèque ? Il y a plusieurs solutions, de la plus rapide à la plus complète.

| Situation | Solution |
| --- | --- |
| Le produit utilise un profil EEP standard déjà géré | **1. Mode générique** : il marche tout de suite |
| Vous ne connaissez pas son profil | **2. Identifier le produit** avec le journal radio |
| Il marche en générique et vous voulez qu'il soit dans la liste pour tout le monde | **3. Proposer une fiche produit** |
| Son profil n'est pas géré par Ocean2MQTT | **4. Demander un nouveau profil** |

---

## 1. Mode générique : utiliser le produit tout de suite

La plupart des produits EnOcean respectent un **profil EEP** (EnOcean Equipment Profile) standard, noté `RORG-FUNC-TYPE`, par exemple `A5-02-05` pour une sonde de température. Ocean2MQTT sait décoder ces profils, quelle que soit la marque.

1. **Ajouter un produit** → tuile **Générique**.
2. Choisissez le profil EEP du produit (il figure souvent dans sa notice ou sa fiche technique, ou sur le site de la marque).
3. Lancez l'appairage et mettez le produit en mode apprentissage (voir sa notice).

Profils proposés en mode générique :

| Profil | Produit |
| --- | --- |
| F6-02-01 | Interrupteur 2 boutons (rocker) |
| F6-04-01 | Interrupteur à carte |
| F6-05-01 | Détecteur de fuite d'eau |
| F6-05-02 | Détecteur de fumée |
| F6-10-00 | Poignée de fenêtre |
| D5-00-01 | Contact d'ouverture |
| A5-02-05 | Sonde de température 0–40 °C |
| A5-04-01 | Température et humidité |
| A5-06-01 | Luminosité |
| A5-07-03 | Mouvement et luminosité |
| A5-09-04 | CO2, humidité, température |
| A5-09-05 | COV |
| A5-20-01 | Tête thermostatique |
| D2-01-xx | Actionneur on/off, variateur, prise avec mesure (type et nombre de canaux lus à l'appairage) |
| D2-05-00 | Volet roulant |

Si le produit fonctionne, pensez à **proposer sa fiche** (étape 3) : les autres utilisateurs le trouveront directement par sa marque et sa référence.

Un produit a été ajouté en générique et sa fiche existe depuis ? Fiche du produit → **Informations → Changer de fiche** : pas besoin de le réappairer.

---

## 2. Identifier le produit avec le journal radio

Ocean2MQTT écoute tout ce qui passe à portée de la clé.

1. Ouvrez **Ajouter un produit** et faites émettre le produit (appui sur son bouton d'apprentissage, sur une touche, ouverture d'un contact…).
2. S'il envoie une **demande d'appairage complète** (UTE, ou 4BS avec profil), Ocean2MQTT affiche **« Ce produit ressemble à »** avec les fiches et le profil correspondants, et le produit apparaît dans la liste des **émetteurs entendus** avec son identifiant, son code fabricant et son profil.
3. Sinon, ouvrez la page **Télégrammes**, filtrez sur l'identifiant du produit et regardez :
   - **RORG** : `F6` (RPS : interrupteurs, poignées, fuite d'eau), `D5` (1BS : contacts), `A5` (4BS : capteurs), `D2` (VLD : actionneurs, compteurs), `D4` (UTE : demande d'appairage) ;
   - les **données** envoyées à chaque action.
4. **Exporter en CSV** : ce fichier sera très utile pour l'étape 3 ou 4.

> Un interrupteur RPS (F6-02-01) n'envoie ni sa marque ni sa référence : c'est normal qu'Ocean2MQTT ne puisse pas le reconnaître tout seul. Choisissez « Interrupteur 2 boutons » en générique ou sa fiche si elle existe.

---

## 3. Proposer une fiche produit

Une fiche, c'est **un fichier YAML + une photo**, sans écrire de code. Elle permet de retrouver le produit par sa marque et sa référence, avec sa procédure d'appairage dans la langue de l'utilisateur.

### Le plus simple : ouvrir une demande

[Ouvrir une issue « Nouveau produit »](https://github.com/eHomeLabs/Ocean2MQTT/issues/new?template=nouveau-produit.yml) avec :
- la marque, la référence et le nom du produit ;
- son profil EEP (ou l'export CSV du journal radio) ;
- la procédure d'appairage (notice ou lien vers la notice) ;
- une photo du produit si vous avez le droit de la partager ;
- ce qui fonctionne déjà en mode générique.

### Pour les contributeurs : la fiche YAML

Fichier `produits/<marque>/<référence>.yaml` (en minuscules), par exemple `produits/ubiwizz/ubild001.yaml` :

```yaml
ref: UBILD001                 # référence commerciale
marque: Ubiwizz
nom:
  fr: Détecteur de fumée
  en: Smoke detector
type: capteur                 # actionneur, prise, interrupteur, capteur, chauffage
eep: F6-05-02                 # profil principal
appairage:
  mode: rps                   # rps, 1bs, 4bs, 4bs_bidir, ute_uni, ute_bidir
  etapes:
    fr:
    - Installez la pile 9 V fournie.
    - Appuyez 2 secondes sur le bouton « Learn » jusqu'au bip.
    en:
    - Insert the supplied 9 V battery.
    - Press the "Learn" button for 2 seconds until it beeps.
reglages:
- timeout
support: communaute           # « valide » seulement après un test sur produit réel
photo: ubild001.png
notice: https://…
notes: Ce qui reste à confirmer sur produit réel.
```

Champs utiles :

| Champ | Rôle |
| --- | --- |
| `fabricant_id` | Code fabricant EnOcean (ex. 70 pour NodOn) : améliore la suggestion automatique |
| `eep_supplementaires` | Autres profils émis par le même produit (ex. CO2 + COV) |
| `canaux` | Nombre de canaux d'un actionneur |
| `mesure` | `true` si le produit mesure puissance / énergie |
| `reglages` | Réglages proposés : `led`, `power_on_state`, `local_control`, `auto_off`, `delay_off`, `switch_type`, `roller_shutter`, `temperature_offset`, `humidity_offset`, `timeout`, `buttons`… |
| `recom` | `true` si le produit gère le Remote Commissioning |
| `appairage.apres` | Conseil affiché une fois l'appairage réussi |
| `variantes` | Autres références du même produit |

Le format complet est décrit dans [`produits/schema.json`](https://github.com/eHomeLabs/Ocean2MQTT/blob/main/produits/schema.json).

**Mode d'appairage** :
- `rps` / `1bs` : le produit envoie un télégramme normal (appui, contact) ; Ocean2MQTT l'enregistre ;
- `4bs` : télégramme d'apprentissage 4BS (bouton « Learn ») ;
- `4bs_bidir` : 4BS avec réponse (têtes thermostatiques A5-20-01) ;
- `ute_uni` / `ute_bidir` : demande UTE ; Ocean2MQTT répond automatiquement (actionneurs D2).

**Photo** : PNG carré, fond transparent, 400 × 400 px conseillé, même nom que la fiche. Utilisez uniquement une photo que vous avez le droit de partager.

**Vérifier la fiche** avant de proposer la modification :

```bash
python -m ocean2mqtt.library   # contrôle toutes les fiches (schéma, photo, profil géré)
pytest                          # tests
```

Puis proposez une *pull request*. Une fiche entre en **Communauté** ; elle passe en **Validé** après un rapport de test sur produit réel (appairage, commandes, mesures, réglages).

---

## 4. Demander un nouveau profil EEP

Si le profil de votre produit n'est pas dans la liste du mode générique, Ocean2MQTT ne sait pas encore décoder ses télégrammes. [Ouvrez une issue « Nouveau produit »](https://github.com/eHomeLabs/Ocean2MQTT/issues/new?template=nouveau-produit.yml) avec :
- le profil EEP (notice ou fiche technique) ;
- l'**export CSV des télégrammes** (page Télégrammes), en notant ce que vous faisiez à chaque télégramme (appui sur tel bouton, température lue sur un autre appareil…) ;
- si possible la fiche technique du fabricant.

Le décodage d'un profil s'écrit à partir de la spécification EnOcean des EEP ; vos télégrammes réels permettent de le vérifier.
