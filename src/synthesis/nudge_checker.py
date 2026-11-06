"""
SIP Insight Lab — Nudge & Ethics Guardrail Checker (Task 4.10)
==============================================================
Validates hypothesis cards, interview guides, and synthesis outputs
against the mandatory 4-point Nudge Checklist:
  1. Fear / loss aversion / FOMO language → Block / Remove
  2. False urgency to re-invest → Block / Remove
  3. Specific fund or stock recommendations → Hard Block
  4. Unvalidated causal claims → Must be framed as hypothesis, not finding
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
import re
import logging

logger = logging.getLogger("synthesis.nudge_checker")


@dataclass
class NudgeCheckResult:
    card_id: str
    passed: bool
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sanitized_text: Optional[str] = None

    def summary(self) -> Dict[str, Any]:
        return {
            "card_id": self.card_id,
            "passed": self.passed,
            "violation_count": len(self.violations),
            "warning_count": len(self.warnings),
            "violations": self.violations,
            "warnings": self.warnings,
        }


class NudgeChecker:
    """
    Enforces ethical and regulatory constraints on hypothesis cards and synthesized texts.
    """

    # Check 1: Fear, Loss Aversion, FOMO
    FEAR_PATTERNS = [
        (r"\b(don't miss out|fear of missing out|fomo)\b", "FOMO / Regret language"),
        (r"\b(lose (all )?your wealth|financial ruin|devastating loss)\b", "Catastrophic loss language"),
        (r"\b(panic(king)?|terrified|paralyzed with fear)\b", "Fear-inducing emotional rhetoric"),
        (r"\b(you will regret|costly mistake that will haunt)\b", "Manipulative regret nudge"),
    ]

    # Check 2: False Urgency to Re-Invest
    URGENCY_PATTERNS = [
        (r"\b(act fast|hurry|invest now before|immediate action required)\b", "Manufactured urgency to invest"),
        (r"\b(limited time|clock is ticking|before it's too late)\b", "Artificial investment deadline"),
        (r"\b(start investing right this second)\b", "Aggressive investment prompt"),
    ]

    # Check 3: Specific Fund or Stock Recommendations (SEBI Advisory Barrier)
    FUND_RECOMMENDATION_PATTERNS = [
        (r"\b(buy|sell|switch into)\s+([a-z0-9\s]+(?:fund|etf|stock|equity))\b", "Direct buy/sell fund instruction"),
        (r"\b(?:recommend|suggest investing in)\s+(?:quant|nippon|hdfc|sbi|mirae|parag parikh|uti|axis|tata|icici pru)\b", "Specific AMC recommendation"),
        (r"\b(?:guaranteed|assured|risk-free)\s+(?:returns?|cagr|profits?)\b", "Misleading return guarantee"),
    ]

    # Check 4: Unvalidated Causal Claims (must be framed as hypotheses)
    CAUSAL_CLAIM_PATTERNS = [
        (r"\b(proves beyond doubt|undeniable proof that|conclusively demonstrates)\b", "Unvalidated definitive causal claim"),
        (r"\b(is the sole cause of|guaranteed to fix churn entirely)\b", "Overstated causal link"),
    ]

    def check_text(self, text: str, card_id: str = "card_unknown") -> NudgeCheckResult:
        """
        Evaluate arbitrary text against all 4 guardrail rules.
        Separates platform synthesis from verbatim user quotes.
        """
        violations: List[str] = []
        warnings: List[str] = []

        # If full markdown card is provided, separate verbatim quotes from platform synthesized content
        synth_parts = []
        in_quotes = False
        for line in text.split("\n"):
            if "### Supporting Quotes" in line:
                in_quotes = True
                continue
            elif in_quotes and line.startswith("### "):
                in_quotes = False

            if not in_quotes:
                synth_parts.append(line)

        synth_text = "\n".join(synth_parts).lower()
        full_text_lower = text.lower()

        # Check 1: Fear / FOMO (checked on platform synthesis)
        for pat, desc in self.FEAR_PATTERNS:
            if re.search(pat, synth_text):
                violations.append(f"Check 1 Failed (Fear/FOMO): {desc}")

        # Check 2: Urgency (checked on platform synthesis)
        for pat, desc in self.URGENCY_PATTERNS:
            if re.search(pat, synth_text):
                violations.append(f"Check 2 Failed (Urgency): {desc}")

        # Check 3: Fund / Stock Advice (checked on platform synthesis)
        for pat, desc in self.FUND_RECOMMENDATION_PATTERNS:
            if re.search(pat, synth_text):
                violations.append(f"Check 3 Failed (Specific Fund Advice): {desc}")

        # Check 4: Unvalidated Causal Claims (checked on platform synthesis)
        for pat, desc in self.CAUSAL_CLAIM_PATTERNS:
            if re.search(pat, synth_text):
                warnings.append(f"Check 4 Warning (Causal Overstatement): {desc} — Reframe as hypothesis")

        # Sanitize / Replace overly definitive terms if found
        sanitized = text
        for pat, _ in self.CAUSAL_CLAIM_PATTERNS:
            sanitized = re.sub(pat, "hypothesizes that", sanitized, flags=re.IGNORECASE)

        passed = len(violations) == 0

        return NudgeCheckResult(
            card_id=card_id,
            passed=passed,
            violations=violations,
            warnings=warnings,
            sanitized_text=sanitized if passed else None,
        )

    def generate_review_report_markdown(
        self,
        results: List[NudgeCheckResult],
        title: str = "SIP Insight Lab — Nudge & Ethics Checklist Review Log",
    ) -> str:
        """
        Format markdown audit log for PM and Compliance review.
        """
        total = len(results)
        passed_count = sum(1 for r in results if r.passed)
        failed_count = total - passed_count

        lines = [
            f"# {title}",
            "",
            f"- **Total Cards Evaluated:** {total}",
            f"- **Cards Passed Checklist:** {passed_count} / {total}",
            f"- **Cards Flagged / Blocked:** {failed_count}",
            f"- **Compliance Standard:** Zero Tolerance for Investment Advice, Fear/FOMO Rhetoric, and Artificial Urgency",
            "",
            "---",
            "",
            "## Checklist Verification Summary",
            "",
            "| Card ID | Fear/FOMO Check | Urgency Check | Advisory Check | Hypothesis Framing | Overall Status |",
            "|---|:---:|:---:|:---:|:---:|:---:|",
        ]

        for r in results:
            v_text = "; ".join(r.violations) if r.violations else "None"
            w_text = "; ".join(r.warnings) if r.warnings else "Compliant"
            has_c1 = not any("Check 1" in v for v in r.violations)
            has_c2 = not any("Check 2" in v for v in r.violations)
            has_c3 = not any("Check 3" in v for v in r.violations)
            has_c4 = len(r.warnings) == 0

            status = "✅ **PASSED**" if r.passed else "❌ **FLAGGED**"

            lines.append(
                f"| `{r.card_id}` | {'✅' if has_c1 else '❌'} | {'✅' if has_c2 else '❌'} | "
                f"{'✅' if has_c3 else '❌'} | {'✅' if has_c4 else '⚠️ Warning'} | {status} |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## Detailed Review Notes",
            "",
        ])

        for r in results:
            lines.append(f"### Card: `{r.card_id}`")
            if r.passed and not r.warnings:
                lines.append("- **Status:** 100% Compliant with ethical guidelines. Ready for product distribution.")
            else:
                if r.violations:
                    lines.append(f"- **Violations Identified:** {len(r.violations)}")
                    for v in r.violations:
                        lines.append(f"  - ❌ {v}")
                if r.warnings:
                    lines.append(f"- **Warnings (Hypothesis Framing):** {len(r.warnings)}")
                    for w in r.warnings:
                        lines.append(f"  - ⚠️ {w}")
            lines.append("")

        return "\n".join(lines)
