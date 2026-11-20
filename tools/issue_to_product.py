"""Crée une fiche produit à partir d'une issue « Proposer un nouveau produit EnOcean ».

Utilisé par le workflow GitHub « Nouveau produit » quand le mainteneur ajoute
l'étiquette « accepté » : python tools/issue_to_product.py issue.json
(issue.json = l'issue au format de l'API GitHub : title, body, number).
Écrit produits/<marque>/<référence>.yaml (+ la photo) et affiche le chemin de la fiche.
"""

from __future__ import annotations

import io
import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent / "produits"

# Libellés du formulaire (.github/ISSUE_TEMPLATE/nouveau-produit.yml) -> champ
LABELS = {
    "Marque": "marque",
    "Référence": "reference",
    "Nom en français": "nom_fr",
    "Nom en anglais": "nom_en",
    "Type": "type",
    "Profil EEP": "eep",
    "Autres profils émis": "eep_supplementaires",
    "Code fabricant EnOcean": "fabricant_id",
    "Mode d'appairage": "appairage",
    "Procédure d'appairage en français": "etapes_fr",
    "Procédure d'appairage en anglais": "etapes_en",
    "Nombre de canaux": "canaux",
    "Fonctions": "options",
    "Lien vers la notice": "notice",
    "Photo du produit": "photo",
    "Ce qui fonctionne déjà": "description",
    "Télégrammes": "telegrammes",
}
TYPES = ("actionneur", "prise", "interrupteur", "capteur", "chauffage")
MODES = ("ute_bidir", "ute_uni", "1bs", "4bs_bidir", "4bs", "rps")
# Mode d'appairage déduit du profil quand le contributeur ne le connaît pas
DEFAULT_MODE = {"F6": "rps", "D5": "1bs", "A5": "4bs", "D2": "ute_bidir"}
EMPTY = {"", "_No response_", "_Pas de réponse_", "None"}


class IssueError(ValueError):
    """Formulaire incomplet ou invalide (message affiché dans l'issue)."""


def parse_sections(body: str) -> dict[str, str]:
    """Corps d'une issue de formulaire (« ### Libellé » puis la valeur) -> champs."""
    out: dict[str, str] = {}
    for block in re.split(r"^### ", body or "", flags=re.MULTILINE)[1:]:
        label, _, value = block.partition("\n")
        value = value.strip()
        for prefix, key in LABELS.items():
            if any(part.strip().startswith(prefix) for part in label.split(" / ")):
                out[key] = "" if value in EMPTY else value
                break
    return out


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def lines(text: str) -> list[str]:
    out = []
    for line in (text or "").splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        if len(line) >= 3:
            out.append(line)
    return out


def eep_value(text: str) -> str | None:
    match = re.search(r"\b([0-9A-Fa-f]{2})[-‐ ]?([0-9A-Fa-f]{2})[-‐ ]?([0-9A-Fa-f]{2})\b", text or "")
    return "-".join(g.upper() for g in match.groups()) if match else None


def photo_url(text: str) -> str | None:
    match = re.search(r"https://[^\s)\"'>]+", text or "")
    return match.group(0) if match else None


