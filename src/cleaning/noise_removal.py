"""
SIP Insight Lab - Cleaning: Noise Removal (Task 2.4)
=====================================================
Removes noise from feedback text:
  - HTML tags stripped
  - Emojis normalised to text descriptions or removed
  - Duplicate/repeated sentences collapsed
  - URLs removed
  - Excessive punctuation collapsed
  - Platform boilerplate phrases removed

Usage:
    from src.cleaning.noise_removal import NoiseRemover
    nr = NoiseRemover()
    cleaned = nr.clean("Check out https://t.co/xyz!! 😡😡😡 Groww is bad bad bad")
"""

import re
import html
import unicodedata
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Common boilerplate phrases from app store reviews / YouTube
_BOILERPLATE_PHRASES = [
    r"please\s+rate\s+this\s+app",
    r"click\s+the\s+thumbs\s+up",
    r"like\s+and\s+subscribe",
    r"hit\s+the\s+bell\s+icon",
    r"download\s+the\s+app\s+now",
    r"use\s+my\s+referral\s+code",
]
_BOILERPLATE_RE = re.compile(
    "|".join(_BOILERPLATE_PHRASES), flags=re.IGNORECASE
)

# URL patterns
_URL_RE = re.compile(
    r"http[s]?://(?:[a-zA-Z]|[0-9]|[$\-_@.&+!*(),]|%[0-9a-fA-F]{2})+"
    r"|www\.[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}"
)

# Excessive punctuation: 3+ of the same char -> 2
_PUNCT_RE = re.compile(r"([!?.,])\1{2,}")

# Repeated word sequences: "bad bad bad" -> "bad"
_WORD_REPEAT_RE = re.compile(r"\b(\w+)( \1){2,}\b", re.IGNORECASE)


class NoiseRemover:
    """
    Cleans feedback text of HTML, URLs, excessive punctuation, and repeats.

    Args:
        remove_emojis: If True, strip all emoji characters entirely.
                       If False (default), keep them as-is (they can be
                       informative sentiment signals).
        min_length:    Minimum cleaned text length to be considered valid.
    """

    def __init__(
        self,
        remove_emojis: bool = False,
        min_length: int = 15,
    ):
        self.remove_emojis = remove_emojis
        self.min_length = min_length

    def clean(self, text: str) -> str:
        """
        Apply the full noise removal pipeline to text.

        Returns:
            Cleaned text string. May be empty if the input was all noise.
        """
        if not text:
            return ""

        # 1. Decode HTML entities (&amp; -> &, &lt; -> <, etc.)
        text = html.unescape(text)

        # 2. Strip HTML tags
        text = re.sub(r"<[^>]+>", " ", text)

        # 3. Remove URLs
        text = _URL_RE.sub(" ", text)

        # 4. Remove boilerplate phrases
        text = _BOILERPLATE_RE.sub(" ", text)

        # 5. Handle emojis
        if self.remove_emojis:
            text = self._strip_emojis(text)

        # 6. Collapse excessive punctuation: !!! -> !!
        text = _PUNCT_RE.sub(r"\1\1", text)

        # 7. Collapse repeated words: "bad bad bad" -> "bad"
        text = _WORD_REPEAT_RE.sub(r"\1", text)

        # 8. Remove duplicate sentences
        text = self._dedup_sentences(text)

        # 9. Normalise whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def is_valid(self, text: str) -> bool:
        """Return True if the cleaned text meets minimum length."""
        return len(text.strip()) >= self.min_length

    def _strip_emojis(self, text: str) -> str:
        """Remove all Unicode characters in emoji ranges."""
        return "".join(
            c for c in text
            if not (
                unicodedata.category(c) in ("So", "Sk")
                or "\U0001F000" <= c <= "\U0001FFFF"
                or "\U00002600" <= c <= "\U000027BF"
            )
        )

    def _dedup_sentences(self, text: str) -> str:
        """Remove exact duplicate sentences (case-insensitive)."""
        # Split on sentence-ending punctuation
        sentences = re.split(r"(?<=[.!?])\s+", text)
        seen: set[str] = set()
        unique: list[str] = []
        for s in sentences:
            key = s.strip().lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(s.strip())
        return " ".join(unique)

    def clean_batch(self, texts: list[str]) -> list[str]:
        """Clean a list of texts."""
        return [self.clean(t) for t in texts]


if __name__ == "__main__":
    nr = NoiseRemover()
    test_cases = [
        "Check out https://groww.in!! <b>Great app</b> 😡😡😡 SIP cancelled cancelled cancelled",
        "Bad app. Bad app. Bad app. Please rate this app!!! Very frustrating!!!",
        "&lt;p&gt;My SIP failed. My SIP failed.&lt;/p&gt;",
        "Normal clean text about SIP investment working fine.",
    ]
    for t in test_cases:
        c = nr.clean(t)
        print(f"IN : {t}")
        print(f"OUT: {c}")
        print()
