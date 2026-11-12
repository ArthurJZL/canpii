"""The Streamlit demo's examples must keep producing the entities they advertise.

The ``detect`` tests need Presidio's anonymizer and the spaCy models but not
Streamlit. The ``AppTest`` smoke test is skipped when Streamlit is not
installed (it is a demo dependency, not a dev dependency).
"""

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
    pytest.importorskip("presidio_anonymizer")
    spec = importlib.util.spec_from_file_location("canpii_demo_app", APP)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_examples_produce_expected_entities(app):
    assert len(app.EXAMPLES) == len(EXPECTED)
    for example, expected in zip(app.EXAMPLES, EXPECTED, strict=True):
        result = app.detect(example.text, example.language, example.preset, example.threshold)
        assert {(f.entity, f.text) for f in result.findings} == expected, example.text
        assert result.text == example.text
        for f in result.findings:
            assert example.text[f.start : f.end] == f.text
            assert f.score >= example.threshold
        for entity, value in expected:
            assert value not in result.anonymized
            assert f"<{entity}>" in result.anonymized


def test_defaults_match_the_documented_ones(app):
    assert app.DEFAULT_THRESHOLD == 0.4
    assert app.DEFAULT_PRESET == "PIPEDA (federal private sector)"
    assert next(iter(app.PRESET_CHOICES)) == app.ALL_ENTITIES
    assert set(app.PRESET_CHOICES.values()) == {None, "pipeda", "phipa", "quebec_law25"}
    assert app.LANGUAGES == {"en": "English", "fr": "Français"}
    assert {e.language for e in app.EXAMPLES} == {"en", "fr"}


def test_empty_text_returns_nothing(app):
    for text in ("", "   \n"):
        result = app.detect(text, "en", app.ALL_ENTITIES, 0.4)
        assert result.findings == []
        assert result.anonymized == text


def test_threshold_filters_weak_matches(app):
    example = app.EXAMPLES[0]
    strict = app.detect(example.text, example.language, example.preset, 0.8)
    assert {(f.entity, f.text) for f in strict.findings} == {("PERSON", "Jane Tremblay")}


def test_highlight_html_escapes_user_text(app):
    text = '<script>alert("x")</script> & OHIP 1234-567-897 AB <b>'
    result = app.detect(text, "en", app.DEFAULT_PRESET, 0.4)
    assert ("CA_HEALTH_NUMBER", "1234-567-897 AB") in {(f.entity, f.text) for f in result.findings}
    html = app.highlight_html(result.text, result.findings)
    assert "<script" not in html
    assert "<b>" not in html
    assert "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp; " in html
    assert html.count("<mark ") == len(result.findings)
    assert ">CA_HEALTH_NUMBER</span>" in html


def test_highlight_html_escapes_inside_a_finding(app):
    finding = app.Finding("X<i>", "<img src=x>", 0.5, 2, 13)
    html = app.highlight_html("a <img src=x> b", [finding])
    assert "<img" not in html
    assert "<i>" not in html
    assert "&lt;img src=x&gt;" in html
    assert "X&lt;i&gt;" in html


def test_streamlit_app_runs_an_example_and_detect(app):
    testing = pytest.importorskip("streamlit.testing.v1")
    at = testing.AppTest.from_file(str(APP), default_timeout=120).run()
    assert not at.exception
    assert at.selectbox(key="preset").value == app.DEFAULT_PRESET
    assert at.slider(key="threshold").value == app.DEFAULT_THRESHOLD
    assert at.radio(key="language").value == "en"
    assert "not legal advice" in at.warning[0].value

    # One click on the French example fills the inputs and runs the detection.
    at.button(key="example_1").click().run()
    assert not at.exception
    assert at.text_area(key="text").value == app.EXAMPLES[1].text
    assert at.radio(key="language").value == "fr"
    assert at.selectbox(key="preset").value == app.EXAMPLES[1].preset
    assert {(f.entity, f.text) for f in at.session_state["detection"].findings} == EXPECTED[1]

    # Edit the text, switch back to English and press Detect.
    at.text_area(key="text").set_value("OHIP 1234-567-897 AB, passport GA123456.")
    at.radio(key="language").set_value("en")
    at.selectbox(key="preset").set_value(app.DEFAULT_PRESET)
    at.button(key="detect").click().run()
    assert not at.exception
    table = at.dataframe[0].value
    assert list(table.columns) == app.TABLE_HEADERS
    assert set(zip(table["entity"], table["text"], strict=True)) == {
        ("CA_HEALTH_NUMBER", "1234-567-897 AB"),
        ("CA_PASSPORT", "GA123456"),
    }
    assert at.code[0].value == "OHIP <CA_HEALTH_NUMBER>, passport <CA_PASSPORT>."