def build(fields: dict[str, str]) -> tuple[str, dict]:
    """Champs du formulaire -> (identifiant « marque/référence », contenu de la fiche)."""
    brand = fields.get("marque", "").strip()
    ref = fields.get("reference", "").strip()
    eep = eep_value(fields.get("eep", ""))
    type_ = next((t for t in TYPES if fields.get("type", "").startswith(t)), None)
    steps_fr = lines(fields.get("etapes_fr", ""))
    steps_en = lines(fields.get("etapes_en", ""))
    errors = []
    if not brand:
        errors.append("Brand / Marque")
    if not ref:
        errors.append("Reference / Référence")
    if not eep:
        errors.append("EEP profile / Profil EEP (format A5-02-05)")
    if not type_:
        errors.append("Type")
    if not (steps_fr or steps_en):
        errors.append("Pairing steps in English or French / Procédure d'appairage en anglais ou français")
    if errors:
        raise IssueError("Missing or invalid fields / Champs manquants ou invalides :\n- "
                         + "\n- ".join(errors))

    mode = next((m for m in MODES if fields.get("appairage", "").startswith(m)), None)
    mode = mode or DEFAULT_MODE.get(eep[:2], "rps")
    name_en = fields.get("nom_en", "").strip()
    # The catalog schema requires a French fallback even for English-only submissions.
    names = {"fr": fields.get("nom_fr", "").strip() or name_en or ref}
    if name_en:
        names["en"] = name_en
    steps = {"fr": steps_fr or steps_en}
    if steps_en:
        steps["en"] = steps_en
    sheet: dict = {"ref": ref, "marque": brand, "nom": names, "type": type_, "eep": eep}
    extra = [e for e in (eep_value(p) for p in re.split(r"[,;/ ]+", fields.get(
        "eep_supplementaires", ""))) if e and e != eep]
    if extra:
        sheet["eep_supplementaires"] = sorted(set(extra))
    manufacturer = fields.get("fabricant_id", "").strip()
    if manufacturer:
        try:
            value = int(manufacturer, 16) if manufacturer.lower().startswith("0x") else int(
                manufacturer)
            if 0 <= value <= 2047:
                sheet["fabricant_id"] = value
        except ValueError:
            pass
    sheet["appairage"] = {"mode": mode, "etapes": steps}
    try:
        channels = int(fields.get("canaux", "").strip() or 1)
        if 1 < channels <= 8:
            sheet["canaux"] = channels
    except ValueError:
        pass
    options = fields.get("options", "")
    if re.search(r"\[[xX]\]\s*Mesure", options):
        sheet["mesure"] = True
    if re.search(r"\[[xX]\]\s*Remote Commissioning", options):
        sheet["recom"] = True
    sheet["reglages"] = ["timeout"] if type_ in ("capteur", "interrupteur") else []
    if not sheet["reglages"]:
        del sheet["reglages"]
    sheet["support"] = "communaute"
    notice = photo_url(fields.get("notice", ""))
    if notice:
        sheet["notice"] = notice
    notes = fields.get("description", "").strip()
    sheet["notes"] = (notes + "\n" if notes else "") + "À confirmer sur produit réel."
    return f"{slug(brand)}/{slug(ref)}", sheet


def _download(url: str, token: str | None) -> bytes:
    """Pièce jointe GitHub : github.com redirige vers un stockage externe qui refuse un
    jeton d'accès (HTTP 400). Le jeton n'est donc jamais transmis après la redirection,
    et on réessaie sans jeton si besoin (dépôt public)."""
    attempts = [token, None] if token and url.startswith("https://github.com/") else [None]
    last: Exception | None = None
    for auth in attempts:
        request = urllib.request.Request(url, headers={"User-Agent": "ocean2mqtt-bot"})
        if auth:
            request.add_unredirected_header("Authorization", f"Bearer {auth}")
        try:
            with urllib.request.urlopen(request, timeout=30) as resp:
                return resp.read()
        except Exception as err:  # noqa: BLE001
            last = err
    assert last is not None
    raise last


def save_photo(url: str, path: Path, token: str | None = None) -> None:
    """Télécharge la photo et l'enregistre en PNG carré 400 × 400, fond conservé."""
    from PIL import Image

    image = Image.open(io.BytesIO(_download(url, token))).convert("RGBA")
    side = max(image.size)
    square = Image.new("RGBA", (side, side), (255, 255, 255, 0))
    square.paste(image, ((side - image.width) // 2, (side - image.height) // 2))
    square.resize((400, 400), Image.LANCZOS).save(path, optimize=True)


def main() -> int:
    import os

    issue = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    fields = parse_sections(issue.get("body") or "")
    try:
        product_id, sheet = build(fields)
    except IssueError as err:
        print(f"ERREUR : {err}")
        return 1
    folder = ROOT / product_id.split("/")[0]
    folder.mkdir(parents=True, exist_ok=True)
    stem = product_id.split("/")[1]
    url = photo_url(fields.get("photo", ""))
    if url:
        try:
            save_photo(url, folder / f"{stem}.png", os.environ.get("GITHUB_TOKEN"))
            sheet["photo"] = f"{stem}.png"
        except Exception as err:  # noqa: BLE001
            print(f"Photo non récupérée ({err}) : fiche créée sans photo")
    sheet["notes"] += f" Proposé dans l'issue #{issue.get('number')}."
    path = folder / f"{stem}.yaml"
    path.write_text(yaml.safe_dump(sheet, allow_unicode=True, sort_keys=False, width=100),
                    encoding="utf-8")
    print(path.relative_to(ROOT.parent))
    return 0


if __name__ == "__main__":
    sys.exit(main())
