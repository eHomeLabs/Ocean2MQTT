"""Construit le catalogue web des produits (GitHub Pages) : python tools/build_catalog.py site

Lit les fiches de produits/, copie les photos et écrit site/index.html + site/catalogue.json.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ocean2mqtt.core.exposes import exposes
from ocean2mqtt.library import load_library

REPO = "https://github.com/eHomeLabs/Ocean2MQTT"


def artwork_index(eep: str, type_: str, features: list[str]) -> int:
    keys = set(features)
    if eep == "F6-05-01" or "water_leak" in keys:
        return 11
    if eep.startswith("D5-00") or eep == "F6-10-00" or "open" in keys:
        return 5
    if eep.startswith("A5-20"):
        return 10
    if eep.startswith("D2-05") or "position" in keys:
        return 7
    if type_ == "prise":
        return 1
    if eep.startswith("A5-09") or keys & {"co2", "voc"}:
        return 4
    if eep.startswith(("A5-07", "A5-08")) or keys & {"motion", "occupancy"}:
        return 2
    if eep.startswith("A5-06") or "illuminance" in keys:
        return 3
    if type_ == "chauffage" or "setpoint" in keys:
        return 9
    if eep.startswith(("A5-02", "A5-04")) or "temperature" in keys:
        return 0
    if type_ == "interrupteur" or eep.startswith(("F6-01", "F6-02")):
        return 8
    return 6


def build(out: Path) -> int:
    library = load_library(ROOT / "produits")
    out.mkdir(parents=True, exist_ok=True)
    (out / "photos").mkdir(exist_ok=True)
    items = []
    products = list(library.products.values()) + library.generics()
    for product in sorted(products, key=lambda p: (p.generic, p.brand.lower(), p.model)):
        photo = None
        if product.image:
            src = Path(product.image)
            dest = out / "photos" / product.id.replace("/", "-")
            dest = dest.with_suffix(src.suffix)
            shutil.copyfile(src, dest)
            photo = f"photos/{dest.name}"
        features = sorted({e.key for e in exposes(product)} - {"rssi"})
        family = ("controllers" if product.type == "interrupteur" else
                  "sensors" if product.type == "capteur" else "actuators")
        items.append({
            "id": product.id,
            "generic": product.generic,
            "family": family,
            "artwork": artwork_index(product.eep, product.type, features),
            "brand": product.brand,
            "model": product.model,
            "references": list(product.variants) or [product.model],
            "names": {lang: product.name(lang) for lang in ("fr", "en")},
            "steps": {lang: list(product.steps(lang)) for lang in ("fr", "en")},
            "type": product.type,
            "eep": product.eep,
            "extra_eeps": list(product.extra_eeps),
            "support": product.support,
            "teach_in": product.teach_in,
            "metering": product.metering,
            "recom": product.recom,
            "manual": product.manual,
            "photo": photo,
            "features": features,
            "sheet": None if product.generic else f"{REPO}/blob/main/produits/{product.id}.yaml",
        })
    generics = sorted(p.eep for p in library.generics())
    (out / "catalogue.json").write_text(
        json.dumps({"products": items, "generic_eeps": generics}, ensure_ascii=False),
        encoding="utf-8",
    )
    shutil.copyfile(Path(__file__).parent / "catalog" / "index.html", out / "index.html")
    shutil.copyfile(ROOT / "frontend/src/assets/generic-devices.png", out / "generic-devices.png")
    shutil.copyfile(ROOT / "docs" / "logo" / "ocean2mqtt-mark.svg", out / "logo.svg")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    print(f"{len(items)} produits, {len(generics)} profils génériques -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(build(Path(sys.argv[1] if len(sys.argv) > 1 else "site")))
