"""Synthetic test data: fake identifiers with valid structure/checksums.

Everything here is generated from a pseudo-random number generator. Values
are *structurally* valid (they pass the same checks as the recognizers) but
are not looked up anywhere and are not derived from real people. Because the
identifier spaces are finite, a generated value can still coincide with an
issued identifier by chance: use the output only for testing detection, never
for anything that treats it as a real identifier, and never commit real
identifiers to this repository.

Pure standard library; no Presidio dependency.
"""

from __future__ import annotations

import random
import string
from collections.abc import Callable
from dataclasses import dataclass

from canpii import validators as v

__all__ = [
    "GENERATORS",
    "NEAR_MISSES",
    "NEGATIVES",
    "LabeledExample",
    "Span",
    "build_corpus",
    "generate",
]

Rng = random.Random


def _digits(rng: Rng, n: int, first_nonzero: bool = False) -> str:
    s = "".join(rng.choice(string.digits) for _ in range(n))
    if first_nonzero and s[0] == "0":
        s = str(rng.randint(1, 9)) + s[1:]
    return s


def _letters(rng: Rng, n: int) -> str:
    return "".join(rng.choice(string.ascii_uppercase) for _ in range(n))


def _yymmdd(rng: Rng, female_offset: bool) -> str:
    yy = rng.randint(0, 99)
    mm = rng.randint(1, 12)
    dd = rng.randint(1, 28)
    if female_offset and rng.random() < 0.5:
        mm += 50
    return f"{yy:02d}{mm:02d}{dd:02d}"


# -- valid generators -------------------------------------------------------


def ohip(rng: Rng, formatted: bool = True) -> str:
    """Ontario health number with a Luhn-valid check digit and optional version code."""
    base = _digits(rng, 9, first_nonzero=True)
    num = base + v.luhn_check_digit(base)
    vc = _letters(rng, rng.choice([0, 1, 2]))
    core = f"{num[:4]}-{num[4:7]}-{num[7:]}" if formatted else num
    if formatted and rng.random() < 0.5:
        core = core.replace("-", " ")
    return f"{core} {vc}".strip() if vc else core


def bc_phn(rng: Rng, formatted: bool = True) -> str:
    """BC PHN with a valid MOD-11 check digit."""
    while True:
        first = "9" + _digits(rng, 8)
        check = v.bc_phn_check_digit(first)
        if check is not None:
            num = first + str(check)
            return f"{num[:4]} {num[4:7]} {num[7:]}" if formatted else num


def ab_phn(rng: Rng, formatted: bool = False) -> str:
    """Alberta PHN (9 digits, no published checksum)."""
    num = _digits(rng, 9, first_nonzero=True)
    return f"{num[:5]}-{num[5:]}" if formatted else num


def ramq(rng: Rng, formatted: bool = True) -> str:
    """Quebec NAM with a plausible embedded birth date."""
    letters = _letters(rng, 4)
    body = _yymmdd(rng, female_offset=True) + _digits(rng, 2)
    if formatted:
        return f"{letters} {body[:4]} {body[4:]}"
    return letters + body


def passport(rng: Rng, formatted: bool = True) -> str:
    """Two letters + six digits."""
    return _letters(rng, 2) + _digits(rng, 6)


def bn(rng: Rng, formatted: bool = True) -> str:
    """Generate a Luhn-valid Business Number root, or a program account."""
    base = _digits(rng, 8, first_nonzero=True)
    root = base + v.luhn_check_digit(base)
    if not formatted:
        return root
    program = rng.choice(sorted(v.BN_PROGRAM_IDENTIFIERS))
    return f"{root} {program} {_digits(rng, 4)}"


def bank_transit(rng: Rng, formatted: bool = True) -> str:
    """MICR transit-institution ``TTTTT-III``."""
    return f"{_digits(rng, 5)}-{_digits(rng, 3)}"


