// Textes de l'interface en français et en anglais.
// La langue vient de la configuration du service ; l'utilisateur peut la changer
// (Réglages), le choix est gardé dans le navigateur.

export type Lang = "fr" | "en";

const FR = {
  // Menu et en-tête
  "nav.products": "Mes produits",
  "nav.add": "Ajouter un produit",
  "nav.recom": "Remote Commissioning",
  "nav.telegrams": "Télégrammes",
  "nav.settings": "Réglages",
  "foot.version": "Version {v} (bêta)",
  "status.service": "Service connecté",
  "status.connecting": "Connexion au service…",
  "status.stick": "Clé EnOcean connectée",
  "status.noStick": "Clé EnOcean absente",
  "close": "Fermer",
  "cancel": "Annuler",
  "save": "Enregistrer",
  "remove": "Retirer",
  "retry": "Réessayer",
  "refresh": "Relire",
  "loading": "Chargement…",
  // Mes produits
  "products.count": "{n} produit(s) · {a} disponible(s)",
  "products.room": "Pièce",
  "products.allRooms": "Toutes",
  "products.add": "+ Ajouter un produit",
  "products.empty": "Aucun produit pour l'instant",
  "products.emptyHint": "Ajoutez votre premier produit EnOcean depuis la bibliothèque.",
  "card.available": "Disponible",
  "card.silent": "Sans nouvelles",
  "card.onOff": "Marche / arrêt",
  "card.lastAction": "Dernière action",
  "card.silentHint": "Un produit sans pile n'émet que quand on l'utilise : « sans nouvelles » est normal.",
  "card.details": "Détails",
  "card.channel": "Canal {n}",
  "card.position": "Position : {p}",
  "card.posUnknown": "inconnue",
  "card.posClosed": "fermé",
  "card.posOpen": "ouvert",
  "card.posPct": "ouvert à {n} %",
  "card.open": "Ouvrir",
  "card.stop": "Stop",
  "card.close": "Fermer",
  "card.down": "Baisser",
  "card.up": "Monter",
  "seen.never": "jamais vu",
  "seen.s": "vu il y a {n} s",
  "seen.min": "vu il y a {n} min",
  "seen.h": "vu il y a {n} h",
  "seen.d": "vu il y a {n} j",
  "signal.good": "signal bon",
  "signal.medium": "signal moyen",
  "signal.weak": "signal faible",
  // Fiche détaillée
  "detail.control": "Contrôle",
  "detail.settings": "Réglages",
  "detail.recom": "Remote Commissioning",
  "detail.telegrams": "Télégrammes",
  "detail.info": "Informations",
  "detail.rename": "Nom et pièce",
  "detail.name": "Nom",
  "detail.roomOpt": "Pièce (facultatif)",
  "detail.removeConfirm": "Retirer « {name} » d'Ocean2MQTT ?",
  "detail.id": "Identifiant EnOcean",
  "detail.topic": "Topic MQTT",
  "detail.product": "Produit",
  "detail.eep": "Profil EEP",
  "detail.support": "Support",
  "detail.manual": "Notice du produit",
  // Réglages produit
  "settings.none": "Ce produit n'a pas de réglage.",
  "settings.product": "Envoyés au produit",
  "settings.local": "Appliqués par Ocean2MQTT",
  "settings.recom": "Par Remote Commissioning",
  "settings.notRead": "Le produit ne permet pas de relire ces réglages : la valeur affichée est la dernière envoyée.",
  "settings.applied": "Réglage appliqué",
  "settings.run": "Lancer",
  "settings.unset": "non réglé",
  // Remote Commissioning
  "recom.intro": "Réglages à distance des produits qui gèrent le Remote Commissioning (ReMan / ReCom).",
  "recom.none": "Aucun produit appairé ne gère le Remote Commissioning.",
  "recom.access": "Accès",
  "recom.secured": "Code attribué par Ocean2MQTT",
  "recom.pending": "Code en attente de confirmation",
  "recom.locked": "Pas encore de code",
  "recom.unlock": "Déverrouiller",
  "recom.ping": "Test Ping",
  "recom.code": "Code du QR code",
  "recom.codeHint": "8 caractères hexadécimaux, avec ou sans le préfixe 11Z",
  "recom.useCode": "Utiliser ce code",
  "recom.links": "Télécommandes appairées",
  "recom.linksRead": "Lire la table",
  "recom.linksEmpty": "Aucune télécommande dans la table.",
  "recom.linksUnknown": "Table pas encore lue.",
  "recom.linksCount": "{n} / {max} places utilisées",
  "recom.linkAdd": "Ajouter une télécommande",
  "recom.linkId": "Identifiant EnOcean de la télécommande",
  "recom.linkType": "Type",
  "recom.linkAddBtn": "Ajouter",
  "recom.linkDelete": "Supprimer",
  "recom.linkDeleteConfirm": "Supprimer la télécommande {id} de la table ?",
  "recom.config": "Paramètres lus dans le produit",
  "recom.configRead": "Lire les paramètres",
  "recom.log": "Journal",
  "recom.logEmpty": "Aucune opération pour l'instant.",
  "recom.ok": "OK",
  "recom.failed": "Échec",
  "recom.open": "Ouvrir",
  "recom.warning": "Le Remote Management n'est pas chiffré : le code passe en clair à la radio lors d'un déverrouillage.",
  "recom.confirmTitle": "Envoyer le code de sécurité ?",
  "recom.confirmText": "Pour cette opération, Ocean2MQTT doit déverrouiller « {name} » : son code de sécurité est envoyé en clair par radio (le protocole Remote Management n'est pas chiffré). Un récepteur EnOcean à portée pourrait le capter. Le déverrouillage reste valable 10 minutes.",
  "recom.confirmOk": "Envoyer le code",
  "recom.session": "Déverrouillé (encore {n} min)",
  "recom.disabled": "Remote Commissioning désactivé",
  "recom.disabledHint": "Aucune commande Remote Commissioning n'est envoyée. Pour l'activer : recom.enabled dans configuration.yaml, ou l'option « Remote Commissioning » de l'add-on.",
  "app.recom": "Remote Commissioning",
  "app.recomHow": "Pour le désactiver complètement : recom.enabled: false dans configuration.yaml, ou l'option « Remote Commissioning » de l'add-on.",
  "app.recomOn": "Activé : le code de sécurité est demandé à chaque déverrouillage et passe en clair à la radio.",
  // Télégrammes
  "tg.intro": "Télégrammes reçus et émis par la clé, en direct.",
  "tg.pause": "Pause",
  "tg.resume": "Reprendre",
  "tg.clear": "Vider",
  "tg.export": "Exporter (CSV)",
  "tg.sender": "Émetteur",
  "tg.allSenders": "Tous",
  "tg.rorg": "RORG",
  "tg.all": "Tous",
  "tg.time": "Heure",
  "tg.dir": "Sens",
  "tg.data": "Données",
  "tg.dbm": "dBm",
  "tg.rx": "reçu",
  "tg.tx": "émis",
  "tg.dup": "doublon",
  "tg.empty": "Aucun télégramme pour l'instant.",
  "tg.unknownDevice": "inconnu",
  // Ajouter un produit
  "add.subtitle": "Choisissez votre produit dans la bibliothèque, puis suivez sa procédure d'appairage.",
  "add.search": "Rechercher",
  "add.searchHint": "Référence, nom ou EEP (ex. SIN-2, fil pilote, D2-01-0C)",
  "add.brand": "Marque",
  "add.type": "Type",
  "add.all": "Toutes",
  "add.allTypes": "Tous",
  "add.count": "{n} produit(s)",
  "add.legend": "testé sur produit réel",
  "add.legendCommunity": "pas encore testé",
  "add.valid": "Validé",
  "add.community": "Communauté",
  "add.generic": "Générique",
  "add.genericTile": "Produit absent de la bibliothèque ? Choisissez son profil EEP.",
  "add.genericTitle": "Produit générique",
  "add.genericIntro": "Choisissez le profil EEP du produit (indiqué dans sa notice). Vous obtenez les fonctions de base du profil.",
  "add.choose": "Choisissez un produit dans la bibliothèque pour afficher sa procédure d'appairage.",
  "add.profile": "Profil EEP",
  "add.pairing": "Appairage",
  "add.features": "Ce que vous obtiendrez",
  "add.procedure": "Procédure d'appairage",
  "add.step0": "Cliquez sur « Lancer l'appairage » : Ocean2MQTT écoute pendant 60 s.",
  "add.communityHint": "Fiche pas encore testée sur produit réel : si l'appairage échoue, signalez-le sur GitHub.",
  "add.genericHint": "Mode générique : pas de réglages propres au produit. Si tout fonctionne, proposez sa fiche sur GitHub.",
  "add.start": "Lancer l'appairage (60 s)",
  "add.photoMissing": "Photo à fournir",
  "add.timeoutTitle": "Aucun produit détecté",
  "add.timeoutText": "Vérifiez la procédure (alimentation, nombre d'appuis) et que le produit est à portée de la clé, puis réessayez.",
  "add.back": "Retour à la bibliothèque",
  "add.listening": "En écoute…",
  "add.doNow": "Faites maintenant la manipulation du {model} :",
  "add.doNowGeneric": "Faites maintenant la manipulation du produit.",
  "add.paired": "Produit appairé",
  "add.productName": "Nom du produit",
  "add.roomHint": "Salon, Chambre…",
  "add.finish": "Terminer",
  "add.suggestTitle": "Ce produit ressemble à :",
  "add.suggestText": "{id} vient d'envoyer une demande d'appairage ({eep}).",
  "add.unknownTitle": "Émetteurs entendus mais pas appairés",
  "add.unknownHint": "Capteurs et interrupteurs : ajoutez-les en un clic. Un actionneur doit suivre sa procédure.",
  "add.unknownClear": "Effacer la liste",
  "add.pairOneClick": "Ajouter",
  "add.pairWith": "Ajouter comme…",
  "add.seen": "{n} télégramme(s)",
  "add.teachIn": "demande d'appairage",
  // Réglages de l'application
  "app.language": "Langue de l'interface",
  "app.gateway": "Clé EnOcean",
  "app.port": "Port",
  "app.baseId": "Base ID",
  "app.chipId": "Identifiant de la puce",
  "app.firmware": "Version de la clé",
  "app.mqtt": "Serveur MQTT",
  "app.host": "Serveur",
  "app.baseTopic": "Topic de base",
  "app.discovery": "Découverte Home Assistant",
  "app.yes": "oui",
  "app.no": "non",
  "app.configHint": "Ces paramètres se changent dans configuration.yaml (ou dans la configuration de l'add-on Home Assistant).",
  "app.about": "À propos",
  "app.aboutText": "Ocean2MQTT est un projet open source eHomeLabs (licence MIT).",
  // Migration, sauvegarde, changement de clé
  "mig.bannerTitle": "NodOcean for HA détecté",
  "mig.bannerText": "{n} produit(s) appairé(s) avec la clé {base}. Reprenez-les sans réappairer, ou partez d'une installation vierge.",
  "mig.start": "Reprendre mes produits",
  "mig.fresh": "Nouvelle installation",
  "mig.title": "Reprendre les produits de NodOcean for HA",
  "mig.titleFile": "Importer des produits",
  "mig.titleBackup": "Restaurer une sauvegarde",
  "mig.chooseKey": "Quelle clé EnOcean utilisez-vous avec Ocean2MQTT ?",
  "mig.sameKey": "La même clé que NodOcean (recommandé)",
  "mig.sameKeyHint": "Tous les produits sont repris tels quels, actionneurs compris : rien à réappairer.",
  "mig.newKey": "Une autre clé : reprendre les capteurs",
  "mig.newKeyHint": "Capteurs et interrupteurs repris. Les actionneurs gardent leur nom et leur pièce mais sont à réappairer avec la nouvelle clé.",
  "mig.freshKey": "Une autre clé : installation vierge",
  "mig.freshKeyHint": "Rien n'est repris : vous ajoutez vos produits un par un. NodOcean peut rester actif avec son ancienne clé.",
  "mig.disableTitle": "Désactivez d'abord NodOcean for HA",
  "mig.disableText": "Une clé EnOcean ne peut être utilisée que par un seul logiciel. Dans Home Assistant : Paramètres → Appareils et services → NodOcean for HA → ⋮ → Désactiver. Redémarrez ensuite l'add-on Ocean2MQTT si la clé est indiquée absente.",
  "mig.disabledOk": "NodOcean for HA est désactivé.",
  "mig.keyStatus": "Clé branchée : {base}",
  "mig.keyAbsent": "Clé EnOcean absente : elle est sans doute encore utilisée par NodOcean for HA.",
  "mig.mismatch": "La clé branchée ({current}) n'est pas celle qui a appairé ces produits ({source}) : les actionneurs seront à réappairer.",
  "mig.preview": "Produits trouvés",
  "mig.st.ok": "Repris",
  "mig.st.repair": "À réappairer",
  "mig.st.exists": "Déjà présent",
  "mig.st.code": "Code ReCom repris",
  "mig.doneCodes": "Code Remote Commissioning repris pour {n} produit(s) déjà présent(s).",
  "mig.st.unknown": "Modèle inconnu",
  "mig.recom": "code ReCom",
  "mig.import": "Importer {n} produit(s)",
  "mig.next": "Continuer",
  "mig.back": "Retour",
  "mig.doneTitle": "Produits repris",
  "mig.done": "{n} produit(s) importé(s), dont {r} à réappairer.",
  "mig.after": "Les entités Home Assistant de NodOcean sont remplacées par les entités MQTT d'Ocean2MQTT : mettez à jour vos automatisations et tableaux de bord, puis supprimez l'intégration NodOcean for HA. L'historique d'énergie repart sur les nouvelles entités.",
  "mig.freshDone": "Installation vierge : ajoutez vos produits depuis « Ajouter un produit ».",
  "mig.section": "Migration et sauvegarde",
  "mig.fromHa": "Reprendre depuis NodOcean for HA",
  "mig.fromHaNone": "NodOcean for HA n'a pas été trouvé dans la configuration de Home Assistant (add-on uniquement).",
  "mig.fromFile": "Importer un fichier d'export NodOcean",
  "mig.fromFileHint": "Fichier créé par le bouton « Exporter pour Ocean2MQTT » de NodOcean for HA (version 0.8.6 ou plus).",
  "mig.backup": "Télécharger une sauvegarde",
  "mig.backupTitle": "Sauvegarde et restauration",
  "mig.backupHint": "Produits appairés, noms, pièces, réglages et codes Remote Commissioning. Gardez ce fichier en lieu sûr.",
  "mig.restore": "Restaurer une sauvegarde",
  "mig.badFile": "Fichier illisible",
  "repair.badge": "À réappairer",
  "repair.button": "Réappairer",
  "repair.cardHint": "Nouvelle clé EnOcean : ce produit ne répond plus tant qu'il n'est pas réappairé.",
  "repair.bannerTitle": "Nouvelle clé EnOcean détectée",
  "repair.bannerText": "{n} actionneur(s) appairé(s) avec l'ancienne clé ({base}) sont à réappairer. Leur nom, leur pièce et leurs réglages sont conservés.",
  "status.noStickNodocean": "Clé EnOcean absente : si NodOcean for HA l'utilise encore, désactivez-le puis redémarrez Ocean2MQTT.",
} as const;

