"""Redact Canadian PII with canpii, then do RAG with Cohere.

The pattern::

    raw support tickets --canpii--> redacted tickets --Cohere Embed--> retrieval
                                                     --Cohere Chat (documents=...)--> answer
    answer --local mapping--> re-identified answer (never leaves this process)

Usage::

    pip install "canpii[examples]"
    python -m spacy download en_core_web_sm
    python -m spacy download fr_core_news_sm

    python redact_then_cohere.py --dry-run     # no network, prints the payloads
    CO_API_KEY=... python redact_then_cohere.py

Every identifier in this file is synthetic.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from canpii import create_analyzer, get_preset

# Model names: check https://docs.cohere.com/docs/models before running.
CHAT_MODEL = "command-a-plus-05-2026"
EMBED_MODEL = "embed-v5.0-fast"

DEFAULT_PRESET = "pipeda"
SCORE_THRESHOLD = 0.4
TOP_K = 2

SYSTEM_PROMPT = (
    "You answer questions about support tickets using only the provided documents. "
    "Personal identifiers were replaced by placeholders such as <CA_HEALTH_NUMBER_1> or "
    "<PERSON_1> before the text reached you. Treat each placeholder as an opaque name and "
    "repeat it exactly as written when you refer to it."
)


@dataclass(frozen=True)
class Ticket:
    """A synthetic support ticket and the identifiers planted in it."""

    id: str
    language: str
    text: str
    identifiers: tuple[str, ...] = ()


# Synthetic data. The identifiers are the fake values used in the canpii README and
# tests: structurally valid, not issued to anyone.
TICKETS: tuple[Ticket, ...] = (
    Ticket(
        id="ticket-1001",
        language="en",
        text=(
            "A customer, Jane Tremblay, called because the pharmacy rejected her Ontario health "
            "card, OHIP 1234-567-897 AB. Resolution: the version code on file was out of date. "
            "She was told to renew the card at ServiceOntario and call back."
        ),
        identifiers=("Jane Tremblay", "1234-567-897 AB", "1234-567-897"),
    ),
    Ticket(
        id="ticket-1002",
        language="fr",
        text=(
            "Le client signale que sa carte RAMQ BOUF 9451 1419 est expirée. Résolution : "
            "renouvellement demandé auprès de la RAMQ, délai prévu de dix jours ouvrables."
        ),
        identifiers=("BOUF 9451 1419",),
    ),
    Ticket(
        id="ticket-1003",
        language="en",
        text=(
            "Refund request from a sole proprietor, business number 123456782 RT 0001. Send it "
            "to bank transit 00011-003, account 1234567. Status: refund approved, payment "
            "expected within three business days."
        ),
        identifiers=("123456782 RT 0001", "123456782", "00011-003", "1234567"),
    ),
    Ticket(
        id="ticket-1004",
        language="en",
        text=(
            "Driver onboarding is blocked: Ontario driver's licence A1234-56789-01234 failed "
            "validation, so the applicant sent passport GA123456 instead. Status: waiting for "
            "manual review."
        ),
        identifiers=("A1234-56789-01234", "GA123456"),
    ),
    Ticket(
        id="ticket-1005",
        language="en",
        text=(
            "The label printer at dock 4 is offline. Resolution: the ribbon was replaced and "
            "a test label printed correctly."
        ),
    ),
)

QUESTION = (
    "What happened with the customer whose health card number is 1234-567-897 AB, "
    "and what was she told to do?"
)
QUESTION_IDENTIFIERS = ("1234-567-897 AB", "1234-567-897")


class LeakError(AssertionError):
    """A raw identifier was found in a payload that is about to leave the process."""


@dataclass
class Pseudonymizer:
    """Replace detected entities with placeholders.

    With ``reversible=True`` (default) every distinct value gets a stable, numbered
    placeholder (``<CA_HEALTH_NUMBER_1>``): the same value maps to the same placeholder
    in every document and in the question, and :attr:`mapping` lets you restore the
    original values locally. With ``reversible=False`` the placeholder is just
    ``<CA_HEALTH_NUMBER>`` and nothing is kept.

    :attr:`mapping` holds the raw values. Keep it in memory or in a store with the same
    protection as the source data; never send it anywhere.
    """

    analyzer: Any
    entities: Sequence[str] | None = None
    score_threshold: float = SCORE_THRESHOLD
    reversible: bool = True
    mapping: dict[str, str] = field(default_factory=dict)
    _by_value: dict[tuple[str, str], str] = field(default_factory=dict, repr=False)
    _counters: dict[str, int] = field(default_factory=lambda: defaultdict(int), repr=False)

    def _placeholder(self, entity: str, value: str) -> str:
        if not self.reversible:
            return f"<{entity}>"
        key = (entity, re.sub(r"[\s-]+", "", value).casefold())
        if key not in self._by_value:
            self._counters[entity] += 1
            placeholder = f"<{entity}_{self._counters[entity]}>"
            self._by_value[key] = placeholder
            self.mapping[placeholder] = value
        return self._by_value[key]

    def redact(self, text: str, language: str) -> str:
        """Return ``text`` with every detected entity replaced by its placeholder."""
        results = self.analyzer.analyze(
            text,
            language=language,
            entities=list(self.entities) if self.entities is not None else None,
            score_threshold=self.score_threshold,
        )
        # Where findings overlap keep the best-scoring, then longest, one.
        kept: list[Any] = []
        for r in sorted(results, key=lambda r: (-r.score, -(r.end - r.start), r.start)):
            if all(r.end <= k.start or r.start >= k.end for k in kept):
                kept.append(r)
        kept.sort(key=lambda r: r.start)
        # Number placeholders in reading order, then splice from the end.
        placeholders = [self._placeholder(r.entity_type, text[r.start : r.end]) for r in kept]
        for r, placeholder in reversed(list(zip(kept, placeholders, strict=True))):
            text = text[: r.start] + placeholder + text[r.end :]
        return text

    def reidentify(self, text: str) -> str:
        """Put the original values back into ``text`` (local use only)."""
        # Longest placeholder first so <X_1> does not clobber <X_10>.
        for placeholder in sorted(self.mapping, key=len, reverse=True):
            text = text.replace(placeholder, self.mapping[placeholder])
        return text


@dataclass(frozen=True)
class Prepared:
    """Everything that may leave the process: redacted documents and question."""

    documents: list[dict[str, Any]]
    question: str


def prepare(tickets: Iterable[Ticket], question: str, pseudonymizer: Pseudonymizer) -> Prepared:
    """Redact the tickets and the question (the question can contain PII too)."""
    documents = [
        {"id": t.id, "data": {"text": pseudonymizer.redact(t.text, t.language)}} for t in tickets
    ]
    return Prepared(documents=documents, question=pseudonymizer.redact(question, "en"))


def embed_documents_payload(prepared: Prepared, model: str = EMBED_MODEL) -> dict[str, Any]:
    """Keyword arguments for ``ClientV2.embed`` that index the documents."""
    return {
        "model": model,
        "input_type": "search_document",
        "texts": [d["data"]["text"] for d in prepared.documents],
        "embedding_types": ["float"],
    }


def embed_query_payload(prepared: Prepared, model: str = EMBED_MODEL) -> dict[str, Any]:
    """Keyword arguments for ``ClientV2.embed`` that embed the question."""
    return {
        "model": model,
        "input_type": "search_query",
        "texts": [prepared.question],
        "embedding_types": ["float"],
    }


def chat_payload(
    question: str, documents: list[dict[str, Any]], model: str = CHAT_MODEL
) -> dict[str, Any]:
    """Keyword arguments for ``ClientV2.chat``: grounded generation over ``documents``."""
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        "documents": documents,
    }


def assert_no_raw_identifiers(payloads: Iterable[Any], identifiers: Iterable[str]) -> None:
    """Raise :class:`LeakError` if any identifier appears in any payload.

    Each payload is serialized to JSON first, so the check covers every nested string.
    Call this immediately before sending.
    """
    wanted = sorted({i for i in identifiers if i}, key=len, reverse=True)
    for payload in payloads:
        blob = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
        for identifier in wanted:
            if identifier in blob:
                raise LeakError(f"raw identifier {identifier!r} found in an outgoing payload")


def known_identifiers(
    tickets: Iterable[Ticket], pseudonymizer: Pseudonymizer, extra: Iterable[str] = ()
) -> set[str]:
    """Return the identifiers that must never be sent: planted ones plus everything detected."""
    planted = {i for t in tickets for i in t.identifiers}
    return planted | set(pseudonymizer.mapping.values()) | set(extra)


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity of two vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def top_k_documents(
    query_embedding: Sequence[float],
    document_embeddings: Sequence[Sequence[float]],
    documents: list[dict[str, Any]],
    k: int = TOP_K,
) -> list[dict[str, Any]]:
    """Return the ``k`` documents most similar to the query, best first."""
    scored = sorted(
        zip(documents, document_embeddings, strict=True),
        key=lambda pair: cosine(query_embedding, pair[1]),
        reverse=True,
    )
    return [doc for doc, _ in scored[:k]]


def answer_with_cohere(
    client: Any,
    prepared: Prepared,
    identifiers: Iterable[str],
    *,
    top_k: int = TOP_K,
    chat_model: str = CHAT_MODEL,
    embed_model: str = EMBED_MODEL,
) -> tuple[str, list[dict[str, Any]], Any]:
    """Embed, retrieve and chat. ``client`` is a ``cohere.ClientV2``.

    Returns ``(answer_text, documents_sent, citations)``. Every payload passes
    :func:`assert_no_raw_identifiers` before the call that sends it.
    """
    identifiers = set(identifiers)

    docs_payload = embed_documents_payload(prepared, embed_model)
    query_payload = embed_query_payload(prepared, embed_model)
    assert_no_raw_identifiers([docs_payload, query_payload], identifiers)
    doc_embeddings = client.embed(**docs_payload).embeddings.float_
    query_embedding = client.embed(**query_payload).embeddings.float_[0]

    selected = top_k_documents(query_embedding, doc_embeddings, prepared.documents, top_k)
    payload = chat_payload(prepared.question, selected, chat_model)
    assert_no_raw_identifiers([payload], identifiers)
    response = client.chat(**payload)

    text = "".join(part.text for part in response.message.content or [] if part.type == "text")
    return text, selected, response.message.citations or []


def _print_json(title: str, payload: Any) -> None:
    print(f"--- {title}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print()


def main(argv: Sequence[str] | None = None) -> int:
    """Run the example."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="do everything except the network calls and print the payloads",
    )
    ap.add_argument(
        "--no-reversible",
        action="store_true",
        help="use plain <ENTITY> placeholders and keep no mapping",
    )
    ap.add_argument("--preset", default=DEFAULT_PRESET, help="canpii policy preset")
    ap.add_argument("--question", default=QUESTION)
    ap.add_argument("--top-k", type=int, default=TOP_K)
    ap.add_argument("--chat-model", default=CHAT_MODEL)
    ap.add_argument("--embed-model", default=EMBED_MODEL)
    args = ap.parse_args(argv)

    # 1. Redact locally.
    pseudonymizer = Pseudonymizer(
        analyzer=create_analyzer(languages=["en", "fr"]),
        entities=get_preset(args.preset).entity_list(),
        reversible=not args.no_reversible,
    )
    prepared = prepare(TICKETS, args.question, pseudonymizer)
    identifiers = known_identifiers(TICKETS, pseudonymizer, QUESTION_IDENTIFIERS)

    if args.dry_run:
        # 2. Build the payloads exactly as they would be sent, check them, print them.
        payloads = {
            "ClientV2.embed (documents)": embed_documents_payload(prepared, args.embed_model),
            "ClientV2.embed (query)": embed_query_payload(prepared, args.embed_model),
            # Retrieval needs real embeddings, so the dry run shows the chat call with
            # every document; a live run sends only the top-k of them.
            f"ClientV2.chat (all documents; a live run sends the top {args.top_k})": chat_payload(
                prepared.question, prepared.documents, args.chat_model
            ),
        }
        assert_no_raw_identifiers(payloads.values(), identifiers)
        print("DRY RUN: nothing is sent. Payloads that a live run would send:\n")
        for title, payload in payloads.items():
            _print_json(title, payload)
        print(f"Leak check passed: none of {len(identifiers)} raw identifiers is in a payload.\n")
        if pseudonymizer.mapping:
            _print_json("Local mapping (stays in this process, never sent)", pseudonymizer.mapping)
        return 0

    if not os.environ.get("CO_API_KEY"):
        print("Set CO_API_KEY, or use --dry-run to see the payloads.", file=sys.stderr)
        return 2
    import cohere

    client = cohere.ClientV2(api_key=os.environ["CO_API_KEY"])
    answer, selected, citations = answer_with_cohere(
        client,
        prepared,
        identifiers,
        top_k=args.top_k,
        chat_model=args.chat_model,
        embed_model=args.embed_model,
    )
    print("Question sent:      ", prepared.question)
    print("Documents sent:     ", ", ".join(d["id"] for d in selected))
    print("Answer from Cohere: ", answer)
    for c in citations:
        sources = ", ".join(getattr(s, "id", "?") or "?" for s in c.sources or [])
        print(f"  cited {c.text!r} from {sources}")
    if pseudonymizer.mapping:
        # 3. Re-identify locally; this string never leaves the process.
        print("Re-identified:      ", pseudonymizer.reidentify(answer))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
