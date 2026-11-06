"""
SIP Insight Lab - Cleaning: Language Detector (Task 2.1)
=========================================================
Detects the language of a feedback item and filters for
English (en) and Hindi (hi) only.

Uses langdetect (primary) with a simple Unicode-script fallback
for short Hindi texts that langdetect may misclassify.

Usage:
    from src.cleaning.lang_detect import LanguageDetector
    ld = LanguageDetector()
    lang = ld.detect("My SIP was cancelled")    # -> "en"
    ok   = ld.is_accepted("My SIP was cancelled") # -> True
"""

import logging
import re
import unicodedata

logger = logging.getLogger(__name__)

ACCEPTED_LANGS = {"en", "hi"}

# Devanagari Unicode block — strong signal of Hindi/Marathi text
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


class LanguageDetector:
    """
    Detects the language of text and decides whether to keep or discard.

    Strategy:
      1. If text contains significant Devanagari script -> "hi" (accept)
      2. Otherwise use langdetect library
      3. If langdetect raises (text too short/ambiguous) -> default "en"
    """

    def __init__(self, accepted: set[str] = ACCEPTED_LANGS):
        self.accepted = accepted
        try:
            import langdetect
            self._langdetect = langdetect
            logger.info("LanguageDetector: langdetect library loaded.")
        except ImportError:
            self._langdetect = None
            logger.warning(
                "langdetect not installed — defaulting all text to 'en'. "
                "Run: pip install langdetect"
            )

    def detect(self, text: str) -> str:
        """
        Return the ISO 639-1 language code for the text.
        Returns 'en' if detection fails or is ambiguous.
        """
        if not text or not text.strip():
            return "unknown"

        # Strong Devanagari signal (>5% of chars are Devanagari)
        deva_count = len(_DEVANAGARI_RE.findall(text))
        if deva_count / max(len(text), 1) > 0.05:
            return "hi"

        if self._langdetect is None:
            return "en"

        try:
            from langdetect import detect as _detect
            lang = _detect(text)
            return lang
        except Exception:
            return "en"  # Safe default for short/ambiguous text

    def is_accepted(self, text: str) -> bool:
        """Return True if the detected language is in the accepted set."""
        return self.detect(text) in self.accepted

    def filter_batch(self, texts: list[str]) -> list[tuple[str, str, bool]]:
        """
        Filter a batch of texts.
        Returns list of (text, detected_lang, is_accepted) tuples.
        """
        return [(t, self.detect(t), self.is_accepted(t)) for t in texts]


if __name__ == "__main__":
    ld = LanguageDetector()
    samples = [
        "My SIP was cancelled after 3 failed debits. Very frustrated with Groww.",
        "मेरा SIP अपने आप रद्द हो गया, बहुत परेशान हूँ।",
        "Le SIP est annulé",  # French — should be rejected
        "短い",               # Japanese — should be rejected
    ]
    for s in samples:
        lang = ld.detect(s)
        accepted = ld.is_accepted(s)
        print(f"[{lang}] accepted={accepted}  {s[:60]}")