export type Key = keyof typeof FR;

const EN: Record<Key, string> = {
  "nav.products": "My devices",
  "nav.add": "Add a device",
  "nav.recom": "Remote Commissioning",
  "nav.telegrams": "Telegrams",
  "nav.settings": "Settings",
  "foot.version": "Version {v} (beta)",
  "status.service": "Service connected",
  "status.connecting": "Connecting to the service…",
  "status.stick": "EnOcean stick connected",
  "status.noStick": "No EnOcean stick",
  "close": "Close",
  "cancel": "Cancel",
  "save": "Save",
  "remove": "Remove",
  "retry": "Retry",
  "refresh": "Read again",
  "loading": "Loading…",
  "products.count": "{n} device(s) · {a} available",
  "products.room": "Room",
  "products.allRooms": "All",
  "products.add": "+ Add a device",
  "products.empty": "No device yet",
  "products.emptyHint": "Add your first EnOcean device from the library.",
  "card.available": "Available",
  "card.silent": "No news",
  "card.onOff": "On / off",
  "card.lastAction": "Last action",
  "card.silentHint": "A battery-free device only transmits when used: “no news” is normal.",
  "card.details": "Details",
  "card.channel": "Channel {n}",
  "card.position": "Position: {p}",
  "card.posUnknown": "unknown",
  "card.posClosed": "closed",
  "card.posOpen": "open",
  "card.posPct": "{n} % open",
  "card.open": "Open",
  "card.stop": "Stop",
  "card.close": "Close",
  "card.down": "Lower",
  "card.up": "Raise",
  "seen.never": "never seen",
  "seen.s": "seen {n} s ago",
  "seen.min": "seen {n} min ago",
  "seen.h": "seen {n} h ago",
  "seen.d": "seen {n} d ago",
  "signal.good": "good signal",
  "signal.medium": "fair signal",
  "signal.weak": "weak signal",
  "detail.control": "Control",
  "detail.settings": "Settings",
  "detail.recom": "Remote Commissioning",
  "detail.telegrams": "Telegrams",
  "detail.info": "Information",
  "detail.rename": "Name and room",
  "detail.name": "Name",
  "detail.roomOpt": "Room (optional)",
  "detail.removeConfirm": "Remove “{name}” from Ocean2MQTT?",
  "detail.id": "EnOcean ID",
  "detail.topic": "MQTT topic",
  "detail.product": "Product",
  "detail.eep": "EEP profile",
  "detail.support": "Support",
  "detail.manual": "Product manual",
  "settings.none": "This device has no settings.",
  "settings.product": "Sent to the device",
  "settings.local": "Applied by Ocean2MQTT",
  "settings.recom": "Through Remote Commissioning",
  "settings.notRead": "The device cannot report these settings: the value shown is the last one sent.",
  "settings.applied": "Setting applied",
  "settings.run": "Run",
  "settings.unset": "not set",
  "recom.intro": "Remote settings for devices that support Remote Commissioning (ReMan / ReCom).",
  "recom.none": "No paired device supports Remote Commissioning.",
  "recom.access": "Access",
  "recom.secured": "Code assigned by Ocean2MQTT",
  "recom.pending": "Code waiting for confirmation",
  "recom.locked": "No code yet",
  "recom.unlock": "Unlock",
  "recom.ping": "Ping test",
  "recom.code": "QR code",
  "recom.codeHint": "8 hexadecimal characters, with or without the 11Z prefix",
  "recom.useCode": "Use this code",
  "recom.links": "Paired remotes",
  "recom.linksRead": "Read the table",
  "recom.linksEmpty": "No remote in the table.",
  "recom.linksUnknown": "Table not read yet.",
  "recom.linksCount": "{n} / {max} slots used",
  "recom.linkAdd": "Add a remote",
  "recom.linkId": "EnOcean ID of the remote",
  "recom.linkType": "Type",
  "recom.linkAddBtn": "Add",
  "recom.linkDelete": "Delete",
  "recom.linkDeleteConfirm": "Delete remote {id} from the table?",
  "recom.config": "Parameters read from the device",
  "recom.configRead": "Read parameters",
  "recom.log": "Log",
  "recom.logEmpty": "No operation yet.",
  "recom.ok": "OK",
  "recom.failed": "Failed",
  "recom.open": "Open",
  "recom.warning": "Remote Management is not encrypted: the code is sent in clear over the air when unlocking.",
  "recom.confirmTitle": "Send the security code?",
  "recom.confirmText": "For this operation, Ocean2MQTT must unlock “{name}”: its security code is sent in clear over the air (Remote Management is not encrypted). An EnOcean receiver within range could capture it. The unlock stays valid for 10 minutes.",
  "recom.confirmOk": "Send the code",
  "recom.session": "Unlocked ({n} min left)",
  "recom.disabled": "Remote Commissioning disabled",
  "recom.disabledHint": "No Remote Commissioning command is ever sent. To enable it: recom.enabled in configuration.yaml, or the add-on's “Remote Commissioning” option.",
  "app.recom": "Remote Commissioning",
  "app.recomHow": "To disable it completely: recom.enabled: false in configuration.yaml, or the add-on's “Remote Commissioning” option.",
  "app.recomOn": "Enabled: you are asked before each unlock, and the security code is sent in clear over the air.",
  "tg.intro": "Telegrams received and sent by the stick, live.",
  "tg.pause": "Pause",
  "tg.resume": "Resume",
  "tg.clear": "Clear",
  "tg.export": "Export (CSV)",
  "tg.sender": "Sender",
  "tg.allSenders": "All",
  "tg.rorg": "RORG",
  "tg.all": "All",
  "tg.time": "Time",
  "tg.dir": "Dir.",
  "tg.data": "Data",
  "tg.dbm": "dBm",
  "tg.rx": "rx",
  "tg.tx": "tx",
  "tg.dup": "duplicate",
  "tg.empty": "No telegram yet.",
  "tg.unknownDevice": "unknown",
  "add.subtitle": "Pick your device in the library, then follow its pairing procedure.",
  "add.search": "Search",
  "add.searchHint": "Reference, name or EEP (e.g. SIN-2, pilot wire, D2-01-0C)",
  "add.brand": "Brand",
  "add.type": "Type",
  "add.all": "All",
  "add.allTypes": "All",
  "add.count": "{n} device(s)",
  "add.legend": "tested on a real device",
  "add.legendCommunity": "not tested yet",
  "add.valid": "Validated",
  "add.community": "Community",
  "add.generic": "Generic",
  "add.genericTile": "Device not in the library? Pick its EEP profile.",
  "add.genericTitle": "Generic device",
  "add.genericIntro": "Pick the device's EEP profile (see its manual). You get the basic functions of the profile.",
  "add.choose": "Pick a device in the library to see its pairing procedure.",
  "add.profile": "EEP profile",
  "add.pairing": "Pairing",
  "add.features": "What you will get",
  "add.procedure": "Pairing procedure",
  "add.step0": "Click “Start pairing”: Ocean2MQTT listens for 60 s.",
  "add.communityHint": "Not tested on a real device yet: if pairing fails, please report it on GitHub.",
  "add.genericHint": "Generic mode: no device-specific settings. If everything works, propose its sheet on GitHub.",
  "add.start": "Start pairing (60 s)",
  "add.photoMissing": "Photo to be provided",
  "add.timeoutTitle": "No device detected",
  "add.timeoutText": "Check the procedure (power, number of presses) and that the device is within range of the stick, then try again.",
  "add.back": "Back to the library",
  "add.listening": "Listening…",
  "add.doNow": "Now do the {model} procedure:",
  "add.doNowGeneric": "Now do the device procedure.",
  "add.paired": "Device paired",
  "add.productName": "Device name",
  "add.roomHint": "Living room, Bedroom…",
  "add.finish": "Finish",
  "add.suggestTitle": "This device looks like:",
  "add.suggestText": "{id} just sent a pairing request ({eep}).",
  "add.unknownTitle": "Heard but not paired",
  "add.unknownHint": "Sensors and switches: add them in one click. An actuator must follow its procedure.",
  "add.unknownClear": "Clear the list",
  "add.pairOneClick": "Add",
  "add.pairWith": "Add as…",
  "add.seen": "{n} telegram(s)",
  "add.teachIn": "pairing request",
  "app.language": "Interface language",
  "app.gateway": "EnOcean stick",
  "app.port": "Port",
  "app.baseId": "Base ID",
  "app.chipId": "Chip ID",
  "app.firmware": "Stick version",
  "app.mqtt": "MQTT server",
  "app.host": "Server",
  "app.baseTopic": "Base topic",
  "app.discovery": "Home Assistant discovery",
  "app.yes": "yes",
  "app.no": "no",
  "app.configHint": "These parameters are changed in configuration.yaml (or in the Home Assistant add-on configuration).",
  "app.about": "About",
  "app.aboutText": "Ocean2MQTT is an open source eHomeLabs project (MIT licence).",
  "mig.bannerTitle": "NodOcean for HA found",
  "mig.bannerText": "{n} device(s) paired with stick {base}. Bring them over without re-pairing, or start from a fresh install.",
  "mig.start": "Bring my devices over",
  "mig.fresh": "Fresh install",
  "mig.title": "Bring over NodOcean for HA devices",
  "mig.titleFile": "Import devices",
  "mig.titleBackup": "Restore a backup",
  "mig.chooseKey": "Which EnOcean stick do you use with Ocean2MQTT?",
  "mig.sameKey": "The same stick as NodOcean (recommended)",
  "mig.sameKeyHint": "Every device is taken over as is, actuators included: nothing to re-pair.",
  "mig.newKey": "Another stick: bring over sensors",
  "mig.newKeyHint": "Sensors and switches are taken over. Actuators keep their name and room but must be re-paired with the new stick.",
  "mig.freshKey": "Another stick: fresh install",
  "mig.freshKeyHint": "Nothing is taken over: you add your devices one by one. NodOcean can keep running with its own stick.",
  "mig.disableTitle": "First disable NodOcean for HA",
  "mig.disableText": "An EnOcean stick can only be used by one program at a time. In Home Assistant: Settings → Devices & services → NodOcean for HA → ⋮ → Disable. Then restart the Ocean2MQTT add-on if the stick is shown as missing.",
  "mig.disabledOk": "NodOcean for HA is disabled.",
  "mig.keyStatus": "Stick plugged in: {base}",
  "mig.keyAbsent": "No EnOcean stick: it is probably still used by NodOcean for HA.",
  "mig.mismatch": "The stick plugged in ({current}) is not the one that paired these devices ({source}): actuators will have to be re-paired.",
  "mig.preview": "Devices found",
  "mig.st.ok": "Taken over",
  "mig.st.repair": "To re-pair",
  "mig.st.exists": "Already there",
  "mig.st.code": "ReCom code taken over",
  "mig.doneCodes": "Remote Commissioning code taken over for {n} device(s) already there.",
  "mig.st.unknown": "Unknown model",
  "mig.recom": "ReCom code",
  "mig.import": "Import {n} device(s)",
  "mig.next": "Continue",
  "mig.back": "Back",
  "mig.doneTitle": "Devices taken over",
  "mig.done": "{n} device(s) imported, {r} of them to re-pair.",
  "mig.after": "NodOcean's Home Assistant entities are replaced by Ocean2MQTT's MQTT entities: update your automations and dashboards, then delete the NodOcean for HA integration. Energy history starts again on the new entities.",
  "mig.freshDone": "Fresh install: add your devices from “Add a device”.",
  "mig.section": "Migration and backup",
  "mig.fromHa": "Bring over from NodOcean for HA",
  "mig.fromHaNone": "NodOcean for HA was not found in the Home Assistant configuration (add-on only).",
  "mig.fromFile": "Import a NodOcean export file",
  "mig.fromFileHint": "File created by the “Export for Ocean2MQTT” button of NodOcean for HA (version 0.8.6 or later).",
  "mig.backup": "Download a backup",
  "mig.backupTitle": "Backup and restore",
  "mig.backupHint": "Paired devices, names, rooms, settings and Remote Commissioning codes. Keep this file somewhere safe.",
  "mig.restore": "Restore a backup",
  "mig.badFile": "Unreadable file",
  "repair.badge": "To re-pair",
  "repair.button": "Re-pair",
  "repair.cardHint": "New EnOcean stick: this device won't respond until it is re-paired.",
  "repair.bannerTitle": "New EnOcean stick detected",
  "repair.bannerText": "{n} actuator(s) paired with the previous stick ({base}) must be re-paired. Their name, room and settings are kept.",
  "status.noStickNodocean": "No EnOcean stick: if NodOcean for HA still uses it, disable it and restart Ocean2MQTT.",
};