def bank_routing(rng: Rng, formatted: bool = True) -> str:
    """Electronic routing ``0IIITTTTT``."""
    return "0" + _digits(rng, 3) + _digits(rng, 5)


def bank_account(rng: Rng, formatted: bool = True) -> str:
    """7-12 digit account number."""
    return _digits(rng, rng.randint(7, 12), first_nonzero=True)


def on_dl(rng: Rng, formatted: bool = True) -> str:
    """Ontario licence ``A1234-56789-01234`` with a plausible YYMMDD tail."""
    num = _digits(rng, 8) + _yymmdd(rng, female_offset=True)
    s = _letters(rng, 1) + num
    return f"{s[:5]}-{s[5:10]}-{s[10:]}" if formatted else s


def qc_dl(rng: Rng, formatted: bool = True) -> str:
    """Quebec licence: letter + 12 digits."""
    s = _letters(rng, 1) + _digits(rng, 12)
    return f"{s[:5]}-{s[5:11]}-{s[11:]}" if formatted else s


def bc_dl(rng: Rng, formatted: bool = True) -> str:
    """BC licence: 7 digits."""
    return _digits(rng, 7, first_nonzero=True)


def sin(rng: Rng, formatted: bool = True) -> str:
    """SIN (upstream entity) with a valid Luhn digit; first digit not 0 or 8."""
    base = rng.choice("12345679") + _digits(rng, 7)
    num = base + v.luhn_check_digit(base)
    return f"{num[:3]} {num[3:6]} {num[6:]}" if formatted else num


# -- near-misses (look right, fail an official rule) ------------------------


def bc_phn_bad_check(rng: Rng) -> str:
    """Correct shape, wrong MOD-11 check digit."""
    while True:
        num = "9" + _digits(rng, 9)
        if not v.bc_phn_valid(num):
            return f"{num[:4]} {num[4:7]} {num[7:]}"


def ramq_bad_date(rng: Rng) -> str:
    """Correct shape, impossible birth month."""
    month = rng.choice([0, 13, 25, 49, 50, 63, 77, 99])
    yy, dd = rng.randint(0, 99), rng.randint(1, 28)
    return f"{_letters(rng, 4)} {yy:02d}{month:02d} {dd:02d}{_digits(rng, 2)}"


def bn_bad_program(rng: Rng) -> str:
    """9 digits + a program identifier CRA does not use."""
    root = _digits(rng, 9, first_nonzero=True)
    return f"{root} {rng.choice(['XX', 'AB', 'QQ', 'ZZ'])} {_digits(rng, 4)}"


# -- generic negatives (should not be detected without context) ------------


def phone(rng: Rng) -> str:
    """NANP phone number in the fictional 555-01xx range."""
    area = rng.choice(["416", "514", "604", "403", "613", "905", "438"])
    fmt = rng.choice(["{a}-555-01{x}", "({a}) 555-01{x}", "{a}55501{x}", "+1 {a} 555 01{x}"])
    return fmt.format(a=area, x=_digits(rng, 2))


def iso_date(rng: Rng) -> str:
    return f"{rng.randint(1990, 2030)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"


def order_id(rng: Rng) -> str:
    fmt = rng.choice(["ORD-{d}", "INV{d}", "PO-{y}-{s}", "#{d}", "{d}"])
    return fmt.format(
        d=_digits(rng, rng.randint(6, 10)), y=rng.randint(2020, 2030), s=_digits(rng, 5)
    )


def amount(rng: Rng) -> str:
    return f"${rng.randint(1, 99999):,}.{_digits(rng, 2)}"


