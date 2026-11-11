---
title: What Presidio misses for Canadian PII, and what I did about it
published: false
description: Stock Presidio has no recognizer for Canadian health cards, passports, Business Numbers, bank numbers or driver's licences. I measured what it does with them and wrote a package that fills the gap.
tags: python, privacy, opensource, llm
---

I'm Arthur, a systems engineer at Geek+ in Toronto, where I work on warehouse automation
integrations. This post is about [canpii](https://github.com/ArthurJZL/canpii), an
open-source package I wrote that adds Canadian identifiers to
[Microsoft Presidio](https://github.com/data-privacy-stack/presidio), a widely used
open-source PII detector.

## The problem, in one support ticket

Here is a made-up ticket. Every identifier in this post is synthetic.

```text
Ticket from Jane Tremblay: the clinic rejected my health card, OHIP 1234-567-897 AB.
Please also update our business number to 123456782 RT 0001.
```

And one in French:

```text
Bonjour, mon numéro d'assurance maladie est BOUF 9451 1419 et la pharmacie le refuse.
```

The first contains an Ontario health number (OHIP) and a CRA Business Number with a GST/HST
program account. The second contains a Québec health insurance number (RAMQ).

I ran both through stock Presidio 2.2.366: the default recognizers, nothing added, with the
small spaCy models for English and French, and a score threshold of 0.4. This is what it
found in the English ticket:

```text
PERSON        'Jane Tremblay'   0.85
PHONE_NUMBER  '1234-567-897'    0.40
DATE_TIME     '123456782'       0.85
US_PASSPORT   '123456782'       0.40
```

After anonymization:

```text
Ticket from <PERSON>: the clinic rejected my health card, OHIP <PHONE_NUMBER> AB.
Please also update our business number to <DATE_TIME> RT 0001.
```

The health number is masked, but as a phone number, and its version code `AB` is left
behind. The Business Number is masked as a date, and the program account `RT 0001` is left
behind. If your policy says "block health numbers" or "allow phone numbers", it does the
wrong thing in both cases.

In the French ticket, stock Presidio found nothing. The RAMQ number went through unchanged.

## Why Canadian identifiers are awkward

There is no single "Canadian health number". Each province issues its own:

- Ontario: 10 digits plus an optional one- or two-letter version code.
- Québec: 4 letters and 8 digits, with the holder's birth date embedded.
- British Columbia: 10 digits starting with 9, with a MOD-11 check digit.
- Alberta: 9 digits, with no published check digit.

So one entity needs several recognizers, and they differ in how much you can trust a
match. A BC number that passes its checksum is strong evidence. A 9-digit Alberta number
is just nine digits; only the words around it ("AHCIP", "health number") tell you what it
is. Passport numbers (2 letters and 6 digits) and bank account numbers (7 to 12 digits)
are in the same position: without context they look like order IDs.

Then there is French. The context words that raise a score have to exist in both
languages: "carte santé", "assurance maladie", "permis de conduire", "numéro d'entreprise".

Context matching has its own trap. Presidio does ship a Canadian SIN recognizer (disabled
by default), and one of its context words is "sin". Presidio's default matching is by
substring, and "sin" is a substring of "bu**sin**ess". With that recognizer enabled:

```text
Number on file: 130-692-544.             CA_SIN 0.5
Our business number is 130-692-544.      CA_SIN 0.85
```

The word "business" raises the SIN score from 0.5 to 0.85, as much as the word "SIN"
itself does. I reported this upstream as
[presidio#2459](https://github.com/data-privacy-stack/presidio/issues/2459). canpii's
analyzer uses whole-word context matching, where the second sentence scores 0.5.

## What canpii does

canpii adds five entities in Presidio's own style: `CA_HEALTH_NUMBER` (Ontario, Québec,
BC, Alberta), `CA_PASSPORT`, `CA_BN`, `CA_BANK_ACCOUNT` and `CA_DRIVER_LICENSE` (Ontario,
Québec, BC). Each recognizer has English and French context words, and validation where an
official rule exists: the BC checksum, the RAMQ birth date, the CRA program identifiers.
It also turns on Presidio's own SIN and postal code recognizers.

```python
from presidio_anonymizer import AnonymizerEngine
from canpii import create_analyzer, get_preset

analyzer = create_analyzer(languages=["en", "fr"])
entities = get_preset("pipeda").entity_list()

tickets = [
    (
        "en",
        "Ticket from Jane Tremblay: the clinic rejected my health card, "
        "OHIP 1234-567-897 AB. Please also update our business number to 123456782 RT 0001.",
    ),
    ("fr", "Bonjour, mon numéro d'assurance maladie est BOUF 9451 1419 et la pharmacie le refuse."),
]
for language, text in tickets:
    results = analyzer.analyze(text, language=language, entities=entities)
    print(AnonymizerEngine().anonymize(text=text, analyzer_results=results).text)
```

Output:

```text
Ticket from <PERSON>: the clinic rejected my health card, OHIP <CA_HEALTH_NUMBER>. Please also update our business number to <CA_BN>.
Bonjour, mon numéro d'assurance maladie est <CA_HEALTH_NUMBER> et la pharmacie le refuse.
```

The version code and the program account are now part of the match, and the French ticket
is handled. `pipeda` is one of three presets (with `phipa` and `quebec_law25`): lists of
entity types that are a starting point for a policy. They are not legal advice.

## Numbers

The repository has a benchmark: 1,740 bilingual template sentences with 700 labeled
occurrences of the five identifiers above, some with a context word and some without. I ran the
positives through stock Presidio and through Presidio + canpii at threshold 0.4. Recall:

| Entity | Gold spans | Stock: right entity | Stock: flagged as anything | canpii: right entity |
|---|---:|---:|---:|---:|
| CA_HEALTH_NUMBER | 240 | 0.000 | 0.696 | 0.863 |
| CA_PASSPORT | 60 | 0.000 | 0.183 | 0.667 |
| CA_BN | 60 | 0.000 | 0.500 | 0.933 |
| CA_BANK_ACCOUNT | 160 | 0.000 | 0.506 | 0.625 |
| CA_DRIVER_LICENSE | 180 | 0.000 | 0.483 | 0.778 |
| All five | 700 | 0.000 | 0.537 | 0.776 |

"Flagged as anything" is the generous reading for stock Presidio: any part of the
identifier tagged as any entity, as in the ticket above. It covers the whole identifier
for only 0.360 of the spans.

The caveat matters more than the table. I wrote the template sentences, so this is a
regression benchmark, not an estimate of accuracy on real text. Recall is also only half
of it: on the same corpus canpii's precision ranges from 0.71 (bank numbers) to 1.00. The
method and full tables are in
[benchmarks/RESULTS.md](https://github.com/ArthurJZL/canpii/blob/main/benchmarks/RESULTS.md).

## Where it falls short

- **No context, no match, for the weak patterns.** All of canpii's misses in that table
  are sentences without a context word. There it found 0 of 20 passport numbers and 0 of
  60 bank numbers. That is deliberate, because flagging every 7-digit number is worse, but
  it means free-form text will have misses.
- **Provinces are missing.** Health cards for Saskatchewan, Manitoba and Nova Scotia, and
  driver's licences for Alberta and Manitoba, are not covered yet. Neither are New
  Brunswick, PEI, Newfoundland and Labrador or the territories.
- **The French needs a native review.** The French context words and test sentences have
  not been reviewed by someone who writes Québec French every day.
- **The benchmark is synthetic.** A more realistic corpus is an open issue.

Issues [#1 to #8](https://github.com/ArthurJZL/canpii/issues) cover these gaps. Each
province is a self-contained recognizer, validator and tests, with a recipe in
CONTRIBUTING.md. If you know your province's card format, that is a small pull request.
Two rules: every format rule cites a source, and no real identifiers, ever.

## Links

- Repository: <https://github.com/ArthurJZL/canpii>
- PyPI: <https://pypi.org/project/canpii/> (`pip install canpii`)
- Upstream context bug: <https://github.com/data-privacy-stack/presidio/issues/2459>
