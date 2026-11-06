"""End-to-end: presidio-analyzer + presidio-anonymizer with spaCy models."""

import pytest

from canpii import synthetic
from conftest import CA_ENTITIES

pytestmark = pytest.mark.nlp


def _found(analyzer, text, lang):
    return {
        (r.entity_type, text[r.start : r.end])
        for r in analyzer.analyze(text, language=lang, entities=CA_ENTITIES)
    }


@pytest.mark.parametrize(
    ("lang", "template", "kind"),
    [
        ("en", "Patient OHIP number: {v}.", "ohip"),
        ("fr", "Numéro de carte santé : {v}.", "ohip"),
        ("en", "RAMQ health insurance number {v} on file.", "ramq"),
        ("fr", "Numéro d'assurance maladie : {v}", "ramq"),
        ("en", "BC PHN {v} confirmed by MSP.", "bc_phn"),
        ("fr", "Numéro de santé personnel (PHN) : {v}", "bc_phn"),
        ("en", "Alberta AHCIP health number {v}.", "ab_phn"),
        ("en", "Canadian passport number {v}", "passport"),
        ("fr", "Numéro de passeport : {v}", "passport"),
        ("en", "Our GST/HST business number is {v}.", "bn"),
        ("fr", "Numéro d'entreprise (TPS/TVH) : {v}", "bn"),
        ("en", "Bank transit and institution: {v}.", "bank_transit"),
        ("fr", "Numéro de compte bancaire : {v}", "bank_account"),
        ("en", "Ontario driver's licence {v}.", "on_dl"),
        ("fr", "Permis de conduire SAAQ : {v}", "qc_dl"),
        ("en", "ICBC driver's licence {v}.", "bc_dl"),
        ("fr", "Permis de conduire de la C.-B. {v}", "bc_dl"),
    ],
)
def test_detected_with_context(analyzer, rng, lang, template, kind):
    entity, fn = synthetic.GENERATORS[kind]
    value = fn(rng)
    text = template.replace("{v}", value)
    assert (entity, value) in _found(analyzer, text, lang), text


def test_anonymizer_masks_canadian_entities(analyzer, rng):
    from presidio_anonymizer import AnonymizerEngine

    ohip, ramq = synthetic.ohip(rng), synthetic.ramq(rng)
    text = f"OHIP {ohip}; RAMQ {ramq}."
    results = analyzer.analyze(text, language="en", entities=CA_ENTITIES)
    anonymized = AnonymizerEngine().anonymize(text=text, analyzer_results=results).text
    assert ohip not in anonymized and ramq not in anonymized
    assert anonymized.count("<CA_HEALTH_NUMBER>") == 2


def test_french_document_with_preset(analyzer, rng):
    from presidio_anonymizer import AnonymizerEngine

    from canpii import get_preset

    preset = get_preset("quebec_law25")
    nam, dl = synthetic.ramq(rng), synthetic.qc_dl(rng)
    text = f"Carte d'assurance maladie {nam}. Permis de conduire SAAQ {dl}."
    results = analyzer.analyze(text, language="fr", entities=preset.entity_list())
    out = AnonymizerEngine().anonymize(text=text, analyzer_results=results).text
    assert nam not in out and dl not in out


def test_registry_yaml_loads(rng):
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

    from canpii import recognizer_registry_yaml

    nlp = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [
                {"lang_code": "en", "model_name": "en_core_web_sm"},
                {"lang_code": "fr", "model_name": "fr_core_news_sm"},
            ],
        }
    ).create_engine()
    registry = RecognizerRegistryProvider(
        conf_file=recognizer_registry_yaml(), nlp_engine=nlp
    ).create_recognizer_registry()
    names = {(r.name, r.supported_language) for r in registry.recognizers}
    assert ("CaQcRamqRecognizer", "fr") in names
    assert ("CaSinRecognizer", "fr") in names
    engine = AnalyzerEngine(registry=registry, nlp_engine=nlp, supported_languages=["en", "fr"])
    value = synthetic.bc_phn(rng)
    found = engine.analyze(f"PHN {value}", language="en", score_threshold=0.4)
    assert any(r.entity_type == "CA_HEALTH_NUMBER" for r in found)


def test_whole_word_context_mode_avoids_sin_in_business(rng):
    from canpii import create_analyzer

    bn = synthetic.bn(rng)
    text = f"Our business number is {bn}."
    sub = create_analyzer(languages=["en"], context_matching_mode="substring")
    whole = create_analyzer(languages=["en"], context_matching_mode="whole_word")
    ents = ["CA_SIN", "CA_BN"]
    sub_types = {r.entity_type for r in sub.analyze(text, language="en", entities=ents)}
    whole_types = {r.entity_type for r in whole.analyze(text, language="en", entities=ents)}
    # Upstream CA_SIN's context word "sin" is a substring of "business".
    assert "CA_SIN" in sub_types
    assert whole_types == {"CA_BN"}
