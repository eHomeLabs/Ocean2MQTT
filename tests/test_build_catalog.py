"""Public catalog is derived from actual device sheets, including generic profiles."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import build_catalog as catalog

from ocean2mqtt.library import load_library


def test_catalog_preserves_support_and_local_assets(tmp_path):
    catalog.build(tmp_path)
    data = json.loads((tmp_path / "catalogue.json").read_text())
    library = load_library(catalog.ROOT / "produits")
    indexed = {p["id"]: p for p in data["products"]}
    assert len(indexed) == len(library.products) + len(library.generics())
    for product in library.products.values():
        item = indexed[product.id]
        assert item["support"] == product.support
        assert item["eep"] == product.eep
        if item["photo"]:
            assert (tmp_path / item["photo"]).is_file()
    for product in library.generics():
        item = indexed[product.id]
        assert item["support"] == "generique"
        assert item["sheet"] is None
        assert 0 <= item["artwork"] < 12
    assert (tmp_path / "generic-devices.png").is_file()
    assert indexed["generique/a5-04-03"]["artwork"] == 0
    assert indexed["generique/a5-07-01"]["artwork"] == 2
    assert indexed["generique/d5-00-01"]["artwork"] == 5
