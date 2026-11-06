"""Keep documentation in sync with code."""

import importlib.util
import re
from pathlib import Path

from canpii.catalog import CATALOG
from canpii.recognizers import ALL_RECOGNIZERS

ROOT = Path(__file__).resolve().parents[1]


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "generate_docs", ROOT / "scripts" / "generate_docs.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_recognizer_is_sourced_in_entities_md():
    text = (ROOT / "docs" / "entities.md").read_text()
    for cls in ALL_RECOGNIZERS:
        assert f"`{cls.__name__}`" in text, cls.__name__
    assert re.findall(r"https://", text)


def test_catalog_covers_all_recognizers():
    assert {e.recognizer for e in CATALOG} == set(ALL_RECOGNIZERS)


def test_presets_doc_is_generated():
    assert (ROOT / "docs" / "presets.md").read_text() == _load_generator().presets_markdown()


def test_readme_acknowledges_upstream():
    readme = (ROOT / "README.md").read_text()
    for needle in (
        "#2207",
        "#2206",
        "#2204",
        "defer to",
        "not legal advice",
        "Synthetic data only",
    ):
        assert needle.lower() in readme.lower(), needle


def test_good_first_issues_have_front_matter():
    issues = sorted((ROOT / "docs" / "issues").glob("*.md"))
    assert len(issues) >= 8
    for path in issues:
        text = path.read_text()
        assert text.startswith("---\ntitle: "), path.name
        assert "good first issue" in text
