"""Passe une fiche de « Communauté » à « Validé » à partir d'un retour de test.

Utilisé par le workflow GitHub « Retour de test » quand le mainteneur ajoute
l'étiquette « validé » : python tools/validate_product.py issue.json
(issue.json = l'issue au format de l'API GitHub : title, body, number, user).
Modifie produits/<marque>/<référence>.yaml et affiche le chemin de la fiche.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent / "produits"
EMPTY = {"", "_No response_", "_Pas de réponse_", "None"}
# Mentions « à confirmer » retirées des notes une fois le produit validé
TO_CONFIRM = re.compile(
    r"\s*[^.]*(?:à confirmer sur produit réel|to be confirmed on a real device)[^.]*\.?",
    re.IGNORECASE,
)


class ValidationError(ValueError):
    """Retour de test inexploitable (message affiché dans l'issue)."""


def sections(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for block in re.split(r"^### ", body or "", flags=re.MULTILINE)[1:]:
        label, _, value = block.partition("\n")
        value = value.strip()
        for heading in label.split(" / "):
            out[heading.strip()] = "" if value in EMPTY else value
    return out


def checked(text: str) -> list[str]:
    """Cases cochées d'un champ « checkboxes » (partie française du libellé)."""
    found = re.findall(r"^- \[[xX]\] (.+)$", text or "", re.MULTILINE)
    return [m.split(" / ")[0].strip() for m in found]


def sheet_path(sheet_id: str) -> Path:
    from ocean2mqtt.library import ALIASES  # anciennes références de fiches

    sheet_id = sheet_id.strip().strip("`").lower()
    sheet_id = ALIASES.get(sheet_id, sheet_id)
    if not re.fullmatch(r"[a-z0-9_-]+/[a-z0-9_.-]+", sheet_id):
        raise ValidationError(f"Identifiant de fiche invalide : « {sheet_id} » (format marque/référence)")
    path = ROOT / f"{sheet_id}.yaml"
    if not path.is_file():
        raise ValidationError(f"Fiche introuvable : produits/{sheet_id}.yaml")
    return path


def validate(issue: dict) -> Path:
    fields = sections(issue.get("body") or "")
    sheet = fields.get("Fiche", "")
    if not sheet:
        raise ValidationError("Champ « Fiche » vide")
    path = sheet_path(sheet)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data.get("support") == "valide":
        raise ValidationError(f"La fiche {path.relative_to(ROOT)} est déjà « valide »")
    works = checked(fields.get("Ce qui fonctionne", ""))
    if not works:
        raise ValidationError("Aucune fonction cochée dans « Ce qui fonctionne »")
    data["support"] = "valide"
    notes = TO_CONFIRM.sub("", data.get("notes") or "").strip()
    who = (issue.get("user") or {}).get("login")
    version = fields.get("Version d'Ocean2MQTT", "")
    confirmed = f"Confirmé sur produit réel ({', '.join(works).lower()})"
    if version:
        confirmed += f", Ocean2MQTT {version}"
    confirmed += f" : issue #{issue.get('number')}"
    if who:
        confirmed += f" ({who})"
    data["notes"] = f"{notes} {confirmed}.".strip()
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8"
    )
    return path


def main() -> int:
    issue = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    try:
        path = validate(issue)
    except ValidationError as err:
        print(f"ERREUR : {err}")
        return 1
    print(path.relative_to(ROOT.parent))
    return 0


if __name__ == "__main__":
    sys.exit(main())