// Mesures, contrôles et réglages
const KEYS: Record<Lang, Record<string, string>> = {
  fr: {
    temperature: "Température", humidity: "Humidité", power: "Puissance", energy: "Énergie",
    illuminance: "Luminosité", voltage: "Tension", battery: "Batterie", co2: "CO2", voc: "COV",
    valve_position: "Ouverture vanne", setpoint: "Consigne", rssi: "Signal", mode: "Mode fil pilote",
    position: "Position", open: "Ouverture", motion: "Mouvement", card: "Carte", water_leak: "Fuite d'eau",
    window_open: "Fenêtre", battery_low: "Pile", handle: "Poignée", action: "Dernière action",
    state: "Marche / arrêt",
    led: "LED", local_control: "Bouton local", taught_in: "Télécommandes appairées en direct",
    power_failure: "Détection de coupure", power_on_state: "État au retour du courant",
    switch_type: "Type d'interrupteur filaire", auto_off: "Extinction automatique",
    delay_off: "Extinction retardée", travel_time: "Temps de course", rs_switch_type: "Type d'interrupteur (volet)",
    calibration: "Calibration", repeater: "Répéteur", energy_reset: "Remise à zéro de l'énergie",
    buttons: "Nombre de boutons", temperature_offset: "Correction de température",
    humidity_offset: "Correction d'humidité", timeout: "Indisponible après (0 = jamais)",
  },
  en: {
    temperature: "Temperature", humidity: "Humidity", power: "Power", energy: "Energy",
    illuminance: "Illuminance", voltage: "Voltage", battery: "Battery", co2: "CO2", voc: "VOC",
    valve_position: "Valve opening", setpoint: "Setpoint", rssi: "Signal", mode: "Pilot wire mode",
    position: "Position", open: "Opening", motion: "Motion", card: "Card", water_leak: "Water leak",
    window_open: "Window", battery_low: "Battery", handle: "Handle", action: "Last action",
    state: "On / off",
    led: "LED", local_control: "Local button", taught_in: "Directly paired remotes",
    power_failure: "Power failure detection", power_on_state: "Power-on state",
    switch_type: "Wired switch type", auto_off: "Auto off", delay_off: "Delay off",
    travel_time: "Travel time", rs_switch_type: "Switch type (shutter)", calibration: "Calibration",
    repeater: "Repeater", energy_reset: "Reset energy", buttons: "Number of buttons",
    temperature_offset: "Temperature offset", humidity_offset: "Humidity offset",
    timeout: "Unavailable after (0 = never)",
  },
};

