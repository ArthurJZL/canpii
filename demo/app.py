"""Streamlit demo for canpii: Canadian PII recognizers for Microsoft Presidio.

Run locally::

    pip install -r demo/requirements.txt
    streamlit run demo/app.py

or deploy this file on Streamlit Community Cloud (see README.md).

The detection logic (:func:`detect`, :func:`highlight_html`) is plain Python.
Streamlit is only imported inside :func:`main`, so the logic can be imported
and tested without it.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from html import escape

from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_anonymizer import AnonymizerEngine

import canpii
from canpii import PRESETS, create_analyzer, get_preset

ALL_ENTITIES = "All entities"
#: Select box label -> preset name (None means "no entity filter").
PRESET_CHOICES: dict[str, str | None] = {
    ALL_ENTITIES: None,
    **{preset.title: name for name, preset in PRESETS.items()},
}
#: Language code -> label shown in the UI.
LANGUAGES: dict[str, str] = {"en": "English", "fr": "Français"}
DEFAULT_THRESHOLD = 0.4
DEFAULT_PRESET = PRESETS["pipeda"].title
TABLE_HEADERS = ["entity", "text", "score", "start", "end"]


@dataclass(frozen=True)
class Example:
    """One synthetic example: the inputs the app fills in when it is clicked."""

    label: str
    text: str
    language: str
    preset: str
    threshold: float = DEFAULT_THRESHOLD


# Every identifier below is synthetic. They are the fake values used in the
# canpii README and tests: structurally valid, not issued to anyone.
EXAMPLES: list[Example] = [
    Example(
        "EN · Patient record",
        "Patient Jane Tremblay, OHIP 1234-567-897 AB, passport GA123456. "
        "Refund to transit 00011-003, account 1234567.",
        "en",
        PRESETS["pipeda"].title,
    ),
    Example(
        "FR · Dossier québécois",
        "Numéro de carte santé : BOUF 9451 1419. Numéro d'entreprise 123456782 RT 0001. "
        "Permis de conduire L1234-567890-12.",
        "fr",
        PRESETS["quebec_law25"].title,
    ),
    Example(
        "EN · BC health number",
        "BC PHN 9000 000 018 confirmed by MSP. Ontario driver's licence A1234-56789-01234.",
        "en",
        PRESETS["phipa"].title,
    ),
    Example(
        "EN · Business and banking",
        "Our GST/HST business number is 123456782 RT 0001. EFT routing number for the bank: "
        "000300011.",
        "en",
        PRESETS["pipeda"].title,
    ),
    Example(
        "FR · Toutes les entités",
        "Numéro d'assurance maladie : BOUF 9451 1419. Numéro de passeport canadien : GA123456. "
        "Numéro de compte bancaire : 1234567.",
        "fr",
        ALL_ENTITIES,
    ),
]

DISCLAIMER = (
    "**Demo only.** Do not paste real personal data: use the synthetic examples below. "
    "Detection is pattern-based and probabilistic; a clean result here is not a "
    "compliance guarantee and not legal advice."
)
PRESET_HELP = (
    "'All entities' adds spaCy NER labels (dates, organizations, …), which are noisy on "
    "bare numbers."
)
THRESHOLD_HELP = "0.4 is recommended: weak patterns only cross it next to a context word."

#: Fixed colours for the canpii entities; anything else cycles through FALLBACK_COLORS.
ENTITY_COLORS: dict[str, str] = {
    "CA_HEALTH_NUMBER": "#e4572e",
    "CA_PASSPORT": "#3b82f6",
    "CA_BN": "#16a34a",
    "CA_BANK_ACCOUNT": "#d97706",
    "CA_DRIVER_LICENSE": "#9333ea",
    "CA_SIN": "#db2777",
    "CA_POSTAL_CODE": "#0d9488",
    "PERSON": "#64748b",
}
FALLBACK_COLORS = ["#0891b2", "#65a30d", "#c026d3", "#ea580c", "#4f46e5", "#be123c"]


@dataclass(frozen=True)
class Finding:
    """One detected entity, in the shape the table shows."""

    entity: str
    text: str
    score: float
    start: int
    end: int

    def as_row(self) -> dict[str, str | float | int]:
        """Return the finding as a table row keyed by ``TABLE_HEADERS``."""
        return {
            "entity": self.entity,
            "text": self.text,
            "score": self.score,
            "start": self.start,
            "end": self.end,
        }


@dataclass(frozen=True)
class Detection:
    """What :func:`detect` returns: the analyzed text, its findings and the redaction."""

    text: str
    findings: list[Finding]
    anonymized: str


def build_analyzer() -> AnalyzerEngine:
    """Build the bilingual analyzer (loads both spaCy small models)."""
    return create_analyzer(languages=["en", "fr"], score_threshold=0.0)


@lru_cache(maxsize=1)
def get_analyzer() -> AnalyzerEngine:
    """Process-wide analyzer for callers outside Streamlit (tests, scripts)."""
    return build_analyzer()


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


def detect(
    text: str,
    language: str,
    preset_label: str,
    threshold: float,
    *,
    analyzer: AnalyzerEngine | None = None,
    anonymizer: AnonymizerEngine | None = None,
) -> Detection:
    """Analyze ``text``; return non-overlapping findings in reading order and the redaction.

    ``analyzer`` and ``anonymizer`` default to process-wide instances; the
    Streamlit app passes the ones it caches with ``st.cache_resource``.
    """
    text = text or ""
    if not text.strip():
        return Detection(text=text, findings=[], anonymized=text)
    preset_name = PRESET_CHOICES[preset_label]
    entities = get_preset(preset_name).entity_list() if preset_name else None
    results = resolve_overlaps(
        (analyzer or get_analyzer()).analyze(
            text, language=language, entities=entities, score_threshold=threshold
        )
    )
    anonymized = (
        (anonymizer or AnonymizerEngine()).anonymize(text=text, analyzer_results=results).text
    )
    findings = [
        Finding(r.entity_type, text[r.start : r.end], round(r.score, 2), r.start, r.end)
        for r in results
    ]
    return Detection(text=text, findings=findings, anonymized=anonymized)


def entity_color(entity: str) -> str:
    """Colour for an entity label: fixed for canpii entities, stable for the rest."""
    if entity in ENTITY_COLORS:
        return ENTITY_COLORS[entity]
    return FALLBACK_COLORS[sum(entity.encode()) % len(FALLBACK_COLORS)]


def highlight_html(text: str, findings: list[Finding]) -> str:
    """Render ``text`` as HTML with each finding in a coloured, labelled span.

    Every piece of the input, and every entity label, goes through
    :func:`html.escape`; the only markup in the output is what this function
    writes itself. ``findings`` must not overlap (see :func:`resolve_overlaps`).
    """
    parts: list[str] = []
    cursor = 0
    for f in sorted(findings, key=lambda f: f.start):
        if f.start < cursor:  # defensive: never emit overlapping spans
            continue
        color = entity_color(f.entity)
        parts.append(escape(text[cursor : f.start]))
        parts.append(
            f'<mark class="canpii-entity" title="score {f.score:.2f}" style="'
            f"background:{color}26;color:inherit;border:1px solid {color}99;"
            f'border-radius:0.35em;padding:0.1em 0.35em;white-space:nowrap">'
            f"{escape(text[f.start : f.end])}"
            f'<span class="canpii-label" style="margin-left:0.45em;font-size:0.7em;'
            f'font-weight:700;letter-spacing:0.02em;color:{color}">'
            f"{escape(f.entity)}</span></mark>"
        )
        cursor = f.end
    parts.append(escape(text[cursor:]))
    return (
        '<div class="canpii-highlight" style="white-space:pre-wrap;overflow-wrap:anywhere;'
        'line-height:2.1">' + "".join(parts) + "</div>"
    )


def main() -> None:
    """Draw the Streamlit page. Streamlit reruns this on every interaction."""
    import streamlit as st

    st.set_page_config(page_title="canpii demo", page_icon="🍁", layout="wide")

    # Streamlit re-executes this file on each rerun, so module-level caches do
    # not survive; st.cache_resource keeps one analyzer per server process.
    load_analyzer = st.cache_resource(show_spinner="Loading spaCy models (first run only)…")(
        build_analyzer
    )
    load_anonymizer = st.cache_resource(show_spinner=False)(AnonymizerEngine)

    state = st.session_state
    state.setdefault("text", "")
    state.setdefault("language", "en")
    state.setdefault("preset", DEFAULT_PRESET)
    state.setdefault("threshold", DEFAULT_THRESHOLD)
    state.setdefault("detection", None)

    def run_detection() -> None:
        state["detection"] = detect(
            state["text"],
            state["language"],
            state["preset"],
            state["threshold"],
            analyzer=analyzer,
            anonymizer=anonymizer,
        )

    def load_example(example: Example) -> None:
        state["text"] = example.text
        state["language"] = example.language
        state["preset"] = example.preset
        state["threshold"] = example.threshold
        run_detection()

    st.title("canpii: Canadian PII recognizers for Presidio")
    st.markdown(
        "Provincial health cards, passport, CRA Business Number, bank accounts and "
        "driver's licences, in English and French. "
        f"Running `canpii` {canpii.__version__} · "
        "[GitHub](https://github.com/ArthurJZL/canpii) · "
        "[PyPI](https://pypi.org/project/canpii/)"
    )
    st.warning(DISCLAIMER, icon="⚠️")

    # Load the models before any widget is drawn. A click that arrives while a
    # long first load is running would interrupt it and lose the example.
    analyzer = load_analyzer()
    anonymizer = load_anonymizer()

    left, right = st.columns(2, gap="large")
    with left:
        st.text_area(
            "Text",
            key="text",
            height=170,
            placeholder="Paste synthetic text, or pick an example below.",
        )
        language_col, preset_col = st.columns(2)
        language_col.radio(
            "Language",
            list(LANGUAGES),
            key="language",
            format_func=LANGUAGES.get,
            horizontal=True,
        )
        preset_col.selectbox("Policy preset", list(PRESET_CHOICES), key="preset", help=PRESET_HELP)
        if state["preset"] == ALL_ENTITIES:
            st.caption(PRESET_HELP)
        st.slider("Score threshold", 0.0, 1.0, key="threshold", step=0.05, help=THRESHOLD_HELP)
        st.button("Detect", type="primary", on_click=run_detection, key="detect")

        st.markdown("**Synthetic examples (click to run)**")
        with st.container(horizontal=True):
            for index, example in enumerate(EXAMPLES):
                st.button(
                    example.label,
                    key=f"example_{index}",
                    on_click=load_example,
                    args=(example,),
                )

    with right:
        detection: Detection | None = state["detection"]
        st.markdown("**Detected entities**")
        if detection is None:
            st.caption("Run a detection to see the highlighted text here.")
        elif not detection.findings:
            st.caption("No entities found at this threshold.")
            st.html(highlight_html(detection.text, []))
        else:
            st.html(highlight_html(detection.text, detection.findings))
        st.markdown("**Anonymized text**")
        st.code(detection.anonymized if detection else "", language=None, wrap_lines=True)
        st.markdown("**Findings**")
        rows = [f.as_row() for f in detection.findings] if detection else []
        st.dataframe(
            rows or {header: [] for header in TABLE_HEADERS},
            hide_index=True,
            column_order=TABLE_HEADERS,
            column_config={
                "entity": st.column_config.TextColumn(width=170),
                "text": st.column_config.TextColumn(width=150),
                "score": st.column_config.NumberColumn(format="%.2f", width=65),
                "start": st.column_config.NumberColumn(width=60),
                "end": st.column_config.NumberColumn(width=60),
            },
            key="findings",
        )

    st.caption(
        "All identifiers in the examples are synthetic. Presets are engineering starting "
        "points, described in "
        "[docs/presets.md](https://github.com/ArthurJZL/canpii/blob/main/docs/presets.md)."
    )


if __name__ == "__main__":
    main()
