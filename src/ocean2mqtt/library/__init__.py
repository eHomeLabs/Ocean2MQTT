"""Bibliothèque de produits : chargement et validation des fiches YAML."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yaml

from ..core.eep import supported
from ..core.product import Product


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
