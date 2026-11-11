# Redact Canadian PII, then call Cohere

A small, complete example of one pattern: **detect and replace Canadian identifiers
locally with canpii, and only then send text to a hosted model.** Here the hosted
model is [Cohere](https://docs.cohere.com/) (Embed for retrieval, Chat with the
`documents` parameter for a grounded answer), but nothing in the redaction step is
specific to Cohere.

```
raw tickets ──canpii──▶ redacted tickets ──Cohere Embed──▶ retrieval
                                         ──Cohere Chat (documents=…)──▶ answer
answer ──local mapping──▶ re-identified answer (stays in your process)
```

All identifiers in the example are synthetic.

## What it shows

1. **Redaction before the API call.** Five synthetic support tickets (four English, one
   French) containing an OHIP number, a RAMQ number, a CRA Business Number, bank transit
   and account numbers, an Ontario driver's licence, a passport number and a name are
   redacted with the `pipeda` preset.
2. **RAG on the redacted text.** The redacted tickets are embedded with Cohere Embed,
   the best matches for the question are selected by cosine similarity, and Cohere Chat
   answers with those tickets passed as `documents`, so the answer comes back with
   citations.
3. **Reversible pseudonymization.** Instead of a bare `<CA_HEALTH_NUMBER>`, each
   distinct value gets a stable placeholder such as `<CA_HEALTH_NUMBER_1>`. The same
   health number in a ticket and in the user's question becomes the same placeholder,
   so retrieval and the model can still connect them. The placeholder-to-value mapping
   stays in the process, and the final answer is re-identified locally. Pass
   `--no-reversible` for plain `<ENTITY>` placeholders and no mapping.
4. **A leak check.** `assert_no_raw_identifiers()` serializes every outgoing payload
   and raises if any known identifier (the ones planted in the tickets, plus everything
   canpii detected) is still in it. It runs immediately before each call.

## Why

Teams that handle Canadian personal information often cannot, or would rather not, send
identifiers such as health card numbers to a third-party API, whatever region it is
hosted in. Removing them before the request is a simple control that does not depend on
the provider. canpii's presets (`pipeda`, `phipa`, `quebec_law25`) are lists of entity
types that are a reasonable starting point for that; see
[`docs/presets.md`](../../docs/presets.md).

This is an engineering pattern, **not legal advice and not a compliance guarantee**.
Presets do not detect free-text health information, do not make a dataset
"de-identified" or "anonymized" in the legal sense, and do not replace a privacy impact
assessment. Detection is probabilistic: pattern recognizers miss identifiers and flag
unrelated numbers.

## Run it

```bash
pip install "canpii[examples]"        # canpii + the Cohere SDK
python -m spacy download en_core_web_sm
python -m spacy download fr_core_news_sm

# No API key needed: builds and prints the exact payloads, sends nothing.
python examples/cohere_rag_redaction/redact_then_cohere.py --dry-run

# Live run.
export CO_API_KEY=...
python examples/cohere_rag_redaction/redact_then_cohere.py
```

Options: `--preset phipa`, `--no-reversible`, `--top-k 3`, `--question "..."`,
`--chat-model`, `--embed-model`. The model names are constants at the top of the script
(`command-a-plus-05-2026`, `embed-v5.0-fast`); check
[Cohere's model list](https://docs.cohere.com/docs/models) and change them if they have
been superseded.

## Sample dry-run output

Abridged (`…` marks cuts) from a real `--dry-run`:

```text
DRY RUN: nothing is sent. Payloads that a live run would send:

--- ClientV2.embed (documents)
{
  "model": "embed-v5.0-fast",
  "input_type": "search_document",
  "texts": [
    "A customer, <PERSON_1>, called because the pharmacy rejected her Ontario health card, OHIP <CA_HEALTH_NUMBER_1>. Resolution: the version code on file was out of date. She was told to renew the card at ServiceOntario and call back.",
    "Le client signale que sa carte RAMQ <CA_HEALTH_NUMBER_2> est expirée. Résolution : renouvellement demandé auprès de la RAMQ, délai prévu de dix jours ouvrables.",
    "Refund request from a sole proprietor, business number <CA_BN_1>. Send it to bank transit <CA_BANK_ACCOUNT_1>, account <CA_BANK_ACCOUNT_2>. Status: refund approved, payment expected within three business days.",
    "Driver onboarding is blocked: Ontario driver's licence <CA_DRIVER_LICENSE_1> failed validation, so the applicant sent passport <CA_PASSPORT_1> instead. Status: waiting for manual review.",
    "The label printer at dock 4 is offline. Resolution: the ribbon was replaced and a test label printed correctly."
  ],
  "embedding_types": [
    "float"
  ]
}

--- ClientV2.embed (query)
{
  "model": "embed-v5.0-fast",
  "input_type": "search_query",
  "texts": [
    "What happened with the customer whose health card number is <CA_HEALTH_NUMBER_1>, and what was she told to do?"
  ],
  …
}

--- ClientV2.chat (all documents; a live run sends the top 2)
{
  "model": "command-a-plus-05-2026",
  "messages": [
    {
      "role": "system",
      "content": "You answer questions about support tickets using only the provided documents. …"
    },
    {
      "role": "user",
      "content": "What happened with the customer whose health card number is <CA_HEALTH_NUMBER_1>, and what was she told to do?"
    }
  ],
  "documents": [
    {
      "id": "ticket-1001",
      "data": {
        "text": "A customer, <PERSON_1>, called because the pharmacy rejected her Ontario health card, OHIP <CA_HEALTH_NUMBER_1>. …"
      }
    },
    …
  ]
}

Leak check passed: none of 10 raw identifiers is in a payload.

--- Local mapping (stays in this process, never sent)
{
  "<PERSON_1>": "Jane Tremblay",
  "<CA_HEALTH_NUMBER_1>": "1234-567-897 AB",
  "<CA_HEALTH_NUMBER_2>": "BOUF 9451 1419",
  "<CA_BN_1>": "123456782 RT 0001",
  "<CA_BANK_ACCOUNT_1>": "00011-003",
  "<CA_BANK_ACCOUNT_2>": "1234567",
  "<CA_DRIVER_LICENSE_1>": "A1234-56789-01234",
  "<CA_PASSPORT_1>": "GA123456"
}
```

## Things to know before copying this

* **The mapping is personal information.** It holds the raw values. Keep it in memory
  for the request, or in a store protected like the source data. Do not log it.
* **The leak check only knows what it is told.** It covers identifiers planted in the
  example and values canpii detected. An identifier that canpii misses is not in that
  list, so the check cannot catch it. In your own system, feed it identifiers from a
  source you trust (for example the customer record the ticket belongs to).
* **Names come from spaCy NER.** `PERSON` is detected by the small spaCy model, which is
  noisy: it can tag an acronym such as "OHIP" as a person. When that happens the leak
  check fails closed, because the "name" also appears elsewhere unredacted. Use a larger
  model (`create_analyzer(models={"en": "en_core_web_lg"})`) for real text.
* **Retrieval in the dry run.** Ranking needs real embeddings, so `--dry-run` prints the
  chat request with all five documents; a live run sends only the top `--top-k`.
* **What was tested.** The dry run, and the full embed → retrieve → chat path against
  the real Cohere SDK over an in-process mock transport
  ([`tests/test_cohere_example.py`](../../tests/test_cohere_example.py)), which checks
  the request bodies the SDK produces. The example has not yet been run against the live
  Cohere API: treat the model names and the live response handling as unverified.
