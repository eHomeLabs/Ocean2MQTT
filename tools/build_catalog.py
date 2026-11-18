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


def build(out: Path) -> int:
    library = load_library(ROOT / "produits")
    out.mkdir(parents=True, exist_ok=True)
    (out / "photos").mkdir(exist_ok=True)
    items = []
    for product in sorted(library.products.values(), key=lambda p: (p.brand.lower(), p.model)):
        photo = None
        if product.image:
            src = Path(product.image)
            dest = out / "photos" / product.id.replace("/", "-")
            dest = dest.with_suffix(src.suffix)
            shutil.copyfile(src, dest)
            photo = f"photos/{dest.name}"
        items.append({
            "id": product.id,
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
            "features": sorted({e.key for e in exposes(product)} - {"rssi"}),
            "sheet": f"{REPO}/blob/main/produits/{product.id}.yaml",
        })
    generics = sorted(p.eep for p in library.generics())
    (out / "catalogue.json").write_text(
        json.dumps({"products": items, "generic_eeps": generics}, ensure_ascii=False),
        encoding="utf-8",
    )
    shutil.copyfile(Path(__file__).parent / "catalog" / "index.html", out / "index.html")
    shutil.copyfile(ROOT / "docs" / "logo" / "ocean2mqtt-mark.svg", out / "logo.svg")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    print(f"{len(items)} produits, {len(generics)} profils génériques -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(build(Path(sys.argv[1] if len(sys.argv) > 1 else "site")))
