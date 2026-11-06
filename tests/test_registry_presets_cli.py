import json

import pytest
from presidio_analyzer import RecognizerRegistry

from canpii import (
    ALL_RECOGNIZERS,
    ENTITIES,
    PRESETS,
    get_preset,
    get_recognizers,
    register_all,
)
from canpii.cli import main


def test_get_recognizers_per_language():
    recs = get_recognizers(("en", "fr"))
    assert len(recs) == 2 * len(ALL_RECOGNIZERS)


def test_province_filter_keeps_federal():
    recs = get_recognizers(("en",), provinces=["qc"])
    provinces = {r.PROVINCE for r in recs}
    assert provinces == {"QC", None}


def test_entity_filter():
    recs = get_recognizers(("en",), entities=["CA_PASSPORT"])
    assert [r.name for r in recs] == ["CaPassportRecognizer"]


def test_register_all_adds_upstream_once():
    registry = RecognizerRegistry(supported_languages=["en", "fr"])
    added = register_all(registry, ("en", "fr"))
    names = [(r.name, r.supported_language) for r in registry.recognizers]
    assert ("CaSinRecognizer", "fr") in names
    assert len(names) == len(set(names)) == len(added)
    again = register_all(registry, ("en",), entities=["CA_SIN"])
    assert again == []


def test_register_all_without_upstream():
    registry = RecognizerRegistry(supported_languages=["en"])
    register_all(registry, ("en",), include_upstream=False)
    assert "CaSinRecognizer" not in {r.name for r in registry.recognizers}


@pytest.mark.parametrize("name", sorted(PRESETS))
def test_presets(name):
    preset = get_preset(name)
    assert preset.entities and len(set(preset.entities)) == len(preset.entities)
    assert preset.law_url.startswith("https://")
    assert "CA_HEALTH_NUMBER" in preset.entities
    ours = set(preset.entities) & set(ENTITIES)
    assert ours


def test_get_preset_aliases_and_errors():
    assert get_preset("Quebec-Law25").name == "quebec_law25"
    with pytest.raises(KeyError):
        get_preset("gdpr")


def test_cli_export(capsys):
    assert main(["export", "--format", "litellm", "--preset", "pipeda", "-l", "en"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert all(i["supported_language"] == "en" for i in data)


def test_cli_export_to_file(tmp_path):
    out = tmp_path / "cf.yaml"
    assert main(["export", "-f", "contextforge", "-o", str(out)]) == 0
    assert "custom_patterns" in out.read_text()


def test_cli_generate(capsys):
    assert main(["generate", "bc_phn", "-n", "3", "--seed", "1"]) == 0
    assert len(capsys.readouterr().out.split("\n")) == 4


def test_cli_presets_and_entities(capsys):
    assert main(["presets"]) == 0
    assert "not legal advice" in capsys.readouterr().out
    assert main(["entities"]) == 0
    assert "CaQcRamqRecognizer" in capsys.readouterr().out