#: name -> (entity, generator) for valid values
GENERATORS: dict[str, tuple[str, Callable[..., str]]] = {
    "ohip": ("CA_HEALTH_NUMBER", ohip),
    "ramq": ("CA_HEALTH_NUMBER", ramq),
    "bc_phn": ("CA_HEALTH_NUMBER", bc_phn),
    "ab_phn": ("CA_HEALTH_NUMBER", ab_phn),
    "passport": ("CA_PASSPORT", passport),
    "bn": ("CA_BN", bn),
    "bank_transit": ("CA_BANK_ACCOUNT", bank_transit),
    "bank_routing": ("CA_BANK_ACCOUNT", bank_routing),
    "bank_account": ("CA_BANK_ACCOUNT", bank_account),
    "on_dl": ("CA_DRIVER_LICENSE", on_dl),
    "qc_dl": ("CA_DRIVER_LICENSE", qc_dl),
    "bc_dl": ("CA_DRIVER_LICENSE", bc_dl),
    "sin": ("CA_SIN", sin),
}

NEAR_MISSES: dict[str, Callable[[Rng], str]] = {
    "bc_phn_bad_check": bc_phn_bad_check,
    "ramq_bad_date": ramq_bad_date,
    "bn_bad_program": bn_bad_program,
}

NEGATIVES: dict[str, Callable[[Rng], str]] = {
    "phone": phone,
    "iso_date": iso_date,
    "order_id": order_id,
    "amount": amount,
}


def generate(kind: str, n: int = 1, seed: int | None = None, formatted: bool = True) -> list[str]:
    """Generate ``n`` values of ``kind`` (a key of GENERATORS, NEAR_MISSES or NEGATIVES)."""
    rng = random.Random(seed)
    if kind in GENERATORS:
        fn = GENERATORS[kind][1]
        return [fn(rng, formatted) for _ in range(n)]
    if kind in NEAR_MISSES:
        return [NEAR_MISSES[kind](rng) for _ in range(n)]
    if kind in NEGATIVES:
        return [NEGATIVES[kind](rng) for _ in range(n)]
    known = sorted([*GENERATORS, *NEAR_MISSES, *NEGATIVES])
    raise KeyError(f"Unknown kind {kind!r}; choose one of {known}")


# -- labeled bilingual corpus ----------------------------------------------

