"""
SIP Insight Lab — Addressability Checker (Task 4.5)
===================================================
Rules-based checker that evaluates whether a root cause bucket or
opportunity is solvable within ethical and regulatory boundaries.

Key Rule:
  Score = 1.0 if solvable without investment advice or fear nudges;
  Score = 0.0 otherwise.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import re
import logging

logger = logging.getLogger("synthesis.addressability")


@dataclass
class AddressabilityResult:
    root_cause: str
    score: float  # 0.0 or 1.0
    addressable: bool
    intervention_type: str
    rationale: str
    ethical_flags: List[str]


class AddressabilityChecker:
    """
    Evaluates addressability of root cause buckets and intervention concepts.
    Enforces SEBI non-advisory boundary and anti-manipulation guidelines.
    """

    # Prohibited patterns indicating investment advice or FOMO/fear
    INVESTMENT_ADVICE_PATTERNS = [
        r"\b(buy|sell|switch to)\s+([a-z0-9\s]+fund|stock|equity)\b",
        r"\b(guaranteed\s+returns?|best\s+performing\s+fund)\b",
        r"\b(outperform|beat the market|top rated)\b",
    ]

    FEAR_FOMO_PATTERNS = [
        r"\b(don't miss out|hurry|act now|limited time|before it's too late)\b",
        r"\b(fear of losing|panic|regret|disaster|lose all your money)\b",
        r"\b(urgent|immediate action required|warning: you will lose)\b",
    ]

    # Taxonomy default addressability mappings
    TAXONOMY_RULES = {
        "RC-01": {
            "addressable": True,
            "score": 1.0,
            "intervention_type": "automated_recovery",
            "rationale": "High addressability via UPI AutoPay migration, pre-debit balance nudges, and smart auto-retry before 3-strike cancellation.",
        },
        "RC-02": {
            "addressable": True,
            "score": 1.0,
            "intervention_type": "ux_friction_reduction",
            "rationale": "High addressability via simplified SIP management UI, transparent error codes, and self-serve pause/skip controls.",
        },
        "RC-03": {
            "addressable": True,
            "score": 1.0,
            "intervention_type": "expectation_setting",
            "rationale": "Addressable via realistic range-based CAGR calculators, rolling return visualisations, and 3-5 year horizon education.",
        },
        "RC-04": {
            "addressable": False,
            "score": 0.0,
            "intervention_type": "liquidity_relief",
            "rationale": "Personal cash-flow shock / job loss is an external macroeconomic constraint, though flexible SIP pause helps mitigate.",
        },
        "RC-05": {
            "addressable": False,
            "score": 0.0,
            "intervention_type": "planned_redemption",
            "rationale": "Deliberate informed goal redemption or planned allocation rebalancing is natural investor lifecycle, not product failure.",
        },
        "RC-06": {
            "addressable": True,
            "score": 1.0,
            "intervention_type": "financial_literacy",
            "rationale": "Addressable via in-app contextual coaching explaining NAV fluctuations, rupee-cost averaging, and normal market volatility.",
        },
        "RC-07": {
            "addressable": True,
            "score": 1.0,
            "intervention_type": "peer_anchoring",
            "rationale": "Addressable by countering speculative finfluencer narratives with transparent historical fund benchmark facts.",
        },
        "RC-99": {
            "addressable": False,
            "score": 0.0,
            "intervention_type": "unclassifiable",
            "rationale": "Ambiguous or incomplete feedback cannot be addressed without further qualitative discovery.",
        },
    }

    def evaluate(
        self,
        root_cause: str,
        proposed_intervention: Optional[str] = None,
    ) -> AddressabilityResult:
        """
        Evaluate addressability for a given root cause and optional proposed solution.
        """
        rule = self.TAXONOMY_RULES.get(
            root_cause,
            {
                "addressable": False,
                "score": 0.0,
                "intervention_type": "unknown",
                "rationale": f"Unrecognized root cause code: {root_cause}",
            },
        )

        flags: List[str] = []
        score = rule["score"]
        addressable = rule["addressable"]

        # If a proposed intervention text is supplied, check for ethical violations
        if proposed_intervention:
            text_lower = proposed_intervention.lower()

            for pat in self.INVESTMENT_ADVICE_PATTERNS:
                if re.search(pat, text_lower):
                    flags.append("VIOLATION: Involves specific fund/stock advice (prohibited by SEBI boundary)")
                    score = 0.0
                    addressable = False
                    break

            for pat in self.FEAR_FOMO_PATTERNS:
                if re.search(pat, text_lower):
                    flags.append("VIOLATION: Involves fear, FOMO, or manipulative urgency nudges")
                    score = 0.0
                    addressable = False
                    break

        rationale = rule["rationale"]
        if flags:
            rationale += " [Blocked by ethics guardrails: " + "; ".join(flags) + "]"

        return AddressabilityResult(
            root_cause=root_cause,
            score=score,
            addressable=addressable,
            intervention_type=rule["intervention_type"],
            rationale=rationale,
            ethical_flags=flags,
        )
