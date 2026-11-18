"""Bibliothèque de produits : chargement et validation des fiches YAML."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yaml

from ..core.eep import supported
from ..core.product import (
    TEACH_1BS,
    TEACH_4BS,
    TEACH_4BS_BIDIR,
    TEACH_RPS,
    TEACH_UTE_BIDIR,
    Product,
)

GENERIC_BRAND = "generique"

# Profils proposés en mode générique : EEP -> (type, mode d'appairage, nom FR, nom EN)
GENERIC_EEPS: dict[str, tuple[str, str, str, str]] = {
    "F6-02-01": ("interrupteur", TEACH_RPS, "Interrupteur 2 boutons (rocker)",
                 "2-rocker switch"),
    "F6-04-01": ("capteur", TEACH_RPS, "Interrupteur à carte", "Key card switch"),
    "F6-05-01": ("capteur", TEACH_RPS, "Détecteur de fuite d'eau", "Water leak sensor"),
    "F6-10-00": ("capteur", TEACH_RPS, "Poignée de fenêtre", "Window handle"),
    "D5-00-01": ("capteur", TEACH_1BS, "Contact d'ouverture", "Contact sensor"),
    "A5-02-05": ("capteur", TEACH_4BS, "Capteur de température (0-40 °C)",
                 "Temperature sensor (0-40 °C)"),
    "A5-04-01": ("capteur", TEACH_4BS, "Capteur de température et d'humidité",
                 "Temperature and humidity sensor"),
    "A5-06-01": ("capteur", TEACH_4BS, "Capteur de luminosité", "Light sensor"),
    "A5-07-03": ("capteur", TEACH_4BS, "Détecteur de mouvement et luminosité",
                 "Motion and light sensor"),
    "A5-09-04": ("capteur", TEACH_4BS, "Capteur CO2, humidité, température",
                 "CO2, humidity, temperature sensor"),
    "A5-09-05": ("capteur", TEACH_4BS, "Capteur de COV", "VOC sensor"),
    "A5-20-01": ("actionneur", TEACH_4BS_BIDIR, "Tête thermostatique",
                 "Thermostatic radiator valve"),
    "D2-01-00": ("actionneur", TEACH_UTE_BIDIR, "Actionneur on/off (D2-01, tous types)",
                 "On/off actuator (D2-01, any type)"),
    "D2-05-00": ("actionneur", TEACH_UTE_BIDIR, "Volet roulant (D2-05)",
                 "Roller shutter (D2-05)"),
}

_STEPS = {
    TEACH_RPS: (
        "Appuyez sur un bouton du produit (ou basculez la poignée).",
        "Press a button on the product (or turn the handle).",
    ),
    TEACH_1BS: (
        "Appuyez sur le bouton d'appairage (LRN) du produit.",
        "Press the product's learn (LRN) button.",
    ),
    TEACH_4BS: (
        ("Appuyez sur le bouton d'appairage (LRN) pour que le produit envoie son "
         "télégramme d'apprentissage."),
        "Press the learn (LRN) button so that the product sends its teach-in telegram.",
    ),
    TEACH_4BS_BIDIR: (
        ("Lancez l'appairage sur le produit (voir sa notice) : Ocean2MQTT répond "
         "automatiquement."),
        "Start pairing on the product (see its manual): Ocean2MQTT answers automatically.",
    ),
    TEACH_UTE_BIDIR: (
        ("Mettez le produit en mode appairage (voir sa notice) : il envoie une demande UTE "
         "et Ocean2MQTT répond automatiquement."),
        ("Put the product in pairing mode (see its manual): it sends a UTE request and "
         "Ocean2MQTT answers automatically."),
    ),
}

# Nombre de canaux des actionneurs D2-01 selon le type
_D201_CHANNELS = {0x10: 2, 0x11: 2, 0x12: 2, 0x13: 4, 0x14: 8}


def generic_product(eep: str) -> Product | None:
    """Produit générique pour un EEP (« D2-01-12 »…), None si le profil n'est pas géré."""
    eep = eep.upper()
    key = "D2-01-00" if eep.startswith("D2-01") else eep
    if key not in GENERIC_EEPS or not supported(eep):
        return None
    type_, mode, fr, en = GENERIC_EEPS[key]
    channels = _D201_CHANNELS.get(int(eep[6:], 16), 1) if eep.startswith("D2-01") else 1
    if eep.startswith("D2-01") and eep != key:
        fr, en = f"Actionneur on/off {eep}", f"On/off actuator {eep}"
    step_fr, step_en = _STEPS[mode]
    return Product(
        id=f"{GENERIC_BRAND}/{eep.lower()}",
        brand="Générique",
        model=eep,
        eep=eep,
        teach_in=mode,
        names={"fr": fr, "en": en},
        pairing_steps={"fr": (step_fr,), "en": (step_en,)},
        type=type_,
        channels=channels,
        support="generique",
        generic=True,
        settings=frozenset({"timeout"}) if type_ != "actionneur" else frozenset(),
    )


class LibraryError(Exception):
    """Fiche produit invalide."""


