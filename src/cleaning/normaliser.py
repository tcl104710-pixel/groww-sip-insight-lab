"""
SIP Insight Lab - Cleaning: Text Normaliser (Task 2.5)
=======================================================
Final normalisation step in the cleaning pipeline:
  - Unicode NFKC normalisation (full-width -> ASCII, ligatures, etc.)
  - Encoding artifact fixes (mojibake patterns)
  - Whitespace standardisation
  - Preserve case (do NOT lowercase — sentiment & NER depend on casing)

Note: Lowercasing is intentionally NOT done here. The LLM handles
case-insensitive understanding natively. Lowercasing would destroy
useful signals like "SIP", "NAV", "KYC" which are meaningful acronyms.

Usage:
    from src.cleaning.normaliser import TextNormaliser
    tn = TextNormaliser()
    text = tn.normalise("  My\u00a0SIP\t\twas\r\ncancelled  ")
    # -> "My SIP was cancelled"
"""

import re
import unicodedata
import logging

logger = logging.getLogger(__name__)

# Common mojibake / encoding artifacts seen in scraped data
_ENCODING_FIXES = [
    ("â€™",  "'"),     # curly apostrophe mangled
    ("â€œ",  '"'),     # left double quote mangled
    ("â€\x9d", '"'),   # right double quote mangled
    ("â€”",  "—"),     # em dash mangled
    ("â€“",  "–"),     # en dash mangled
    ("â€¦",  "…"),     # ellipsis mangled
    ("\u00a0", " "),   # non-breaking space -> regular space
    ("\u200b", ""),    # zero-width space -> removed
    ("\u200c", ""),    # zero-width non-joiner
    ("\u200d", ""),    # zero-width joiner
    ("\ufeff", ""),    # BOM
]

_MULTI_SPACE_RE  = re.compile(r"[ \t]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")


class TextNormaliser:
    """
    Final cleaning step: normalise Unicode, fix encoding artifacts,
    standardise whitespace. Preserves original casing.

    Args:
        unicode_form: Unicode normalisation form (default: NFKC).
                      NFKC maps full-width chars to ASCII equivalents.
    """

    def __init__(self, unicode_form: str = "NFKC"):
        self.unicode_form = unicode_form

    def normalise(self, text: str) -> str:
        """
        Apply full normalisation pipeline.

        Returns:
            Normalised text string.
        """
        if not text:
            return ""

        # 1. Normalize smart/curly quotes and dashes
        text = (
            text.replace("’", "'")
            .replace("‘", "'")
            .replace("“", '"')
            .replace("”", '"')
            .replace("–", "-")
            .replace("—", " - ")
        )

        # 2. Fix encoding artifacts (mojibake)
        for pattern, replacement in _ENCODING_FIXES:
            text = text.replace(pattern, replacement)

        # 3. Unicode normalisation (NFKC: compatibility decomposition + canonical composition)
        text = unicodedata.normalize(self.unicode_form, text)

        # 3. Standardise line endings -> single newline
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 4. Collapse runs of 3+ newlines -> two newlines (preserve paragraph breaks)
        text = _MULTI_NEWLINE_RE.sub("\n\n", text)

        # 5. Collapse multiple spaces/tabs (but not newlines) into single space
        text = _MULTI_SPACE_RE.sub(" ", text)

        # 6. Strip leading/trailing whitespace
        text = text.strip()

        return text

    def normalise_batch(self, texts: list[str]) -> list[str]:
        """Normalise a list of texts."""
        return [self.normalise(t) for t in texts]


if __name__ == "__main__":
    tn = TextNormaliser()
    tests = [
        "  My\u00a0SIP\t\twas\r\ncancelled  ",
        "Iâ€™m very frustrated with Groww",
        "ｆｕｌｌ－ｗｉｄｔｈ　ｔｅｘｔ",   # full-width -> ASCII via NFKC
        "Normal text with no issues",
    ]
    for t in tests:
        n = tn.normalise(t)
        print(f"IN : {repr(t)}")
        print(f"OUT: {repr(n)}")
        print()
