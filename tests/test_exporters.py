import json
import re

import pytest
import yaml
from presidio_analyzer import PatternRecognizer

from canpii import get_preset, synthetic
from canpii.exporters import (
    check_contextforge_pattern,
    export,
    iter_portable_patterns,
    to_contextforge,
    to_generic,
    to_litellm_ad_hoc,
)


def test_all_patterns_compile_in_python_re():
    for p in iter_portable_patterns():
        re.compile(p.regex, re.IGNORECASE)


def test_all_patterns_within_contextforge_limits():
    for p in iter_portable_patterns():
        assert check_contextforge_pattern(p.regex) is None, p.name


def test_contextforge_limit_checker():
    assert check_contextforge_pattern("a" * 300)
    assert check_contextforge_pattern("(?<=x)y")
    assert check_contextforge_pattern(r"(a)\1")
    assert check_contextforge_pattern("|".join("a" * 20))


def test_litellm_schema_roundtrips_through_presidio():
    items = to_litellm_ad_hoc(languages=("en", "fr"))
    assert {i["supported_language"] for i in items} == {"en", "fr"}
    for item in items:
        assert set(item) == {
            "name",
            "supported_language",
            "patterns",
            "context",
            "supported_entity",
        }
        for p in item["patterns"]:
            assert set(p) == {"name", "regex", "score"}
        PatternRecognizer.from_dict(item)


def test_litellm_ad_hoc_detects(rng):
    items = [i for i in to_litellm_ad_hoc(["CA_HEALTH_NUMBER"]) if "Ramq" in i["name"]]
    rec = PatternRecognizer.from_dict(items[0])
    value = synthetic.ramq(rng)
    assert rec.analyze(f"NAM {value}", ["CA_HEALTH_NUMBER"])


def test_litellm_includes_upstream_sin_without_backreference():
    items = to_litellm_ad_hoc(["CA_SIN"])
    regexes = [p["regex"] for i in items for p in i["patterns"]]
    assert regexes and all("\\1" not in r for r in regexes)


def test_litellm_config_for_preset():
    text = export("litellm-config", preset=get_preset("phipa"))
    conf = yaml.safe_load(text)
    params = conf["guardrails"][0]["litellm_params"]
    assert params["guardrail"] == "presidio"
    assert params["pii_entities_config"]["CA_HEALTH_NUMBER"] == "MASK"
    assert params["presidio_score_thresholds"] == {"ALL": 0.4}
    assert "not legal advice" in text


def test_contextforge_excludes_weak_patterns():
    conf = yaml.safe_load(to_contextforge())
    patterns = conf["custom_patterns"]
    assert patterns
    for p in patterns:
        assert set(p) == {"pattern", "description", "mask_strategy", "enabled"}
    assert r"\b\d{7}\b" not in {p["pattern"] for p in patterns}


def test_generic_json_mentions_lost_validation():
    data = to_generic()
    assert "NOT included" in data["notes"]
    phn = [p for p in data["patterns"] if p["recognizer"] == "CaBcPhnRecognizer"]
    assert phn and all("MOD-11" in p["validation_lost"] for p in phn)


def test_presidio_yaml_lists_preset_entities():
    text = export("presidio-yaml", preset=get_preset("pipeda"))
    conf = yaml.safe_load(text)
    names = {r["name"] for r in conf["recognizers"]}
    assert {"CaOnOhipRecognizer", "CaSinRecognizer", "EmailRecognizer"} <= names


def test_bundled_yaml_matches_exporter():
    from canpii import recognizer_registry_yaml
    from canpii.exporters import to_presidio_yaml

    assert recognizer_registry_yaml().read_text() == to_presidio_yaml()


def test_json_exports_are_valid_json():
    json.loads(export("litellm", preset=get_preset("pipeda"), languages=["en", "fr"]))
    json.loads(export("generic"))


def test_unknown_format():
    with pytest.raises(ValueError):
        export("nope")
    with pytest.raises(ValueError):
        export("litellm-config")
