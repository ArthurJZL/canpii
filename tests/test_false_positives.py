"""Generic numbers must not be reported at the recommended 0.4 threshold."""

import pytest

from canpii import synthetic
from conftest import CA_ENTITIES

pytestmark = pytest.mark.nlp

GENERIC = [
    ("en", "Call 416-555-0123 or (514) 555-0199 before 5 pm."),
    ("en", "Call 4165550123 for details."),
    ("en", "The meeting is on 2026-11-05 at 10:30."),
    ("en", "Your order ORD-20261105 has shipped, tracking 1Z999AA10123456784."),
    ("en", "Invoice 1234567 totals $12,345.67."),
    ("en", "Room 1234 5678 is on floor 12."),
    ("en", "Product SKU ab123456 is in aisle 7."),
    ("fr", "Appelez-nous au 514-555-0188, poste 1234567."),
    ("fr", "La réunion aura lieu le 2026-11-05."),
    ("fr", "Votre commande 123456789 a été expédiée."),
]


@pytest.mark.parametrize(("lang", "text"), GENERIC)
def test_generic_numbers(analyzer, lang, text):
    results = analyzer.analyze(text, language=lang, entities=CA_ENTITIES)
    assert results == [], [(r.entity_type, text[r.start : r.end], r.score) for r in results]


def test_phone_numbers_bulk(analyzer):
    for value in synthetic.generate("phone", n=60, seed=11):
        text = f"Please call {value} tomorrow."
        assert analyzer.analyze(text, language="en", entities=CA_ENTITIES) == [], text


def test_near_miss_bc_phn_not_reported_as_phn(analyzer):
    # A wrong MOD-11 digit is rejected by the BC recognizer. Without context
    # it may still look like an OHIP number only if it passes Luhn, which we
    # exclude here to test the BC rule in isolation.
    from canpii import validators as v

    for value in synthetic.generate("bc_phn_bad_check", n=40, seed=5):
        if v.ohip_luhn_valid(value):
            continue
        results = analyzer.analyze(f"Ref {value}", language="en", entities=CA_ENTITIES)
        assert results == [], value


def test_sin_with_context_is_sin_not_health_number(analyzer, rng):
    sin = synthetic.sin(rng)
    text = f"Social insurance number: {sin}"
    types = {r.entity_type for r in analyzer.analyze(text, language="en", entities=CA_ENTITIES)}
    assert types == {"CA_SIN"}


def test_bc_phn_with_context_is_not_sin(analyzer, rng):
    phn = synthetic.bc_phn(rng)
    text = f"Personal health number {phn}"
    types = {r.entity_type for r in analyzer.analyze(text, language="en", entities=CA_ENTITIES)}
    assert types == {"CA_HEALTH_NUMBER"}
