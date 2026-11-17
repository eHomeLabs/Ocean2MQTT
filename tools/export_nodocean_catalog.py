"""Convertit le catalogue de NodOcean for HA en fiches YAML Ocean2MQTT.

Usage : python tools/export_nodocean_catalog.py <dossier NodOcean-for-HA> <dossier produits>
Outil de migration utilisé une fois ; les fiches YAML font foi ensuite.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
import sys
from pathlib import Path

import yaml

TYPES = {
    "SIN-2-1-01": "actionneur", "SIN-2-2-01": "actionneur", "SIN-2-FP-01": "chauffage",
    "SIN-2-RS-01": "actionneur", "ASP-2": "prise", "ASP-2-METERING": "prise", "MSP-2": "prise",
    "CWS-2-1": "interrupteur", "CRC-2": "interrupteur", "CFS-2": "interrupteur",
    "CCS-2": "interrupteur", "TSB-2": "interrupteur",
    "SDO-2": "capteur", "SWO-2": "capteur", "PIR-2": "capteur", "STP-2": "capteur", "STPH-2": "capteur",
}  # fmt: skip
DECODERS = {"CRC-2": "soft_remote", "CFS-2": "single_button"}
SETTINGS = {
    "led": "LED", "power_on_state": "POWER_ON_STATE", "local_control": "LOCAL_CONTROL",
    "taught_in": "TAUGHT_IN", "power_failure": "POWER_FAILURE", "auto_off": "AUTO_OFF",
    "delay_off": "DELAY_OFF", "switch_type": "SWITCH_TYPE", "roller_shutter": "ROLLER_SHUTTER",
    "temperature_offset": "TEMPERATURE_OFFSET", "humidity_offset": "HUMIDITY_OFFSET",
    "timeout": "TIMEOUT", "buttons": "BUTTON_MODE",
}  # fmt: skip


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def steps(text: str) -> list[str]:
    text = text.replace("**", "").replace("Home Assistant", "Ocean2MQTT").strip()
    parts = re.split(r"(?<=[.)])\s+(?=[A-ZÀ-Ý(])", text)
    return [p.strip() for p in parts if p.strip()]


class Dumper(yaml.SafeDumper):
    pass


def _str(dumper, value):
    return dumper.represent_scalar("tag:yaml.org,2002:str", value)


Dumper.add_representer(str, _str)


def main(nodocean: Path, out: Path) -> None:
    comp = nodocean / "custom_components" / "nodon_enocean"
    catalog = _load(comp / "catalog.py", "nodocean_catalog")
    features = _load(comp / "features.py", "nodocean_features")
    images = nodocean / "docs" / "images" / "products"
    for model, p in catalog.PRODUCTS.items():
        brand = "ubiwizz" if model == "ASP-2-METERING" else "nodon"
        ref = "UBID1501S" if brand == "ubiwizz" else model
        folder = out / brand
        folder.mkdir(parents=True, exist_ok=True)
        german = catalog.GERMAN.get(model, {})
        data: dict = {
            "ref": ref,
            "marque": "Ubiwizz" if brand == "ubiwizz" else "NodOn",
            "nom": {"fr": p.name_fr, "en": p.name_en},
            "type": TYPES[model],
            "eep": p.eep,
        }
        if german.get("name"):
            data["nom"]["de"] = german["name"]
        if model in DECODERS:
            data["decodeur"] = DECODERS[model]
        data["fabricant_id"] = 0x046
        pairing = {"mode": p.teach_in, "etapes": {"fr": steps(p.pairing_fr), "en": steps(p.pairing_en)}}
        if german.get("pairing"):
            pairing["etapes"]["de"] = steps(german["pairing"])
        if p.after_fr:
            pairing["apres"] = {"fr": p.after_fr, "en": p.after_en}
            if german.get("after"):
                pairing["apres"]["de"] = german["after"]
        data["appairage"] = pairing
        if p.channels != 1:
            data["canaux"] = p.channels
        if p.metering:
            data["mesure"] = True
        settings = [k for k, attr in SETTINGS.items() if model in getattr(features, attr)]
        if settings:
            data["reglages"] = settings
        if model in features.RECOM:
            data["recom"] = True
        data["support"] = "valide"
        if p.manual:
            data["notice"] = p.manual
        source_image = images / ("ASP-2.png" if model == "ASP-2-METERING" else f"{model}.png")
        if source_image.is_file():
            photo = f"{ref.lower()}.png"
            shutil.copy(source_image, folder / photo)
            data["photo"] = photo
        variants = [v for v in p.variants if v != ref]
        if variants:
            data["variantes"] = variants
        if brand == "ubiwizz":
            data["notes"] = (
                "Même matériel que la prise NodOn ASP-2 avec mesure (ASP-2-1-01 / ASP-2-1-11). "
                "Fiche reprise de NodOcean for HA (modèle ASP-2-METERING)."
            )
        path = folder / f"{ref.lower()}.yaml"
        path.write_text(
            yaml.dump(data, Dumper=Dumper, allow_unicode=True, sort_keys=False, width=100),
            encoding="utf-8",
        )
        print(path)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