# Templates: "{v}" is the identifier. "ctx" templates contain a context word
# within five tokens before the value; "bare" templates do not.
_TEMPLATES: dict[str, dict[str, dict[str, list[str]]]] = {
    "ohip": {
        "en": {
            "ctx": ["Patient OHIP number: {v}.", "Her Ontario health card is {v}, please verify."],
            "bare": ["Reference {v} was assigned yesterday."],
        },
        "fr": {
            "ctx": [
                "Numéro de carte santé de l'Ontario : {v}.",
                "Assurance santé OHIP {v} vérifiée.",
            ],
            "bare": ["La référence {v} a été attribuée hier."],
        },
    },
    "ramq": {
        "en": {
            "ctx": ["RAMQ health insurance number {v} on file.", "Quebec health card: {v}"],
            "bare": ["Code {v} appears on the form."],
        },
        "fr": {
            "ctx": ["Numéro d'assurance maladie : {v}", "Carte RAMQ {v} expirée."],
            "bare": ["Le code {v} figure sur le formulaire."],
        },
    },
    "bc_phn": {
        "en": {
            "ctx": ["BC PHN {v} confirmed by MSP.", "Personal health number: {v}"],
            "bare": ["Ticket {v} closed."],
        },
        "fr": {
            "ctx": ["Numéro de santé personnel (PHN) : {v}", "Carte santé de C.-B. {v}"],
            "bare": ["Le billet {v} est fermé."],
        },
    },
    "ab_phn": {
        "en": {
            "ctx": ["Alberta AHCIP health number {v}.", "AHCIP personal health number: {v}"],
            "bare": ["Batch {v} shipped."],
        },
        "fr": {
            "ctx": ["Numéro de santé de l'Alberta (AHCIP) : {v}", "Carte santé Alberta {v}"],
            "bare": ["Le lot {v} a été expédié."],
        },
    },
    "passport": {
        "en": {
            "ctx": ["Canadian passport number {v}, expires 2031.", "Passport: {v}"],
            "bare": ["Item {v} is back in stock."],
        },
        "fr": {
            "ctx": ["Numéro de passeport canadien : {v}", "Passeport {v} valide."],
            "bare": ["L'article {v} est de retour en stock."],
        },
    },
    "bn": {
        "en": {
            "ctx": ["Our GST/HST business number is {v}.", "Business number (BN): {v}"],
            "bare": ["See record {v}."],
        },
        "fr": {
            "ctx": ["Numéro d'entreprise (TPS/TVH) : {v}", "Le numéro d'entreprise est {v}."],
            "bare": ["Voir le dossier {v}."],
        },
    },
    "bank_transit": {
        "en": {
            "ctx": ["Bank transit and institution: {v}.", "Direct deposit to branch transit {v}."],
            "bare": ["Part {v} replaced."],
        },
        "fr": {
            "ctx": ["Numéro de transit et d'institution bancaire : {v}", "Succursale {v}."],
            "bare": ["Pièce {v} remplacée."],
        },
    },
    "bank_routing": {
        "en": {
            "ctx": ["EFT routing number for the bank: {v}"],
            "bare": ["Sequence {v} started."],
        },
        "fr": {
            "ctx": ["Numéro d'acheminement bancaire : {v}"],
            "bare": ["La séquence {v} a commencé."],
        },
    },
    "bank_account": {
        "en": {
            "ctx": ["Chequing account number {v}.", "Deposit to bank account {v}."],
            "bare": ["Order {v} was refunded."],
        },
        "fr": {
            "ctx": ["Numéro de compte bancaire : {v}", "Dépôt au compte {v}."],
            "bare": ["La commande {v} a été remboursée."],
        },
    },
    "on_dl": {
        "en": {
            "ctx": ["Ontario driver's licence {v}.", "Driver licence number: {v}"],
            "bare": ["Serial {v} logged."],
        },
        "fr": {
            "ctx": ["Permis de conduire de l'Ontario : {v}", "Numéro de permis {v}."],
            "bare": ["Numéro de série {v} enregistré."],
        },
    },
    "qc_dl": {
        "en": {
            "ctx": ["SAAQ driver's licence {v}.", "Quebec driver licence: {v}"],
            "bare": ["Asset {v} retired."],
        },
        "fr": {
            "ctx": ["Permis de conduire SAAQ : {v}", "Numéro de permis de conduire {v}"],
            "bare": ["L'actif {v} est retiré."],
        },
    },
    "bc_dl": {
        "en": {
            "ctx": ["ICBC driver's licence {v}.", "BC driver licence number: {v}"],
            "bare": ["Room {v} is booked."],
        },
        "fr": {
            "ctx": ["Permis de conduire ICBC : {v}", "Permis de conduire de la C.-B. {v}"],
            "bare": ["La salle {v} est réservée."],
        },
    },
    "sin": {
        "en": {
            "ctx": ["Social insurance number (SIN): {v}"],
            "bare": ["Tracking {v} delivered."],
        },
        "fr": {
            "ctx": ["Numéro d'assurance sociale (NAS) : {v}"],
            "bare": ["Le suivi {v} est livré."],
        },
    },
}

_NEGATIVE_TEMPLATES: dict[str, list[str]] = {
    "en": [
        "Call us at {v} for support.",
        "The meeting is on {v}.",
        "Your order {v} has shipped.",
        "Total due: {v}.",
        "Reference near-miss {v} in the log.",
    ],
    "fr": [
        "Appelez-nous au {v} pour du soutien.",
        "La réunion a lieu le {v}.",
        "Votre commande {v} a été expédiée.",
        "Montant dû : {v}.",
        "Référence {v} dans le journal.",
    ],
}


