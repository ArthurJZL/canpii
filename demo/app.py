"""Gradio demo for canpii: Canadian PII recognizers for Microsoft Presidio.

Run locally::

    pip install -r demo/requirements.txt
    python demo/app.py

or upload the contents of this folder as a Hugging Face Space (see README.md).
"""

from __future__ import annotations

from functools import lru_cache

import gradio as gr
from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_anonymizer import AnonymizerEngine

import canpii
from canpii import PRESETS, create_analyzer, get_preset

ALL_ENTITIES = "All entities"
#: Dropdown label -> preset name (None means "no entity filter").
PRESET_CHOICES: dict[str, str | None] = {
    ALL_ENTITIES: None,
    **{preset.title: name for name, preset in PRESETS.items()},
}
LANGUAGES = [("English", "en"), ("Français", "fr")]
DEFAULT_THRESHOLD = 0.4
DEFAULT_PRESET = PRESETS["pipeda"].title
TABLE_HEADERS = ["entity", "text", "score", "start", "end"]

# Every identifier below is synthetic. They are the fake values used in the
# canpii README and tests: structurally valid, not issued to anyone.
EXAMPLES: list[list[str | float]] = [
    [
        "Patient Jane Tremblay, OHIP 1234-567-897 AB, passport GA123456. "
        "Refund to transit 00011-003, account 1234567.",
        "en",
        PRESETS["pipeda"].title,
        DEFAULT_THRESHOLD,
    ],
    [
        "Numéro de carte santé : BOUF 9451 1419. Numéro d'entreprise 123456782 RT 0001. "
        "Permis de conduire L1234-567890-12.",
        "fr",
        PRESETS["quebec_law25"].title,
        DEFAULT_THRESHOLD,
    ],
    [
        "BC PHN 9000 000 018 confirmed by MSP. Ontario driver's licence A1234-56789-01234.",
        "en",
        PRESETS["phipa"].title,
        DEFAULT_THRESHOLD,
    ],
    [
        "Our GST/HST business number is 123456782 RT 0001. EFT routing number for the bank: "
        "000300011.",
        "en",
        PRESETS["pipeda"].title,
        DEFAULT_THRESHOLD,
    ],
    [
        "Numéro d'assurance maladie : BOUF 9451 1419. Numéro de passeport canadien : GA123456. "
        "Numéro de compte bancaire : 1234567.",
        "fr",
        ALL_ENTITIES,
        DEFAULT_THRESHOLD,
    ],
]

DISCLAIMER = (
    "**Demo only.** Do not paste real personal data: use the synthetic examples below. "
    "Detection is pattern-based and probabilistic; a clean result here is not a "
    "compliance guarantee and not legal advice."
)


@lru_cache(maxsize=1)
def get_analyzer() -> AnalyzerEngine:
    """Build the bilingual analyzer once (loads both spaCy models)."""
    return create_analyzer(languages=["en", "fr"], score_threshold=0.0)


def resolve_overlaps(results: list[RecognizerResult]) -> list[RecognizerResult]:
    """Keep the best-scoring, then longest, result wherever results overlap.

    Same preference as Presidio's anonymizer, applied up front so that the
    highlights, the anonymized text and the table always agree.
    """
    kept: list[RecognizerResult] = []
    for r in sorted(results, key=lambda r: (-r.score, -(r.end - r.start), r.start)):
        if all(r.end <= k.start or r.start >= k.end for k in kept):
            kept.append(r)
    return sorted(kept, key=lambda r: r.start)


def detect(text: str, language: str, preset_label: str, threshold: float) -> list[RecognizerResult]:
    """Analyze ``text`` and return non-overlapping results in reading order."""
    if not text or not text.strip():
        return []
    preset_name = PRESET_CHOICES[preset_label]
    entities = get_preset(preset_name).entity_list() if preset_name else None
    results = get_analyzer().analyze(
        text, language=language, entities=entities, score_threshold=threshold
    )
    return resolve_overlaps(results)


def run(text: str, language: str, preset_label: str, threshold: float):
    """Gradio callback: highlighted spans, anonymized text and a findings table."""
    text = text or ""
    results = detect(text, language, preset_label, threshold)
    highlighted = {
        "text": text,
        "entities": [{"entity": r.entity_type, "start": r.start, "end": r.end} for r in results],
    }
    anonymized = AnonymizerEngine().anonymize(text=text, analyzer_results=results).text
    rows = [
        [r.entity_type, text[r.start : r.end], round(r.score, 2), r.start, r.end] for r in results
    ]
    return highlighted, anonymized, rows


def build_demo() -> gr.Blocks:
    """Assemble the Gradio interface."""
    with gr.Blocks(title="canpii demo") as demo:
        gr.Markdown(
            "# canpii: Canadian PII recognizers for Presidio\n"
            "Provincial health cards, passport, CRA Business Number, bank accounts and "
            "driver's licences, in English and French. "
            f"Running `canpii` {canpii.__version__} · "
            "[GitHub](https://github.com/ArthurJZL/canpii) · "
            "[PyPI](https://pypi.org/project/canpii/)\n\n" + DISCLAIMER
        )
        with gr.Row():
            with gr.Column():
                text = gr.Textbox(
                    label="Text",
                    lines=6,
                    placeholder="Paste synthetic text, or pick an example below.",
                )
                with gr.Row():
                    language = gr.Radio(LANGUAGES, value="en", label="Language")
                    preset = gr.Dropdown(
                        list(PRESET_CHOICES),
                        value=DEFAULT_PRESET,
                        label="Policy preset",
                        info="'All entities' adds spaCy NER labels (dates, organizations, "
                        "…), which are noisy on bare numbers.",
                    )
                threshold = gr.Slider(
                    0.0,
                    1.0,
                    value=DEFAULT_THRESHOLD,
                    step=0.05,
                    label="Score threshold",
                    info="0.4 is recommended: weak patterns only cross it next to a context word.",
                )
                button = gr.Button("Detect", variant="primary")
            with gr.Column():
                highlighted = gr.HighlightedText(label="Detected entities", show_legend=True)
                anonymized = gr.Textbox(label="Anonymized text", lines=4)
                table = gr.Dataframe(
                    headers=TABLE_HEADERS,
                    datatype=["str", "str", "number", "number", "number"],
                    label="Findings",
                    interactive=False,
                )
        inputs = [text, language, preset, threshold]
        outputs = [highlighted, anonymized, table]
        gr.Examples(
            examples=EXAMPLES,
            inputs=inputs,
            outputs=outputs,
            fn=run,
            run_on_click=True,
            cache_examples=False,
            label="Synthetic examples (click to run)",
        )
        button.click(run, inputs, outputs, api_name="detect")
        text.submit(run, inputs, outputs, api_name=False)
        gr.Markdown(
            "All identifiers in the examples are synthetic. Presets are engineering starting "
            "points, described in "
            "[docs/presets.md](https://github.com/ArthurJZL/canpii/blob/main/docs/presets.md)."
        )
    return demo


if __name__ == "__main__":
    build_demo().launch()
