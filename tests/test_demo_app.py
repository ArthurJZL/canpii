"""The Gradio demo's examples must keep producing the entities they advertise."""

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.nlp

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "demo" / "app.py"

EXPECTED = [
    {
        ("PERSON", "Jane Tremblay"),
        ("CA_HEALTH_NUMBER", "1234-567-897 AB"),
        ("CA_PASSPORT", "GA123456"),
        ("CA_BANK_ACCOUNT", "00011-003"),
        ("CA_BANK_ACCOUNT", "1234567"),
    },
    {
        ("CA_HEALTH_NUMBER", "BOUF 9451 1419"),
        ("CA_BN", "123456782 RT 0001"),
        ("CA_DRIVER_LICENSE", "L1234-567890-12"),
    },
    {("CA_HEALTH_NUMBER", "9000 000 018"), ("CA_DRIVER_LICENSE", "A1234-56789-01234")},
    {("CA_BN", "123456782 RT 0001"), ("CA_BANK_ACCOUNT", "000300011")},
    {
        ("CA_HEALTH_NUMBER", "BOUF 9451 1419"),
        ("CA_PASSPORT", "GA123456"),
        ("CA_BANK_ACCOUNT", "1234567"),
    },
]


@pytest.fixture(scope="module")
def app():
    if not APP.exists():
        pytest.skip("demo/ is not shipped in the sdist")
    pytest.importorskip("gradio")
    pytest.importorskip("presidio_anonymizer")
    spec = importlib.util.spec_from_file_location("canpii_demo_app", APP)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_examples_produce_expected_entities(app):
    assert len(app.EXAMPLES) == len(EXPECTED)
    for example, expected in zip(app.EXAMPLES, EXPECTED, strict=True):
        highlighted, anonymized, rows = app.run(*example)
        assert {(row[0], row[1]) for row in rows} == expected, example[0]
        assert len(highlighted["entities"]) == len(rows)
        for _, value in expected:
            assert value not in anonymized


def test_empty_text_returns_nothing(app):
    highlighted, anonymized, rows = app.run("", "en", app.ALL_ENTITIES, 0.4)
    assert highlighted == {"text": "", "entities": []}
    assert anonymized == ""
    assert rows == []