const OPTIONS: Record<Lang, Record<string, string>> = {
  fr: {
    off: "Arrêt", comfort: "Confort", eco: "Éco", frost_protection: "Hors-gel", comfort_1: "Confort -1",
    comfort_2: "Confort -2", closed: "Fermée", open: "Ouverte", tilt: "Oscillo-battant",
    left_up: "Gauche haut", left_down: "Gauche bas", right_up: "Droite haut", right_down: "Droite bas",
    release: "Relâché", press: "Appui", single: "Appui simple", double: "Double appui", long: "Appui long",
    long_release: "Fin d'appui long", previous: "Comme avant", on: "Allumé",
    auto: "Automatique", switch: "Interrupteur", switch_2_state: "Interrupteur 2 états", push_button: "Bouton poussoir",
    level_1: "Niveau 1", level_2: "Niveau 2", classic: "Classique", complex: "Complexe", stop: "Arrêter",
    reset: "Remettre à zéro", type_1: "Type 1", type_2: "Type 2", type_3: "Type 3", type_4: "Type 4",
    rocker_a: "Interrupteur (rocker A)", rocker_b: "Interrupteur (rocker B)", key_card: "Interrupteur à carte",
    window_handle: "Poignée de fenêtre", contact: "Contact d'ouverture", motion: "Détecteur de mouvement",
    soft_button: "Bouton (D2-03-0A)", "4": "4 boutons", "2": "2 boutons",
    ping: "Ping", unlock: "Déverrouillage", code: "Code", links: "Lecture des liens",
    "links/add": "Ajout de lien", "links/delete": "Suppression de lien", config: "Lecture des paramètres",
    assigned: "code attribué", unlocked: "déverrouillé",
  },
  en: {
    off: "Off", comfort: "Comfort", eco: "Eco", frost_protection: "Frost protection", comfort_1: "Comfort -1",
    comfort_2: "Comfort -2", closed: "Closed", open: "Open", tilt: "Tilted",
    left_up: "Left up", left_down: "Left down", right_up: "Right up", right_down: "Right down",
    release: "Released", press: "Press", single: "Single press", double: "Double press", long: "Long press",
    long_release: "Long press released", previous: "As before", on: "On",
    auto: "Automatic", switch: "Switch", switch_2_state: "2-state switch", push_button: "Push button",
    level_1: "Level 1", level_2: "Level 2", classic: "Classic", complex: "Complex", stop: "Stop",
    reset: "Reset", type_1: "Type 1", type_2: "Type 2", type_3: "Type 3", type_4: "Type 4",
    rocker_a: "Switch (rocker A)", rocker_b: "Switch (rocker B)", key_card: "Key card switch",
    window_handle: "Window handle", contact: "Contact sensor", motion: "Motion sensor",
    soft_button: "Button (D2-03-0A)", "4": "4 buttons", "2": "2 buttons",
    ping: "Ping", unlock: "Unlock", code: "Code", links: "Read links",
    "links/add": "Add link", "links/delete": "Delete link", config: "Read parameters",
    assigned: "code assigned", unlocked: "unlocked",
  },
};

