"""examples/cohere_rag_redaction: redaction, pseudonymization and the leak check.

No network. The tests that drive the real Cohere SDK use an in-process HTTP
transport and are skipped when ``cohere`` is not installed.
"""

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples" / "cohere_rag_redaction" / "redact_then_cohere.py"


@pytest.fixture(scope="module")
def ex():
    if not SCRIPT.exists():
        pytest.skip("examples/ is not shipped in the sdist")
    spec = importlib.util.spec_from_file_location("redact_then_cohere", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeAnalyzer:
    """Finds fixed strings, so pattern-free tests need no spaCy model."""

    def __init__(self, known):
        self.known = known  # {value: entity}

    def analyze(self, text, language, entities=None, score_threshold=None):
        out = []
        for value, entity in self.known.items():
            start = text.find(value)
            while start != -1:
                out.append(
                    SimpleNamespace(
                        entity_type=entity, start=start, end=start + len(value), score=0.9
                    )
                )
                start = text.find(value, start + 1)
        return out


def test_example_does_not_import_cohere_at_module_level(ex):
    assert "cohere" not in vars(ex)


def test_reversible_placeholders_are_stable_and_reversible(ex):
    fake = FakeAnalyzer({"1234-567-897": "CA_HEALTH_NUMBER", "GA123456": "CA_PASSPORT"})
    p = ex.Pseudonymizer(analyzer=fake)
    first = p.redact("OHIP 1234-567-897, passport GA123456.", "en")
    second = p.redact("Again 1234-567-897.", "en")
    assert first == "OHIP <CA_HEALTH_NUMBER_1>, passport <CA_PASSPORT_1>."
    assert second == "Again <CA_HEALTH_NUMBER_1>."
    assert p.mapping == {"<CA_HEALTH_NUMBER_1>": "1234-567-897", "<CA_PASSPORT_1>": "GA123456"}
    assert p.reidentify(second) == "Again 1234-567-897."


def test_same_value_with_different_separators_shares_a_placeholder(ex):
    fake = FakeAnalyzer({"1234-567-897": "CA_HEALTH_NUMBER", "1234 567 897": "CA_HEALTH_NUMBER"})
    p = ex.Pseudonymizer(analyzer=fake)
    assert p.redact("a 1234-567-897 b 1234 567 897", "en") == (
        "a <CA_HEALTH_NUMBER_1> b <CA_HEALTH_NUMBER_1>"
    )


def test_non_reversible_mode_keeps_no_mapping(ex):
    p = ex.Pseudonymizer(analyzer=FakeAnalyzer({"GA123456": "CA_PASSPORT"}), reversible=False)
    assert p.redact("passport GA123456", "en") == "passport <CA_PASSPORT>"
    assert p.mapping == {}


def test_reidentify_handles_two_digit_placeholders(ex):
    p = ex.Pseudonymizer(analyzer=FakeAnalyzer({}))
    p.mapping = {"<X_1>": "one", "<X_10>": "ten"}
    assert p.reidentify("<X_10> and <X_1>") == "ten and one"


def test_leak_check_raises_on_nested_identifier(ex):
    payload = {"documents": [{"id": "d1", "data": {"text": "OHIP 1234-567-897 AB"}}]}
    with pytest.raises(ex.LeakError, match="1234-567-897"):
        ex.assert_no_raw_identifiers([payload], ["1234-567-897"])
    ex.assert_no_raw_identifiers([payload], ["GA123456", ""])


def test_leak_check_sees_non_ascii_text(ex):
    with pytest.raises(ex.LeakError):
        ex.assert_no_raw_identifiers([{"t": "Zoé Côté a appelé"}], ["Zoé Côté"])


def test_top_k_documents_orders_by_cosine(ex):
    docs = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    picked = ex.top_k_documents([1.0, 0.0], [[0.0, 1.0], [1.0, 0.1], [0.5, 0.5]], docs, k=2)
    assert [d["id"] for d in picked] == ["b", "c"]


@pytest.fixture(scope="module")
def prepared(ex, analyzer):
    from canpii import get_preset

    pseudonymizer = ex.Pseudonymizer(
        analyzer=analyzer, entities=get_preset(ex.DEFAULT_PRESET).entity_list()
    )
    prepared = ex.prepare(ex.TICKETS, ex.QUESTION, pseudonymizer)
    identifiers = ex.known_identifiers(ex.TICKETS, pseudonymizer, ex.QUESTION_IDENTIFIERS)
    return pseudonymizer, prepared, identifiers


@pytest.mark.nlp
def test_no_planted_identifier_survives_in_any_payload(ex, prepared):
    _, prepared, identifiers = prepared
    planted = {i for t in ex.TICKETS for i in t.identifiers} | set(ex.QUESTION_IDENTIFIERS)
    assert planted <= identifiers
    payloads = [
        ex.embed_documents_payload(prepared),
        ex.embed_query_payload(prepared),
        ex.chat_payload(prepared.question, prepared.documents),
    ]
    ex.assert_no_raw_identifiers(payloads, identifiers)
    blob = json.dumps(payloads, ensure_ascii=False)
    for identifier in planted:
        assert identifier not in blob
    # The untouched ticket is sent as is.
    assert prepared.documents[-1]["data"]["text"] == ex.TICKETS[-1].text


@pytest.mark.nlp
def test_question_and_ticket_share_the_health_number_placeholder(ex, prepared):
    pseudonymizer, prepared, _ = prepared
    assert pseudonymizer.mapping["<CA_HEALTH_NUMBER_1>"] == "1234-567-897 AB"
    assert "<CA_HEALTH_NUMBER_1>" in prepared.question
    assert "<CA_HEALTH_NUMBER_1>" in prepared.documents[0]["data"]["text"]
    for ticket, doc in zip(ex.TICKETS, prepared.documents, strict=True):
        assert pseudonymizer.reidentify(doc["data"]["text"]) == ticket.text


@pytest.mark.nlp
def test_dry_run_prints_payloads_without_identifiers(ex, capsys):
    assert ex.main(["--dry-run", "--no-reversible"]) == 0
    out = capsys.readouterr().out
    assert "Leak check passed" in out
    assert "<CA_HEALTH_NUMBER>" in out
    for ticket in ex.TICKETS:
        for identifier in ticket.identifiers:
            assert identifier not in out


@pytest.mark.nlp
def test_real_sdk_request_bodies_contain_no_identifier(ex, prepared):
    """Drive cohere.ClientV2 over a mock transport and inspect the bytes it would send."""
    cohere = pytest.importorskip("cohere")
    httpx = pytest.importorskip("httpx")
    pseudonymizer, prepared, identifiers = prepared
    sent: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.content.decode("utf-8")
        sent.append((request.url.path, body))
        data = json.loads(body)
        if request.url.path.endswith("/embed"):
            # Unit vectors: the query and the first document point the same way.
            if data["input_type"] == "search_query":
                vectors = [[1.0, 0.0]]
            else:
                vectors = [[1.0, 0.0]] + [[0.0, 1.0]] * (len(data["texts"]) - 1)
            return httpx.Response(
                200,
                json={
                    "id": "emb-1",
                    "response_type": "embeddings_by_type",
                    "embeddings": {"float": vectors},
                    "texts": data["texts"],
                },
            )
        return httpx.Response(
            200,
            json={
                "id": "chat-1",
                "finish_reason": "COMPLETE",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "<PERSON_1> was told to renew the card."}],
                    "citations": [
                        {
                            "start": 11,
                            "end": 37,
                            "text": "was told to renew the card",
                            "sources": [{"type": "document", "id": "ticket-1001"}],
                        }
                    ],
                },
            },
        )

    client = cohere.ClientV2(
        api_key="test-key", httpx_client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    answer, selected, citations = ex.answer_with_cohere(client, prepared, identifiers, top_k=1)

    assert [path.rsplit("/", 1)[-1] for path, _ in sent] == ["embed", "embed", "chat"]
    for _, body in sent:
        for identifier in identifiers:
            assert identifier not in body
            assert identifier not in json.dumps(json.loads(body), ensure_ascii=False)
    chat_body = json.loads(sent[-1][1])
    assert chat_body["model"] == ex.CHAT_MODEL
    assert [d["id"] for d in chat_body["documents"]] == ["ticket-1001"]
    assert [d["id"] for d in selected] == ["ticket-1001"]
    assert answer == "<PERSON_1> was told to renew the card."
    assert pseudonymizer.reidentify(answer) == "Jane Tremblay was told to renew the card."
    assert citations[0].sources[0].id == "ticket-1001"