# Hard negatives: a context word is present, but the number is not an
# identifier. These measure context-induced false positives.
_HARD_NEGATIVE_TEMPLATES: dict[str, list[tuple[str, str]]] = {
    "en": [
        ("phone", "Call the health clinic at {v}."),
        ("phone", "Bank branch phone: {v}"),
        ("amount", "Driver's licence renewal fee: {v}."),
        ("iso_date", "Bank account opened on {v}."),
        ("order_id", "Passport office ticket {v} is ready."),
        ("order_id", "Business account order {v} was refunded."),
        ("iso_date", "Health card appointment on {v}."),
    ],
    "fr": [
        ("phone", "Appelez la clinique santé au {v}."),
        ("phone", "Téléphone de la succursale bancaire : {v}"),
        ("amount", "Frais de permis de conduire : {v}."),
        ("iso_date", "Compte bancaire ouvert le {v}."),
        ("order_id", "Billet du bureau des passeports {v}."),
        ("order_id", "Commande {v} de l'entreprise remboursée."),
        ("iso_date", "Rendez-vous carte santé le {v}."),
    ],
}

# Hard negatives that were deliberately *not* used while tuning scores and
# negative-context words. They keep the benchmark honest: a context word is
# right next to an unrelated number, which no pattern recognizer can resolve.
_UNTUNED_NEGATIVE_TEMPLATES: dict[str, list[str]] = {
    "en": [
        "Patient chart {v} updated.",
        "Driver ID {v} assigned to route 12.",
        "Bank statement page {v}.",
        "Passport photo booth receipt {v}.",
    ],
    "fr": [
        "Dossier patient {v} mis à jour.",
        "Chauffeur {v} affecté au trajet 12.",
        "Relevé bancaire, page {v}.",
        "Reçu photo passeport {v}.",
    ],
}


@dataclass(frozen=True)
class Span:
    """Gold annotation."""

    entity: str
    start: int
    end: int


@dataclass(frozen=True)
class LabeledExample:
    """One synthetic sentence with gold spans."""

    text: str
    language: str
    kind: str
    has_context: bool
    spans: tuple[Span, ...]


def build_corpus(n_per_template: int = 5, seed: int = 2026) -> list[LabeledExample]:
    """Build a labeled bilingual corpus of positives, near-misses and negatives.

    "bare" templates (no context word) are still labeled as positives: they
    measure how much each recognizer depends on context.
    """
    rng = random.Random(seed)
    out: list[LabeledExample] = []
    for kind, by_lang in _TEMPLATES.items():
        entity, fn = GENERATORS[kind]
        for lang, groups in by_lang.items():
            for group, templates in groups.items():
                for template in templates:
                    for _ in range(n_per_template):
                        value = fn(rng, rng.random() < 0.7)
                        text = template.replace("{v}", value)
                        start = template.index("{v}")
                        out.append(
                            LabeledExample(
                                text,
                                lang,
                                kind,
                                group == "ctx",
                                (Span(entity, start, start + len(value)),),
                            )
                        )
    negatives: list[tuple[str, Callable[[Rng], str]]] = [
        *NEGATIVES.items(),
        *NEAR_MISSES.items(),
    ]
    for lang, templates in _NEGATIVE_TEMPLATES.items():
        for kind, fn in negatives:
            for _ in range(n_per_template * 4):
                template = rng.choice(templates)
                out.append(LabeledExample(template.replace("{v}", fn(rng)), lang, kind, False, ()))
    for lang, pairs in _HARD_NEGATIVE_TEMPLATES.items():
        for kind, template in pairs:
            for _ in range(n_per_template * 2):
                value = NEGATIVES[kind](rng)
                out.append(
                    LabeledExample(template.replace("{v}", value), lang, f"hard_{kind}", True, ())
                )
    for lang, templates in _UNTUNED_NEGATIVE_TEMPLATES.items():
        for template in templates:
            for _ in range(n_per_template * 2):
                value = _digits(rng, rng.choice([7, 9, 10]), first_nonzero=True)
                out.append(
                    LabeledExample(template.replace("{v}", value), lang, "untuned", True, ())
                )
    return out
