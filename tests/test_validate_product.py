"""Formulaire « Confirmer qu'un produit fonctionne » -> fiche passée en « valide »."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import validate_product as vp

REPO = Path(__file__).resolve().parent.parent

BODY = """### Fiche / Device sheet

{fiche}

### Version d'Ocean2MQTT / Ocean2MQTT version

0.2.0b23

### Profil EEP / EEP profile

A5-04-02

### Ce qui fonctionne / What works

- [x] Appairage / Pairing
- [x] Mesures et états (valeurs cohérentes) / Measurements and states (plausible values)
- [ ] Commandes (marche/arrêt, volet, fil pilote…) / Commands
- [ ] Réglages / Settings
- [ ] Remote Commissioning

### Dernières valeurs reçues / Last received values

```json
{{"temperature": -3.2}}
```

### Remarques, ce qui ne fonctionne pas / Notes, what does not work

_No response_
"""


@pytest.fixture
def root(tmp_path, monkeypatch) -> Path:
    shutil.copytree(REPO / "produits", tmp_path / "produits")
    monkeypatch.setattr(vp, "ROOT", tmp_path / "produits")
    return tmp_path / "produits"


def issue(fiche: str) -> dict:
    return {"number": 7, "user": {"login": "testeur"}, "body": BODY.format(fiche=fiche)}


def test_validate_community_sheet(root) -> None:
    path = vp.validate(issue("eltako/faft60"))
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["support"] == "valide"
    assert "À confirmer" not in data["notes"]
    assert data["notes"].endswith(
        "Confirmé sur produit réel (appairage, mesures et états (valeurs cohérentes)), "
        "Ocean2MQTT 0.2.0b23 : issue #7 (testeur)."
    )


def test_old_sheet_id_and_errors(root) -> None:
    assert vp.validate(issue("ubiwizz/serfah60")).name == "fah60.yaml"
    with pytest.raises(vp.ValidationError, match="déjà"):
        vp.validate(issue("nodon/sin-2-1-01"))
    with pytest.raises(vp.ValidationError, match="introuvable"):
        vp.validate(issue("eltako/inconnu"))
    with pytest.raises(vp.ValidationError, match="invalide"):
        vp.validate(issue("../../etc/passwd"))
    unchecked = issue("eltako/fpe-1")
    unchecked["body"] = unchecked["body"].replace("- [x]", "- [ ]")
    with pytest.raises(vp.ValidationError, match="Aucune fonction"):
        vp.validate(unchecked)

def test_english_first_report(root) -> None:
    report = issue("eltako/faft60")
    report["body"] = (
        report["body"]
        .replace("Fiche / Device sheet", "Device sheet / Fiche")
        .replace("Ce qui fonctionne / What works", "What works / Ce qui fonctionne")
        .replace(
            "Version d'Ocean2MQTT / Ocean2MQTT version",
            "Ocean2MQTT version / Version d'Ocean2MQTT",
        )
    )
    data = yaml.safe_load(vp.validate(report).read_text(encoding="utf-8"))
    assert data["support"] == "valide"
    assert "Ocean2MQTT 0.2.0b23" in data["notes"]
