"""Pattern-level tests (no NLP model needed)."""

import pytest

from canpii import synthetic
from canpii.recognizers import (
    ALL_RECOGNIZERS,
    CaAbPhnRecognizer,
    CaBankAccountRecognizer,
    CaBcDriverLicenseRecognizer,
    CaBcPhnRecognizer,
    CaBusinessNumberRecognizer,
    CaOnDriverLicenseRecognizer,
    CaOnOhipRecognizer,
    CaPassportRecognizer,
    CaQcDriverLicenseRecognizer,
    CaQcRamqRecognizer,
)
from conftest import best, matches


@pytest.mark.parametrize("cls", ALL_RECOGNIZERS)
class TestConventions:
    def test_country_code(self, cls):
        assert cls.COUNTRY_CODE == "ca"
        assert cls().country_code() == "ca"

    @pytest.mark.parametrize("lang", ["en", "fr"])
    def test_language_instances(self, cls, lang):
        rec = cls(supported_language=lang)
        assert rec.supported_language == lang
        assert rec.supported_entities == [cls.ENTITY]
        assert rec.name == cls.__name__

    def test_context_is_bilingual(self, cls):
        ctx = set(cls.CONTEXT)
        french_markers = {
            "santé",
            "maladie",
            "passeport",
            "entreprise",
            "compte",
            "permis",
            "conduire",
            "banque",
        }
        assert ctx & french_markers, f"{cls.__name__} has no French context words"

    def test_patterns_are_portable(self, cls):
        for p in cls.PATTERNS:
            for token in ("(?=", "(?!", "(?<=", "(?<!", "\\1"):
                assert token not in p.regex, (cls.__name__, p.name)

    def test_overrides(self, cls):
        rec = cls(context=["foo"], supported_entity="MY_ENTITY", name="x")
        assert rec.context == ["foo"]
        assert rec.supported_entities == ["MY_ENTITY"]
        assert rec.name == "x"

    def test_bad_input_types_do_not_crash(self, cls):
        rec = cls()
        assert rec.analyze("", rec.supported_entities) == []
        rec.analyze("x" * 5000 + " 1234 " * 200, rec.supported_entities)


class TestOhip:
    rec = CaOnOhipRecognizer()

    def test_grouped_with_version_code(self):
        assert best(self.rec, "OHIP 1234-567-897 AB ok", "1234-567-897 AB") == pytest.approx(0.4)

    def test_failed_luhn_kept_but_lower(self):
        # Luhn is community-sourced: failure must not reject (recall first).
        assert best(self.rec, "OHIP 1234 567 890", "1234 567 890") == pytest.approx(0.3)

    def test_strict_mode_rejects_failed_luhn(self):
        strict = CaOnOhipRecognizer(strict=True)
        assert best(strict, "OHIP 1234 567 890", "1234 567 890") is None
        assert best(strict, "OHIP 1234 567 897", "1234 567 897") is not None

    def test_lowercase_word_not_swallowed_as_version_code(self):
        text = "number 1234 567 897 is valid"
        assert [t for t, _ in matches(self.rec, text)] == ["1234 567 897"]

    def test_bare_ten_digits_is_weak(self):
        score = best(self.rec, "x 1234567897 y", "1234567897")
        assert score is not None and score < 0.4

    @pytest.mark.parametrize("text", ["416-555-0123", "(416) 555-0123", "2024-11-05"])
    def test_phone_and_date_not_matched(self, text):
        assert matches(self.rec, text) == []


class TestRamq:
    rec = CaQcRamqRecognizer()

    def test_official_example(self):
        assert best(self.rec, "NAM BOUF 9451 1419", "BOUF 9451 1419") == pytest.approx(0.5)

    def test_compact(self):
        assert best(self.rec, "BOUF94511419", "BOUF94511419") == pytest.approx(0.5)

    def test_lowercase_lower_score(self):
        assert best(self.rec, "bouf 9451 1419", "bouf 9451 1419") == pytest.approx(0.35)

    @pytest.mark.parametrize("text", ["ROOM 1234 5678", "ABCD 9413 1419", "CODE 2024 3112"])
    def test_impossible_dates_rejected(self, text):
        assert matches(self.rec, text) == []


class TestBcPhn:
    rec = CaBcPhnRecognizer()

    def test_valid_grouped(self, rng):
        value = synthetic.bc_phn(rng)
        assert best(self.rec, f"PHN {value}", value) == pytest.approx(0.4)

    def test_valid_bare(self, rng):
        value = synthetic.bc_phn(rng, formatted=False)
        assert best(self.rec, f"PHN {value}", value) == pytest.approx(0.1)

    def test_bad_checksum_rejected(self, rng):
        value = synthetic.bc_phn_bad_check(rng)
        assert matches(self.rec, value) == []

    def test_sin_is_not_a_phn(self, rng):
        # SINs are 9 digits; a PHN is 10 - word boundaries keep them apart.
        sin = synthetic.sin(rng, formatted=False)
        assert matches(self.rec, f"SIN {sin}") == []


