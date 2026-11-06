"""Shared base class for canpii pattern recognizers."""

from __future__ import annotations

import re
from typing import ClassVar

from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult
from presidio_analyzer.nlp_engine import NlpArtifacts


class CanadianPatternRecognizer(PatternRecognizer):
    """Base class adding a two-tier validation policy to ``PatternRecognizer``.

    Subclasses may implement two hooks:

    * :meth:`verified_check` - a rule published by the issuing authority.
      A failure **rejects** the match (via Presidio's ``invalidate_result``).
    * :meth:`unverified_check` - a rule that is only secondary- or
      community-sourced. A pass adds :attr:`UNVERIFIED_BONUS` to the score; a
      failure is ignored unless the recognizer was created with
      ``strict=True``, in which case the match is rejected.

    This keeps recall high when our understanding of an identifier is not
    backed by an official specification, while still rewarding matches that
    look right.

    **Negative context.** Weak matches (base score <= 0.3) are dropped when a
    word from :attr:`NEGATIVE_CONTEXT` ("phone", "call", "order", "téléphone",
    "commande", ...) appears shortly before them. This runs *before*
    Presidio's context enhancement, so "Call the health clinic at 4165550123"
    is not reported as a health number just because "health" is nearby.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param name: Recognizer name (defaults to the class name)
    :param strict: Also reject matches that fail unverified rules
    """

    COUNTRY_CODE = "ca"

    ENTITY: ClassVar[str]
    PATTERNS: ClassVar[list[Pattern]]
    CONTEXT: ClassVar[list[str]]
    #: Province/territory code (ISO 3166-2:CA suffix) or None if federal.
    PROVINCE: ClassVar[str | None] = None
    #: Short human-readable label used by exporters and docs.
    LABEL: ClassVar[str] = ""
    UNVERIFIED_BONUS: ClassVar[float] = 0.1
    #: Words that, shortly before a weak match, indicate it is something else.
    NEGATIVE_CONTEXT: ClassVar[tuple[str, ...]] = (
        "phone",
        "telephone",
        "tel",
        "call",
        "fax",
        "cell",
        "mobile",
        "extension",
        "ext",
        "order",
        "invoice",
        "tracking",
        "sku",
        "téléphone",
        "appelez",
        "appeler",
        "cellulaire",
        "télécopieur",
        "poste",
        "commande",
        "facture",
        "suivi",
    )
    #: Characters before a match searched for negative context.
    NEGATIVE_CONTEXT_WINDOW: ClassVar[int] = 48
    #: Matches at or below this base score are subject to negative context.
    NEGATIVE_CONTEXT_MAX_SCORE: ClassVar[float] = 0.3

    def __init__(
        self,
        patterns: list[Pattern] | None = None,
        context: list[str] | None = None,
        supported_language: str = "en",
        supported_entity: str | None = None,
        name: str | None = None,
        strict: bool = False,
    ) -> None:
        self.strict = strict
        patterns = patterns if patterns else self.default_patterns()
        context = context if context else list(self.CONTEXT)
        super().__init__(
            supported_entity=supported_entity or self.ENTITY,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    @classmethod
    def default_patterns(cls) -> list[Pattern]:
        """Return fresh copies of the class patterns (Pattern objects cache state)."""
        return [Pattern(p.name, p.regex, p.score) for p in cls.PATTERNS]

    # -- validation hooks -------------------------------------------------

    def verified_check(self, pattern_text: str) -> bool | None:
        """Return False to reject a match based on an official rule."""
        return None

    def unverified_check(self, pattern_text: str) -> bool | None:
        """Return True/False for a secondary/community rule, None if n/a."""
        return None

    def has_negative_context(self, text: str, start: int) -> bool:
        """Return True if a negative-context word occurs shortly before ``start``."""
        window = text[max(0, start - self.NEGATIVE_CONTEXT_WINDOW) : start]
        return self._negative_re().search(window) is not None

    @classmethod
    def _negative_re(cls) -> re.Pattern[str]:
        cached = cls.__dict__.get("_NEGATIVE_RE_CACHE")
        if cached is None:
            words = "|".join(re.escape(w) for w in cls.NEGATIVE_CONTEXT)
            cached = re.compile(rf"(?<!\w)(?:{words})(?!\w)", re.IGNORECASE)
            cls._NEGATIVE_RE_CACHE = cached
        return cached

    # -- Presidio integration ---------------------------------------------

    def invalidate_result(self, pattern_text: str) -> bool | None:
        """Reject on official-rule failure, or unverified failure if strict."""
        if self.verified_check(pattern_text) is False:
            return True
        return self.strict and self.unverified_check(pattern_text) is False

    def analyze(
        self,
        text: str,
        entities: list[str],
        nlp_artifacts: NlpArtifacts | None = None,
        regex_flags: int | None = None,
    ) -> list[RecognizerResult]:
        """Run pattern matching, then apply the unverified-rule bonus."""
        results = [
            r
            for r in super().analyze(text, entities, nlp_artifacts, regex_flags)
            if not (
                self.NEGATIVE_CONTEXT
                and r.score <= self.NEGATIVE_CONTEXT_MAX_SCORE
                and self.has_negative_context(text, r.start)
            )
        ]
        for result in results:
            if self.unverified_check(text[result.start : result.end]) is True:
                new_score = round(min(1.0, result.score + self.UNVERIFIED_BONUS), 4)
                result.score = new_score
                if result.analysis_explanation is not None:
                    result.analysis_explanation.set_improved_score(new_score)
                    result.analysis_explanation.append_textual_explanation_line(
                        f"canpii: +{self.UNVERIFIED_BONUS} for passing an "
                        "unverified (secondary/community-sourced) check"
                    )
        return results
