"""
SIP Insight Lab - Cleaning: PII Scrubber (Tasks 2.2 + 2.3)
============================================================
Removes Personally Identifiable Information from feedback text
using two complementary approaches:

  1. NER-based: spaCy en_core_web_sm tags PERSON, EMAIL, PHONE, ORG
  2. Regex-based: UPI IDs, Aadhaar numbers, PAN cards, account numbers,
                  phone patterns, email patterns (belt-and-suspenders)

All detected spans are replaced with [REDACTED:<TYPE>].
The scrubber logs WHAT was redacted (type + count) but NEVER the values.

Graceful degradation:
  If spaCy is not installed or model is missing, falls back to regex-only mode.

Install:
    pip install spacy
    python -m spacy download en_core_web_sm

Usage:
    from src.cleaning.pii_scrubber import PIIScrubber
    scrubber = PIIScrubber()
    cleaned, log = scrubber.scrub("Call me at 9876543210, my UPI is john@paytm")
    # cleaned -> "Call me at [REDACTED:PHONE], my UPI is [REDACTED:UPI_ID]"
    # log     -> {"PHONE": 1, "UPI_ID": 1, "total_redacted": 2}
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns (Tasks 2.2 + 2.3)
# ---------------------------------------------------------------------------

_PATTERNS: list[tuple[str, str, str]] = [
    # (label, pattern, replacement_tag)

    # Email addresses
    ("EMAIL",
     r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
     "EMAIL"),

    # Indian mobile numbers: +91 XXXXXXXXXX or 10-digit starting with 6-9
    ("PHONE",
     r"(?:\+91[\s\-]?)?[6-9]\d{9}",
     "PHONE"),

    # UPI IDs: anything@bankname or handle@upi
    ("UPI_ID",
     r"[a-zA-Z0-9._\-]{3,}@(?:paytm|gpay|phonepe|ybl|okicici|oksbi|okaxis|okhdfcbank|upi|apl|waicici|"
     r"ibl|pnb|federal|airtel|jio|indus|rbl|kotak|axisbank|hdfcbank|sbi|icici|[a-zA-Z]{3,10})",
     "UPI_ID"),

    # Aadhaar numbers: 12 digits (sometimes spaced: XXXX XXXX XXXX)
    ("AADHAAR",
     r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b",
     "AADHAAR"),

    # PAN cards: ABCDE1234F pattern
    ("PAN",
     r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
     "PAN"),

    # Bank account numbers: 9–18 digit strings (conservative — require word boundaries)
    ("ACCOUNT_NO",
     r"\b(?:account|a/c|acc)[\s#:]*\d{9,18}\b",
     "ACCOUNT_NO"),

    # IFSC codes: 4 letters + 0 + 6 alphanumeric
    ("IFSC",
     r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
     "IFSC"),
]

_COMPILED: list[tuple[str, re.Pattern, str]] = [
    (label, re.compile(pattern, re.IGNORECASE), tag)
    for label, pattern, tag in _PATTERNS
]

# spaCy NER entity types to redact
_NER_TYPES = {"PERSON", "ORG", "GPE", "LOC", "EMAIL", "PHONE"}


class PIIScrubber:
    """
    Removes PII from text using NER + regex.

    Args:
        use_ner: If True, attempt to load spaCy model for NER.
                 Falls back to regex-only if spaCy is unavailable.
        spacy_model: spaCy model name to load.
    """

    def __init__(
        self,
        use_ner: bool = True,
        spacy_model: str = "en_core_web_sm",
    ):
        self._nlp = None
        if use_ner:
            self._nlp = self._load_spacy(spacy_model)

        mode = "NER + regex" if self._nlp else "regex-only"
        logger.info("PIIScrubber initialised in %s mode.", mode)

    def _load_spacy(self, model_name: str):
        try:
            import spacy
            nlp = spacy.load(model_name)
            logger.info("spaCy model '%s' loaded.", model_name)
            return nlp
        except ImportError:
            logger.warning("spaCy not installed. Using regex-only PII scrubbing.")
        except OSError:
            logger.warning(
                "spaCy model '%s' not found. Run: python -m spacy download %s  "
                "Falling back to regex-only mode.",
                model_name, model_name,
            )
        return None

    def scrub(self, text: str) -> tuple[str, dict]:
        """
        Remove PII from text.

        Args:
            text: Raw or partially cleaned text string.

        Returns:
            (cleaned_text, removal_log)
            where removal_log is {entity_type: count, "total_redacted": N}
        """
        if not text:
            return text, {"total_redacted": 0}

        removal_log: dict[str, int] = {}

        # Step 1: NER-based redaction (if spaCy available)
        if self._nlp:
            text, ner_log = self._ner_scrub(text)
            removal_log.update(ner_log)

        # Step 2: Regex-based redaction (belt-and-suspenders)
        text, regex_log = self._regex_scrub(text)
        for k, v in regex_log.items():
            removal_log[k] = removal_log.get(k, 0) + v

        removal_log["total_redacted"] = sum(
            v for k, v in removal_log.items() if k != "total_redacted"
        )
        return text, removal_log

    def _ner_scrub(self, text: str) -> tuple[str, dict]:
        """Replace NER-tagged spans with [REDACTED:<TYPE>] from right to left."""
        doc = self._nlp(text)
        log: dict[str, int] = {}
        spans_to_redact = [
            (ent.start_char, ent.end_char, ent.label_)
            for ent in doc.ents
            if ent.label_ in _NER_TYPES
        ]
        # Replace right-to-left to preserve character offsets
        for start, end, label in sorted(spans_to_redact, key=lambda x: x[0], reverse=True):
            text = f"{text[:start]}[REDACTED:{label}]{text[end:]}"
            log[label] = log.get(label, 0) + 1
        return text, log

    def _regex_scrub(self, text: str) -> tuple[str, dict]:
        """Apply all regex patterns to the text."""
        log: dict[str, int] = {}
        for label, pattern, tag in _COMPILED:
            matches = pattern.findall(text)
            if matches:
                text = pattern.sub(f"[REDACTED:{tag}]", text)
                log[tag] = log.get(tag, 0) + len(matches)
        return text, log

    def scrub_batch(self, texts: list[str]) -> list[tuple[str, dict]]:
        """Scrub a list of texts. Returns list of (cleaned_text, log) tuples."""
        return [self.scrub(t) for t in texts]

    def has_pii(self, text: str) -> bool:
        """Quick check: does this text contain detectable PII?"""
        _, log = self.scrub(text)
        return log.get("total_redacted", 0) > 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scrubber = PIIScrubber(use_ner=False)  # regex-only for quick test
    test_cases = [
        "My name is Rahul and my number is 9876543210",
        "Email me at test.user@gmail.com for the refund",
        "My UPI is rahul@paytm and account is acc 123456789012",
        "Aadhaar: 1234 5678 9012 for KYC",
        "PAN: ABCDE1234F linked to my Groww account",
        "The Groww app is great for SIP investing",  # no PII
    ]
    for t in test_cases:
        cleaned, log = scrubber.scrub(t)
        print(f"ORIGINAL : {t}")
        print(f"CLEANED  : {cleaned}")
        print(f"LOG      : {log}")
        print()
