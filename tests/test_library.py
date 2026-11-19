"""Bibliothèque de produits : fiches valides, recherche, suggestion automatique."""

from pathlib import Path

import pytest

from ocean2mqtt.core.esp3 import RadioTelegram
from ocean2mqtt.core.product import SUPPORT_LEVELS, TEACH_MODES
from ocean2mqtt.library import check_file, default_root, load_library

ROOT = default_root()
FILES = sorted(ROOT.glob("*/*.yaml"))


def test_root_found() -> None:
    assert (ROOT / "schema.json").is_file()
    assert len(FILES) >= 20


@pytest.mark.parametrize("path", FILES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_every_sheet_is_valid(path: Path) -> None:
    assert check_file(path, ROOT) == []


def test_products_loaded() -> None:
    lib = load_library()
    assert "nodon/sin-2-fp-01" in lib.products
    fp = lib.products["nodon/sin-2-fp-01"]
    assert fp.brand == "NodOn" and fp.eep == "D2-01-0C" and fp.recom
    assert fp.has("led") and fp.support == "valide"
    assert Path(fp.image).is_file()
    for p in lib.products.values():
        assert p.teach_in in TEACH_MODES
        assert p.support in SUPPORT_LEVELS
        assert p.name("fr") and p.name("de")  # repli sur l'anglais / le français


def test_search() -> None:
    lib = load_library()
    assert [p.model for p in lib.search("fil pilote")] == ["SIN-2-FP-01", "UBICH009"]
    assert {p.model for p in lib.search("D2-01-0C")} == {"SIN-2-FP-01", "UBICH009"}
    assert {p.model for p in lib.search("ubiwizz co2")} == {"UBILD023"}
    assert {p.brand for p in lib.by_brand("ubiwizz")} == {"Ubiwizz"}


def test_suggestion_from_teach_in() -> None:
    lib = load_library()
    assert [p.model for p in lib.match_teach_in("D2-01-0C", 0x046)] == ["SIN-2-FP-01"]
    plugs = {p.model for p in lib.match_teach_in("D2-01-0B")}
    assert plugs == {"UBID1501S"}


def test_invalid_sheet_reports_errors(tmp_path: Path) -> None:
    (tmp_path / "schema.json").write_text((ROOT / "schema.json").read_text())
    folder = tmp_path / "acme"
    folder.mkdir()
    bad = folder / "x1.yaml"
    bad.write_text("ref: X1\nmarque: Acme\nnom: {fr: Truc}\ntype: capteur\neep: A5-99-99\n"
                   "appairage: {mode: 4bs, etapes: {fr: [Appuyez sur LRN.]}}\nsupport: valide\n")
    assert check_file(bad, tmp_path) == ["aucun décodeur pour A5-99-99"]
    bad.write_text("ref: X1\nmarque: Acme\n")
    assert check_file(bad, tmp_path)  # champs obligatoires manquants


def _t(rorg: int, payload: str, status: int = 0) -> RadioTelegram:
    return RadioTelegram(rorg=rorg, payload=bytes.fromhex(payload), sender=0x05112233, status=status)


def test_device_uses_sheet_decoders() -> None:
    """Le décodeur est choisi par la fiche, plus par le nom du modèle."""
    from ocean2mqtt.core.device import Device

    lib = load_library()
    crc = Device.__new__(Device)
    crc.product = lib.products["nodon/crc-2"]
    assert crc.decode(_t(0xF6, "10", 0x30)) == {"event": "right_up"}
    air = Device.__new__(Device)
    air.product = lib.products["ubiwizz/ubild023"]
    assert air.decode(_t(0xA5, "00 2D 00 08")) == {"co2": 450}


def test_moved_sheets_keep_old_ids() -> None:
    lib = load_library()
    assert lib.get("ubiwizz/serfah60").id == "eltako/fah60"
    assert lib.get("ubiwizz/ubid1220211").id == "afriso/55080"
    assert lib.get("ubiwizz/micitrv004").id == "micropelt/micitrv004"
    assert [p.id for p in lib.search("SERFAH60")] == ["eltako/fah60"]
