"""Keyword-based NLP signal extractor for geopolitical text."""

from __future__ import annotations

import logging
import re
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Signal keyword lists
# ---------------------------------------------------------------------------

_SANCTIONS_KEYWORDS = [
    r"\bsanction", r"\bembargo", r"\bblacklist", r"\bfreeze assets",
    r"\btrade ban", r"\bexport control",
]
_INSTABILITY_KEYWORDS = [
    r"\binstabilit", r"\bprotest", r"\bstrike", r"\brioting?\b", r"\bcoup\b",
    r"\bgovernment collapse", r"\bpolitical crisis", r"\bunrest",
]
_TRADE_RESTRICTION_KEYWORDS = [
    r"\btariff", r"\btrade restriction", r"\bimport ban", r"\bexport ban",
    r"\bcustoms block", r"\btrade war", r"\bquota",
]
_CONFLICT_KEYWORDS = [
    r"\bwar\b", r"\bmilitary operation", r"\bairstr", r"\bbombard",
    r"\bnaval blockade", r"\bairspace clos", r"\bconflict zone",
    r"\bceasefire", r"\boffensive", r"\bshelling",
]
_HIGH_SEVERITY_KEYWORDS = [
    r"\bwar\b", r"\bnaval blockade", r"\bairspace clos", r"\bmilitary operation",
    r"\bbombard", r"\bshelling",
]


def _match_any(text: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


def _severity(text: str, signals: dict[str, bool]) -> float:
    """Compute a 0–1 severity score from matched signals."""
    score = 0.0
    if signals["conflict"]:
        score += 0.5
        if _match_any(text, _HIGH_SEVERITY_KEYWORDS):
            score += 0.3
    if signals["sanctions"]:
        score += 0.1
    if signals["instability"]:
        score += 0.1
    if signals["trade_restrictions"]:
        score += 0.05
    return min(score, 1.0)


# ---------------------------------------------------------------------------
# Pydantic output model
# ---------------------------------------------------------------------------

class GeopoliticalSignal(BaseModel):
    sanctions: bool = False
    instability: bool = False
    trade_restrictions: bool = False
    conflict: bool = False
    severity: float = 0.0


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------

class NLPSignalExtractor:
    """Extracts geopolitical signals from text using keyword/regex matching."""

    def extract(self, text: str, language: str = "en") -> GeopoliticalSignal:
        """
        Returns a GeopoliticalSignal with boolean flags and a severity score.

        Language detection is attempted via langdetect when *language* is not
        explicitly provided; falls back gracefully if the library is absent.
        """
        detected_lang = self._detect_language(text, language)
        if detected_lang != "en":
            # For non-English text we still attempt extraction on the raw text;
            # a translation layer would be added in production.
            logger.debug("Non-English text detected (%s); extracting on raw text.", detected_lang)

        signals: dict[str, bool] = {
            "sanctions": _match_any(text, _SANCTIONS_KEYWORDS),
            "instability": _match_any(text, _INSTABILITY_KEYWORDS),
            "trade_restrictions": _match_any(text, _TRADE_RESTRICTION_KEYWORDS),
            "conflict": _match_any(text, _CONFLICT_KEYWORDS),
        }
        sev = _severity(text, signals)
        return GeopoliticalSignal(**signals, severity=sev)

    @staticmethod
    def _detect_language(text: str, default: str) -> str:
        try:
            from langdetect import detect  # type: ignore[import]
            return detect(text)
        except Exception:  # noqa: BLE001
            return default
