**Français** · [English](Remote-Commissioning-EN)

# Remote Commissioning

Le **Remote Commissioning** (protocole EnOcean Remote Management, « ReMan / ReCom ») permet de régler un produit à distance : lire et modifier la liste des télécommandes qui lui sont associées, lire les paramètres d'un volet, etc. Il est géré par les modules NodOn (SIN-2-x, volet SIN-2-RS-01…). Onglet **Remote Commissioning** de la fiche du produit, ou page **Remote Commissioning** pour tous les produits.

## Le code de sécurité

Chaque produit peut être protégé par un **code de sécurité** de 32 bits :

- **sans code**, le produit n'accepte les commandes à distance que pendant les **5 minutes qui suivent sa mise sous tension** ;
- **avec un code**, il les accepte à tout moment, à condition d'envoyer d'abord ce code (« déverrouillage »). Le produit reste déverrouillé 5 minutes ; Ocean2MQTT renvoie le code au bout de 4 minutes si besoin.

À l'appairage (ou plus tard, dans la fenêtre de 5 minutes après une mise sous tension), Ocean2MQTT propose :

| Choix | Fonctionnement |
| --- | --- |
| **Code automatique** (recommandé) | Calculé à partir de l'identifiant du produit et d'un **secret propre à votre installation**. Toujours le même pour un produit, impossible à deviner sans le secret. Le secret est dans la sauvegarde. |
| **Code saisi** | Le code du QR code du produit (`11Z…`, ex. SIN-2-RS-01) ou un code de votre choix (8 caractères hexadécimaux). |
| **Aucun code** | Rien n'est envoyé. Réglages à distance seulement dans les 5 minutes après une mise sous tension. |

Les codes attribués par une version précédente ou par NodOcean for HA restent valables (« code aléatoire »).

## Le produit a déjà un code

Volet **« Le produit a déjà un code ? »** :
- saisissez le code connu (QR code) → **Utiliser ce code** ;
- ou **Détecter le code** : Ocean2MQTT essaie le code enregistré, le code automatique et le code saisi (un déverrouillage par code).

**Code perdu ?** Faites un reset usine du produit (NodOn : appui d'environ **8 secondes** sur le bouton, relâchez, puis **appui bref**), appairez-le à nouveau et choisissez un code.

## Sécurité

Le protocole Remote Management n'est **pas chiffré** : le code passe en clair à la radio lors d'un déverrouillage, un récepteur EnOcean à portée pourrait le capter. C'est pourquoi Ocean2MQTT :

- n'envoie le code que sur une action de votre part et **demande confirmation** avant chaque envoi ;
- ne montre jamais le code et le masque dans les journaux ;
- peut **désactiver complètement** le Remote Commissioning : option **Remote Commissioning** de l'add-on, ou `recom.enabled: false` dans `configuration.yaml`. Aucune commande Remote Management n'est alors envoyée.

La sauvegarde et le fichier `devices.json` contiennent les codes : gardez-les en lieu sûr.

## Télécommandes associées

**Lire la table** affiche les télécommandes enregistrées dans le produit (identifiant, profil). Vous pouvez en **ajouter** (identifiant EnOcean + type : interrupteur, contact, détecteur…) ou en **supprimer** sans toucher au produit.
