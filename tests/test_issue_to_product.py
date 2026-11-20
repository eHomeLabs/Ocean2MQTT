"""Formulaire « Proposer un nouveau produit EnOcean » -> fiche YAML valide."""

from __future__ import annotations

import sys
from pathlib import Path

import jsonschema
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import issue_to_product as itp

from ocean2mqtt.library import _schema, _to_product

BODY = """### Marque / Brand

Ubiwizz

### Référence / Reference

UBI-Test 42

### Nom en français / French name

Détecteur de fumée

### Nom en anglais / English name

_No response_

### Type

capteur (sensor)

### Profil EEP / EEP profile

f6 05 02

### Autres profils émis / Other profiles sent (facultatif / optional)

_No response_

### Code fabricant EnOcean / EnOcean manufacturer ID (facultatif / optional)

0x046

### Mode d'appairage / Pairing mode

je ne sais pas / I don't know

### Procédure d'appairage en français / Pairing steps in French

1. Installez la pile.
2. Appuyez sur Learn.

### Procédure d'appairage en anglais / Pairing steps in English (facultatif / optional)

_No response_

### Nombre de canaux (actionneurs) / Number of channels (actuators) (facultatif / optional)

_No response_

### Fonctions / Features

- [ ] Mesure de puissance / énergie (power / energy metering)
- [X] Remote Commissioning (ReMan / ReCom)

### Lien vers la notice ou la fiche technique / Manual or datasheet link

https://example.com/notice.pdf

### Photo du produit / Device picture

<img width="400" alt="photo" src="https://github.com/user-attachments/assets/1234" />

### Ce qui fonctionne déjà, remarques / What already works, notes

Marche en générique.
"""


def test_issue_body_to_sheet() -> None:
    fields = itp.parse_sections(BODY)
    assert fields["nom_en"] == "" and fields["eep"] == "f6 05 02"
    product_id, sheet = itp.build(fields)
    assert product_id == "ubiwizz/ubi-test-42"
    assert sheet["eep"] == "F6-05-02" and sheet["appairage"]["mode"] == "rps"
    assert sheet["appairage"]["etapes"]["fr"] == ["Installez la pile.", "Appuyez sur Learn."]
    assert sheet["fabricant_id"] == 0x46 and sheet["recom"] and "mesure" not in sheet
    assert sheet["notice"] == "https://example.com/notice.pdf"
    assert itp.photo_url(fields["photo"]) == "https://github.com/user-attachments/assets/1234"
    root = Path(__file__).resolve().parent.parent / "produits"
    jsonschema.Draft202012Validator(_schema(root)).validate(sheet)
    _to_product(product_id, root / "ubiwizz" / "x.yaml", sheet)


def test_incomplete_issue() -> None:
    with pytest.raises(itp.IssueError, match="EEP"):
        itp.build(itp.parse_sections(BODY.replace("f6 05 02", "inconnu")))

def test_english_first_issue_without_french_copy() -> None:
    body = """### Brand / Marque

Ubiwizz

### Reference / Référence

UBI-Test 42

### English name / Nom en anglais

Smoke detector

### Type

capteur (sensor)

### EEP profile / Profil EEP

F6-05-02

### Pairing steps in English / Procédure d'appairage en anglais

1. Insert the battery.
2. Press Learn.
"""
    _, sheet = itp.build(itp.parse_sections(body))
    assert sheet["nom"] == {"fr": "Smoke detector", "en": "Smoke detector"}
    assert sheet["appairage"]["etapes"] == {
        "fr": ["Insert the battery.", "Press Learn."],
        "en": ["Insert the battery.", "Press Learn."],
    }
    root = Path(__file__).resolve().parent.parent / "produits"
    jsonschema.Draft202012Validator(_schema(root)).validate(sheet)


def test_all_missing_fields_are_reported_at_once() -> None:
    with pytest.raises(itp.IssueError) as error:
        itp.build({})

    assert str(error.value).splitlines()[1:] == [
        "- Brand / Marque",
        "- Reference / Référence",
        "- EEP profile / Profil EEP (format A5-02-05)",
        "- Type",
        "- Pairing steps in English or French / Procédure d'appairage en anglais ou français",
    ]
