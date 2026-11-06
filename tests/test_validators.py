import random

import pytest

from canpii import synthetic
from canpii import validators as v


class TestLuhn:
    @pytest.mark.parametrize("digits", ["79927398713", "046454286", "0"])
    def test_valid(self, digits):
        assert v.luhn_valid(digits)

    @pytest.mark.parametrize("digits", ["79927398710", "046454287", "", "12a4"])
    def test_invalid(self, digits):
        assert not v.luhn_valid(digits)

    def test_check_digit_roundtrip(self):
        assert v.luhn_check_digit("7992739871") == "3"


class TestBcPhn:
    def test_generated_numbers_are_valid(self):
        rng = random.Random(1)
        for _ in range(200):
            assert v.bc_phn_valid(synthetic.bc_phn(rng))

    def test_every_other_check_digit_is_invalid(self):
        rng = random.Random(2)
        num = synthetic.bc_phn(rng, formatted=False)
        for d in "0123456789":
            candidate = num[:9] + d
            assert v.bc_phn_valid(candidate) == (d == num[9])

    def test_first_digit_must_be_nine(self):
        assert v.bc_phn_check_digit("812345678") is None
        assert not v.bc_phn_valid("8123456789")

    def test_hand_computed_example(self):
        # Digits 2-9 of 912345678x: 1,2,3,4,5,6,7,8 with weights 2,4,8,5,10,9,7,3
        # products mod 11: 2,8,2,9,6,10,5,2 -> sum 44 -> 44 % 11 = 0 -> 11 - 0 = 11
        # -> no valid check digit exists for this prefix.
        assert v.bc_phn_check_digit("912345678") is None
        # 9000000010: digit 9 (weight 3) = 1 -> 3 -> 11 - 3 = 8
        assert v.bc_phn_check_digit("900000001") == 8
        assert v.bc_phn_valid("9000 000 018")

    def test_wrong_length(self):
        assert not v.bc_phn_valid("912345678")
        assert not v.bc_phn_valid("91234567890")


class TestOhip:
    @pytest.mark.parametrize(
        "text", ["1234567897", "1234-567-897", "1234 567 897 AB", "1234567897A"]
    )
    def test_structure(self, text):
        assert v.ohip_structure_valid(text)

    @pytest.mark.parametrize("text", ["123456789", "12345678901", "1234567897ABC", "A234567897"])
    def test_bad_structure(self, text):
        assert not v.ohip_structure_valid(text)

    def test_luhn_is_separate_from_structure(self):
        assert v.ohip_luhn_valid("1234 567 897 AB")
        assert v.ohip_structure_valid("1234 567 890") and not v.ohip_luhn_valid("1234 567 890")


class TestRamq:
    def test_official_example(self):
        # Example from the Quebec MSSS "marqueur X" leaflet: BOUF 9451 1419,
        # female (month 51 = January + 50), born on the 14th.
        info = v.ramq_parse("BOUF 9451 1419")
        assert info is not None
        assert info.letters == "BOUF"
        assert info.birth_year_2d == 94
        assert info.birth_month == 1
        assert info.birth_day == 14
        assert info.female is True
        assert info.admin_code == "19"

    @pytest.mark.parametrize(
        "text",
        [
            "ABCD 9413 1419",  # month 13
            "ABCD 9450 1419",  # month 50
            "ABCD 9463 1419",  # month 63
            "ABCD 9402 3019",  # 30 February
            "ABCD 9404 3119",  # 31 April
            "ABCD 9401 0019",  # day 0
            "ABC 9401 0119",  # 3 letters
        ],
    )
    def test_invalid(self, text):
        assert not v.ramq_valid(text)

    def test_leap_day_accepted(self):
        assert v.ramq_valid("ABCD 0002 2901")


class TestBusinessNumber:
    def test_program_identifiers_from_cra(self):
        assert {"RT", "RP", "RC", "RM", "RR", "RZ"} <= v.BN_PROGRAM_IDENTIFIERS

    @pytest.mark.parametrize(
        "text", ["123456782", "123456782 RT 0001", "123456782RT0001", "123456782-RP-0002"]
    )
    def test_structure(self, text):
        assert v.bn_structure_valid(text)

    def test_unknown_program(self):
        assert not v.bn_structure_valid("123456782 XX 0001")

    def test_luhn(self):
        assert v.bn_luhn_valid("123456782 RT 0001")
        assert not v.bn_luhn_valid("123456789 RT 0001")

    def test_split(self):
        assert v.split_bn("123456782 RT 0001") == ("123456782", "RT", "0001")


class TestOthers:
    def test_passport(self):
        assert v.passport_structure_valid("AB123456")
        assert not v.passport_structure_valid("A1234567")

    def test_bank(self):
        assert v.micr_transit_structure_valid("12345-678")
        assert not v.micr_transit_structure_valid("1234-5678")
        assert v.electronic_routing_structure_valid("000312345")
        assert not v.electronic_routing_structure_valid("100312345")

    def test_on_dl(self):
        assert v.on_dl_structure_valid("A1234-56789-01234")
        assert v.on_dl_birthdate_plausible("A1234-56789-50615")  # 1950-06-15
        assert v.on_dl_birthdate_plausible("A1234-56789-55615")  # month 56 -> June, female
        assert not v.on_dl_birthdate_plausible("A1234-56789-51315")  # month 13

    def test_qc_bc_dl(self):
        assert v.qc_dl_structure_valid("A1234-123456-12")
        assert not v.qc_dl_structure_valid("A1234-123456-1")
        assert v.bc_dl_structure_valid("1234567")
        assert not v.bc_dl_structure_valid("123456")

    def test_ab_phn(self):
        assert v.ab_phn_structure_valid("12345-6789")
        assert not v.ab_phn_structure_valid("1234-56789-0")

    def test_validators_module_has_no_presidio_import(self):
        import ast
        import pathlib

        tree = ast.parse(pathlib.Path(v.__file__).read_text())
        imported = {
            (n.module if isinstance(n, ast.ImportFrom) else a.name).split(".")[0]
            for n in ast.walk(tree)
            if isinstance(n, ast.Import | ast.ImportFrom)
            for a in (n.names if isinstance(n, ast.Import) else [n])
            if (n.module if isinstance(n, ast.ImportFrom) else a.name)
        }
        assert "presidio_analyzer" not in imported
