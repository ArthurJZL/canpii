"""Shared bilingual (English / French) context word lists.

Presidio's default ``LemmaContextAwareEnhancer`` compares each context word
against the *lemmas of single tokens* near a match, using case-insensitive
**substring** matching. Two consequences shape these lists:

* Multi-word phrases ("health card") never match as a whole, so we list the
  distinctive single tokens instead ("health", "card", "carte", "santé").
* Very short or generic words cause accidental boosts by substring match
  ("dl" is inside "handle", "nam" inside "name", "tps" inside "https", "cra"
  inside "democracy", "number" / "numéro" sit next to every phone number),
  so they are deliberately excluded.
"""

HEALTH_EN = ["health", "medical", "patient", "card", "hcn"]
HEALTH_FR = ["santé", "sante", "maladie", "carte", "médical", "medical"]

DRIVER_EN = ["driver", "licence", "license", "licensed"]
DRIVER_FR = ["permis", "conduire", "conducteur"]

BANK_EN = [
    "bank",
    "banking",
    "account",
    "transit",
    "institution",
    "routing",
    "branch",
    "cheque",
    "chequing",
    "deposit",
]
BANK_FR = ["banque", "bancaire", "compte", "succursale", "chèque", "dépôt", "depot", "virement"]