const BINARY: Record<Lang, Record<string, [string, string]>> = {
  fr: {
    open: ["Ouvert", "Fermé"], motion: ["Mouvement", "Calme"], card: ["Carte insérée", "Pas de carte"],
    water_leak: ["Eau détectée", "Sec"], window_open: ["Ouverte", "Fermée"], battery_low: ["Faible", "OK"],
    _: ["Oui", "Non"],
  },
  en: {
    open: ["Open", "Closed"], motion: ["Motion", "Clear"], card: ["Card inserted", "No card"],
    water_leak: ["Water detected", "Dry"], window_open: ["Open", "Closed"], battery_low: ["Low", "OK"],
    _: ["Yes", "No"],
  },
};

const TYPES: Record<Lang, Record<string, string>> = {
  fr: { actionneur: "Actionneurs", chauffage: "Chauffage", prise: "Prises", interrupteur: "Interrupteurs", capteur: "Capteurs" },
  en: { actionneur: "Actuators", chauffage: "Heating", prise: "Plugs", interrupteur: "Switches", capteur: "Sensors" },
};

const TEACH: Record<Lang, Record<string, string>> = {
  fr: { ute_bidir: "UTE bidirectionnel", ute_uni: "UTE", "1bs": "1BS", "4bs": "4BS", "4bs_bidir": "4BS bidirectionnel", rps: "Premier appui" },
  en: { ute_bidir: "Bidirectional UTE", ute_uni: "UTE", "1bs": "1BS", "4bs": "4BS", "4bs_bidir": "Bidirectional 4BS", rps: "First press" },
};