class TestAbPhn:
    rec = CaAbPhnRecognizer()

    def test_context_only(self):
        assert best(self.rec, "123456789", "123456789") == pytest.approx(0.01)
        assert best(self.rec, "12345-6789", "12345-6789") == pytest.approx(0.01)


class TestPassport:
    rec = CaPassportRecognizer()

    def test_match(self):
        assert best(self.rec, "passport AB123456", "AB123456") == pytest.approx(0.1)

    def test_lowercase_not_matched(self):
        assert matches(self.rec, "sku ab123456") == []

    def test_wrong_shape(self):
        assert matches(self.rec, "A1234567 ABC123456 AB1234567") == []


class TestBusinessNumber:
    rec = CaBusinessNumberRecognizer()

    @pytest.mark.parametrize(
        "value", ["123456782 RT 0001", "123456782RT0001", "123456782-RP-0002", "123456782 rc 0001"]
    )
    def test_program_account_luhn_valid(self, value):
        assert best(self.rec, f"BN {value}", value) == pytest.approx(0.7)

    def test_program_account_luhn_invalid_kept(self):
        assert best(self.rec, "123456789 RT 0001", "123456789 RT 0001") == pytest.approx(0.6)

    def test_unknown_program_not_matched_as_account(self):
        assert [t for t, _ in matches(self.rec, "123456782 XX 0001")] == ["123456782"]

    def test_bare_is_weak(self):
        assert best(self.rec, "123456782", "123456782") == pytest.approx(0.15)
        assert best(self.rec, "123456789", "123456789") == pytest.approx(0.05)


class TestBank:
    rec = CaBankAccountRecognizer()

    def test_micr(self):
        assert best(self.rec, "transit 12345-678", "12345-678") == pytest.approx(0.15)

    def test_electronic(self):
        assert best(self.rec, "routing 000312345", "000312345") == pytest.approx(0.05)

    def test_account(self):
        assert best(self.rec, "account 1234567", "1234567") == pytest.approx(0.01)

    def test_zip_plus_four_not_micr(self):
        assert matches(self.rec, "90210-1234") == []


class TestDriverLicences:
    def test_ontario(self):
        rec = CaOnDriverLicenseRecognizer()
        assert best(rec, "A1234-56789-50615", "A1234-56789-50615") == pytest.approx(0.4)
        assert best(rec, "A12345678950615", "A12345678950615") == pytest.approx(0.4)
        # implausible date: kept (community rule), no bonus
        assert best(rec, "A1234-56789-51315", "A1234-56789-51315") == pytest.approx(0.3)
        assert (
            best(CaOnDriverLicenseRecognizer(strict=True), "A1234-56789-51315", "A1234-56789-51315")
            is None
        )

    def test_quebec(self):
        rec = CaQcDriverLicenseRecognizer()
        assert best(rec, "L1234-123456-12", "L1234-123456-12") == pytest.approx(0.2)
        assert best(rec, "L123412345612", "L123412345612") == pytest.approx(0.1)
        assert matches(rec, "L12341234561") == []

    def test_bc(self):
        rec = CaBcDriverLicenseRecognizer()
        assert best(rec, "licence 1234567", "1234567") == pytest.approx(0.01)
        assert matches(rec, "12345678") == []


class TestNegativeContext:
    def test_weak_match_after_phone_word_dropped(self):
        rec = CaOnOhipRecognizer()
        assert matches(rec, "Call the health clinic at 4165550123.") == []
        assert matches(rec, "Appelez la clinique au 4165550123.") == []

    def test_weak_match_without_negative_word_kept(self):
        rec = CaOnOhipRecognizer()
        assert matches(rec, "Health card 4165550123.") != []

    def test_strong_match_not_affected(self):
        rec = CaBusinessNumberRecognizer()
        assert best(rec, "order 123456782 RT 0001", "123456782 RT 0001") == pytest.approx(0.7)

    def test_word_boundaries(self):
        # "tel" must not fire inside "hotel"; "poste" not inside "composte".
        rec = CaBankAccountRecognizer()
        assert matches(rec, "Hotel account 1234567") != []

    def test_can_be_disabled_by_subclass(self):
        class NoNegative(CaOnOhipRecognizer):
            NEGATIVE_CONTEXT = ()

        assert matches(NoNegative(), "Call 4165550123") != []