def default_root() -> Path:
    """Dossier des fiches : celui du paquet installé, sinon celui du dépôt."""
    here = Path(__file__).resolve()
    installed = here.parent.parent / "produits"
    if installed.is_dir():
        return installed
    return here.parents[3] / "produits"


@dataclass
class Library:
    root: Path
    products: dict[str, Product]

    def get(self, product_id: str) -> Product | None:
        """Fiche de la bibliothèque, ou produit générique « generique/<eep> »."""
        if product_id in self.products:
            return self.products[product_id]
        brand, _, eep = product_id.partition("/")
        return generic_product(eep) if brand == GENERIC_BRAND else None

    def generics(self) -> list[Product]:
        return [p for eep in GENERIC_EEPS if (p := generic_product(eep)) is not None]

    def by_brand(self, brand: str) -> list[Product]:
        return [p for p in self.products.values() if p.brand.lower() == brand.lower()]

    def search(self, text: str) -> list[Product]:
        """Recherche libre sur la référence, le nom, la marque et l'EEP."""
        words = text.lower().split()
        found = []
        for p in self.products.values():
            haystack = " ".join(
                [p.model, p.brand, p.eep, *p.extra_eeps, *p.variants, *p.names.values()]
            ).lower()
            if all(w in haystack for w in words):
                found.append(p)
        return found

    def match_teach_in(self, eep: str, manufacturer_id: int | None = None) -> list[Product]:
        """Produits qui correspondent à une demande d'appairage (suggestion automatique)."""
        found = [p for p in self.products.values() if p.eep == eep]
        if manufacturer_id is not None:
            exact = [p for p in found if p.manufacturer_id == manufacturer_id]
            return exact or found
        return found


def _schema(root: Path) -> dict:
    return json.loads((root / "schema.json").read_text(encoding="utf-8"))


def _to_product(product_id: str, path: Path, data: dict) -> Product:
    pairing = data["appairage"]
    return Product(
        id=product_id,
        brand=data["marque"],
        model=data["ref"],
        eep=data["eep"],
        teach_in=pairing["mode"],
        names=dict(data["nom"]),
        pairing_steps={lang: tuple(steps) for lang, steps in pairing["etapes"].items()},
        type=data["type"],
        channels=data.get("canaux", 1),
        metering=data.get("mesure", False),
        decoder=data.get("decodeur"),
        extra_eeps=tuple(data.get("eep_supplementaires", ())),
        settings=frozenset(data.get("reglages", ())),
        recom=data.get("recom", False),
        support=data["support"],
        manufacturer_id=data.get("fabricant_id"),
        manual=data.get("notice"),
        image=str(path.parent / data["photo"]) if data.get("photo") else None,
        after=dict(pairing.get("apres", {})),
        variants=tuple(data.get("variantes", ())),
    )


def check_file(path: Path, root: Path, validator=None) -> list[str]:
    """Liste des erreurs d'une fiche (vide si elle est valide)."""
    import jsonschema

    errors: list[str] = []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as err:
        return [f"YAML invalide : {err}"]
    validator = validator or jsonschema.Draft202012Validator(_schema(root))
    for err in validator.iter_errors(data):
        where = "/".join(str(x) for x in err.absolute_path) or "(racine)"
        errors.append(f"{where} : {err.message}")
    if errors:
        return errors
    if path.stem != data["ref"].lower().replace(" ", "-"):
        errors.append(f"le fichier doit s'appeler {data['ref'].lower().replace(' ', '-')}.yaml")
    if path.parent.name != data["marque"].lower():
        errors.append(f"la fiche doit être rangée dans produits/{data['marque'].lower()}/")
    for code in [data.get("decodeur") or data["eep"], *data.get("eep_supplementaires", [])]:
        if not supported(code):
            errors.append(f"aucun décodeur pour {code}")
    if data.get("photo") and not (path.parent / data["photo"]).is_file():
        errors.append(f"photo absente : {data['photo']}")
    return errors


def load_library(root: Path | None = None) -> Library:
    root = Path(root) if root else default_root()
    products: dict[str, Product] = {}
    for path in sorted(root.glob("*/*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        product_id = f"{path.parent.name}/{path.stem}"
        try:
            products[product_id] = _to_product(product_id, path, data)
        except (KeyError, TypeError) as err:
            raise LibraryError(f"{path} : champ manquant ou invalide ({err})") from err
    return Library(root, products)


def main() -> int:
    """Contrôle de toutes les fiches : python -m ocean2mqtt.library [dossier]."""
    import sys

    import jsonschema

    root = Path(sys.argv[1]) if len(sys.argv) > 1 else default_root()
    validator = jsonschema.Draft202012Validator(_schema(root))
    files = sorted(root.glob("*/*.yaml"))
    failed = 0
    for path in files:
        errors = check_file(path, root, validator)
        for error in errors:
            print(f"{path.relative_to(root)} : {error}")
        failed += bool(errors)
    print(f"{len(files)} fiches contrôlées, {failed} en erreur")
    return 1 if failed else 0