let current: Lang = "fr";
let explicit = false;
try {
  const saved = localStorage.getItem("ocean2mqtt.lang");
  if (saved === "fr" || saved === "en") {
    current = saved;
    explicit = true;
  }
} catch {
  /* stockage indisponible */
}

export function getLang(): Lang {
  return current;
}

/** Langue de la configuration du service, sauf si l'utilisateur en a choisi une. */
export function defaultLang(lang: string | undefined) {
  if (!explicit && lang) current = lang.startsWith("en") ? "en" : "fr";
}

export function setLang(lang: Lang) {
  current = lang;
  explicit = true;
  try {
    localStorage.setItem("ocean2mqtt.lang", lang);
  } catch {
    /* stockage indisponible */
  }
}

export function t(key: Key, vars: Record<string, string | number> = {}): string {
  const text: string = current === "en" ? EN[key] : FR[key];
  return text.replace(/\{(\w+)\}/g, (_, k: string) => String(vars[k] ?? ""));
}

export function label(key: string): string {
  const m = /^(state|auto_off|delay_off)_l(\d+)$/.exec(key);
  if (m) {
    if (m[1] === "state") return t("card.channel", { n: m[2] });
    return `${KEYS[current][m[1]]} (${t("card.channel", { n: m[2] }).toLowerCase()})`;
  }
  return KEYS[current][key] ?? key;
}

