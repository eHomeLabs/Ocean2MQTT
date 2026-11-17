"""Description d'un produit de la bibliothèque (chargée depuis une fiche YAML)."""

from __future__ import annotations

from dataclasses import dataclass, field

# Types d'appairage
TEACH_UTE_BIDIR = "ute_bidir"  # le produit envoie une requête UTE, la passerelle répond
TEACH_UTE_UNI = "ute_uni"  # requête UTE sans réponse attendue
TEACH_1BS = "1bs"  # télégramme 1BS avec bit LRN
TEACH_4BS = "4bs"  # télégramme 4BS avec bit LRN
TEACH_4BS_BIDIR = "4bs_bidir"  # teach-in 4BS avec réponse de la passerelle (vanne)
TEACH_RPS = "rps"  # premier appui de touche reçu

TEACH_MODES = (TEACH_UTE_BIDIR, TEACH_UTE_UNI, TEACH_1BS, TEACH_4BS, TEACH_4BS_BIDIR, TEACH_RPS)

# Niveaux de support affichés dans l'interface
SUPPORT_VALIDE = "valide"
SUPPORT_COMMUNAUTE = "communaute"
SUPPORT_LEVELS = (SUPPORT_VALIDE, SUPPORT_COMMUNAUTE)


@dataclass(frozen=True)
class Product:
    """Un produit décrit par sa fiche (voir produits/schema.json)."""

    id: str  # identifiant unique et stable (ex. « nodon/sin-2-fp-01 »)
    brand: str
    model: str
    eep: str
    teach_in: str
    names: dict[str, str]
    pairing_steps: dict[str, tuple[str, ...]]
    type: str = "actionneur"
    channels: int = 1
    metering: bool = False
    decoder: str | None = None  # décodeur particulier (sinon déduit de l'EEP)
    extra_eeps: tuple[str, ...] = ()  # autres profils émis par le même produit
    settings: frozenset[str] = frozenset()
    recom: bool = False
    support: str = SUPPORT_COMMUNAUTE
    manufacturer_id: int | None = None
    manual: str | None = None
    image: str | None = None  # chemin de la photo, relatif à la fiche
    after: dict[str, str] = field(default_factory=dict)
    variants: tuple[str, ...] = ()

    @property
    def is_actuator(self) -> bool:
        """Le produit reçoit des télégrammes de la passerelle (adresse d'émission dédiée)."""
        return self.teach_in in (TEACH_UTE_BIDIR, TEACH_4BS_BIDIR)

    @property
    def rorg_func_type(self) -> tuple[int, int, int]:
        rorg, func, type_ = (int(x, 16) for x in self.eep.split("-"))
        return rorg, func, type_

    @property
    def references(self) -> str:
        """Références commerciales complètes (ex. « ASP-2-1-00 / ASP-2-1-10 »)."""
        return " / ".join(self.variants) if self.variants else self.model

    def _text(self, values: dict, lang: str, default=""):
        for key in (lang[:2], "en", "fr"):
            if key in values:
                return values[key]
        return default

    def name(self, lang: str = "fr") -> str:
        return self._text(self.names, lang, self.model)

    def steps(self, lang: str = "fr") -> tuple[str, ...]:
        return self._text(self.pairing_steps, lang, ())

    def pairing(self, lang: str = "fr") -> str:
        """Procédure en un seul texte (compatibilité avec les assistants existants)."""
        return " ".join(self.steps(lang))

    def after_text(self, lang: str = "fr") -> str:
        return self._text(self.after, lang)

    def has(self, setting: str) -> bool:
        return setting in self.settings
