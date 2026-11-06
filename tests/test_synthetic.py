import pytest

from canpii import synthetic
from canpii import validators as v

CHECKS = {
    "ohip": lambda s: v.ohip_structure_valid(s) and v.ohip_luhn_valid(s),
    "ramq": v.ramq_valid,
    "bc_phn": v.bc_phn_valid,
    "ab_phn": v.ab_phn_structure_valid,
    "passport": v.passport_structure_valid,
    "bn": lambda s: v.bn_structure_valid(s) and v.bn_luhn_valid(s),
    "bank_transit": v.micr_transit_structure_valid,
    "bank_routing": v.electronic_routing_structure_valid,
    "on_dl": v.on_dl_birthdate_plausible,
    "qc_dl": v.qc_dl_structure_valid,
    "bc_dl": v.bc_dl_structure_valid,
    "sin": lambda s: v.luhn_valid(v.digits_only(s)) and s[0] not in "08",
}


@pytest.mark.parametrize("kind", sorted(CHECKS))
@pytest.mark.parametrize("formatted", [True, False])
def test_generated_values_pass_validators(kind, formatted):
    for value in synthetic.generate(kind, n=100, seed=7, formatted=formatted):
        assert CHECKS[kind](value), (kind, value)


def test_near_misses_fail_official_rules():
    for value in synthetic.generate("bc_phn_bad_check", n=100, seed=3):
        assert not v.bc_phn_valid(value)
    for value in synthetic.generate("ramq_bad_date", n=100, seed=3):
        assert not v.ramq_valid(value)
    for value in synthetic.generate("bn_bad_program", n=100, seed=3):
        assert not v.bn_structure_valid(value)


def test_generation_is_deterministic():
    assert synthetic.generate("ohip", n=5, seed=1) == synthetic.generate("ohip", n=5, seed=1)


def test_unknown_kind():
    with pytest.raises(KeyError):
        synthetic.generate("nope")


def test_corpus_spans_point_at_values():
    corpus = synthetic.build_corpus(n_per_template=2, seed=1)
    assert {ex.language for ex in corpus} == {"en", "fr"}
    for ex in corpus:
        for span in ex.spans:
            value = ex.text[span.start : span.end]
            assert value.strip() == value and value
    assert any(not ex.spans for ex in corpus)