export function option(value: string): string {
  return OPTIONS[current][value] ?? value.replaceAll("_", " ");
}

export function binaryText(key: string): [string, string] {
  return BINARY[current][key] ?? BINARY[current]._;
}

export function typeName(type: string): string {
  return TYPES[current][type] ?? type;
}

export function teachIn(mode: string): string {
  return TEACH[current][mode] ?? mode;
}

export function locale(): string {
  return current === "en" ? "en-GB" : "fr-FR";
}

export function formatValue(value: unknown, unit?: string): string {
  if (value === undefined || value === null) return "—";
  if (typeof value === "number") {
    const text = value.toLocaleString(locale(), { maximumFractionDigits: 2 });
    return unit ? `${text} ${unit}` : text;
  }
  return String(value);
}

export function since(iso: string | null | undefined, now: number): string {
  if (!iso) return t("seen.never");
  const s = Math.max(0, Math.round((now - Date.parse(iso)) / 1000));
  if (s < 60) return t("seen.s", { n: s });
  if (s < 3600) return t("seen.min", { n: Math.round(s / 60) });
  if (s < 86400) return t("seen.h", { n: Math.round(s / 3600) });
  return t("seen.d", { n: Math.round(s / 86400) });
}

export function signal(rssi: unknown): string {
  if (typeof rssi !== "number") return "";
  const dbm = rssi > 0 ? -rssi : rssi;
  if (dbm >= -70) return t("signal.good");
  if (dbm >= -85) return t("signal.medium");
  return t("signal.weak");
}

export function supportName(support: string): string {
  if (support === "valide") return t("add.valid");
  if (support === "generique") return t("add.generic");
  return t("add.community");
}

type Localized = { name: string; steps: string[]; after: string; i18n?: Record<string, { name: string; steps: string[]; after: string }> };

/** Nom, procédure et conseil d'un produit dans la langue de l'interface. */
export function productText(product: Localized): { name: string; steps: string[]; after: string } {
  return product.i18n?.[current] ?? { name: product.name, steps: product.steps, after: product.after };
}
