"""
SIP Insight Lab — Opportunity Ranker (Task 4.6)
==============================================
Calculates the Opportunity Score for each root cause bucket using
the visible, non-black-box formula defined in the project architecture:

  Opportunity Score =
    (Frequency_Score    × 0.30)
    + (Severity_Score   × 0.25)
    + (First6mo_Conc    × 0.25)
    + (Addressability   × 0.20)

Produces a transparent, ranked priority list for product and growth decisions.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import logging

from src.synthesis.aggregator import BucketStatistics
from src.synthesis.scorers import FrequencyScorer, SeverityScorer, First6MoConcentrationScorer
from src.synthesis.addressability import AddressabilityChecker

logger = logging.getLogger("synthesis.ranker")


OPPORTUNITY_LABELS = {
    "RC-01": "Eliminate Involuntary Churn via Automated Mandate Recovery & Smart Retries",
    "RC-02": "Remove UX & Payment Friction in SIP Setup, Pause, and Cancellation Workflows",
    "RC-03": "Align Investor Expectations via Range-Based Realistic SIP Return Calculators",
    "RC-04": "Provide Emergency Liquidity Relief via Flexible SIP Pause & Step-Down Controls",
    "RC-05": "Facilitate Seamless Informed Portfolio Rebalancing & Goal Realisation",
    "RC-06": "Close Investor Knowledge Gaps on Market Volatility & Rupee-Cost Averaging",
    "RC-07": "Anchor Investors Against Social Influencer Hype through Transparent Benchmark Data",
    "RC-99": "Address Unclassifiable Feedback via Exploratory Discovery",
}

ROOT_CAUSE_NAMES = {
    "RC-01": "Involuntary Lapse",
    "RC-02": "UX & Payment Friction",
    "RC-03": "Return Disappointment",
    "RC-04": "Income Change",
    "RC-05": "Deliberate Informed Exit",
    "RC-06": "Knowledge Gap",
    "RC-07": "External Influence",
    "RC-99": "Unclassifiable",
}


@dataclass
class RankedOpportunity:
    rank: int
    root_cause: str
    root_cause_name: str
    opportunity_label: str
    count: int
    percentage_of_corpus: float
    most_affected_stage: str
    frequency_score: float
    severity_score: float
    first_6mo_concentration: float
    addressability_score: float
    opportunity_score: float
    confidence_level: str
    intervention_type: str
    rationale: str
    supporting_item_ids: List[str] = field(default_factory=list)
    supporting_quotes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "root_cause": self.root_cause,
            "root_cause_name": self.root_cause_name,
            "opportunity_label": self.opportunity_label,
            "count": self.count,
            "percentage_of_corpus": round(self.percentage_of_corpus, 2),
            "most_affected_stage": self.most_affected_stage,
            "frequency_score": round(self.frequency_score, 4),
            "severity_score": round(self.severity_score, 4),
            "first_6mo_concentration": round(self.first_6mo_concentration, 4),
            "addressability_score": round(self.addressability_score, 4),
            "opportunity_score": round(self.opportunity_score, 4),
            "confidence_level": self.confidence_level,
            "intervention_type": self.intervention_type,
            "rationale": self.rationale,
            "supporting_item_ids": self.supporting_item_ids,
            "supporting_quotes": self.supporting_quotes,
        }


class OpportunityRanker:
    """
    Ranks root cause buckets according to the opportunity score formula.
    """

    WEIGHT_FREQUENCY = 0.30
    WEIGHT_SEVERITY = 0.25
    WEIGHT_FIRST_6MO = 0.25
    WEIGHT_ADDRESSABILITY = 0.20

    def __init__(
        self,
        freq_scorer: Optional[FrequencyScorer] = None,
        sev_scorer: Optional[SeverityScorer] = None,
        conc_scorer: Optional[First6MoConcentrationScorer] = None,
        addr_checker: Optional[AddressabilityChecker] = None,
    ):
        self.freq_scorer = freq_scorer or FrequencyScorer(mode="relative_to_max")
        self.sev_scorer = sev_scorer or SeverityScorer()
        self.conc_scorer = conc_scorer or First6MoConcentrationScorer()
        self.addr_checker = addr_checker or AddressabilityChecker()

    def rank_buckets(
        self,
        buckets: Dict[str, BucketStatistics],
        total_corpus: Optional[int] = None,
    ) -> List[RankedOpportunity]:
        """
        Evaluate and rank all buckets by opportunity score.
        """
        if not buckets:
            return []

        if total_corpus is None:
            total_corpus = sum(b.count for b in buckets.values())

        max_count = max(b.count for b in buckets.values()) if buckets else 1

        unranked: List[Dict[str, Any]] = []

        for rc, b in buckets.items():
            # 1. Frequency Score [0, 1]
            f_score = self.freq_scorer.score(
                bucket_count=b.count,
                total_corpus=total_corpus,
                max_bucket_count=max_count,
            )

            # 2. Severity Score [0, 1]
            s_score = self.sev_scorer.score(b.sentiment_scores)

            # 3. First 6mo Concentration [0, 1]
            c_score = self.conc_scorer.score(
                first_6mo_count=b.first_6mo_count,
                total_bucket_count=b.count,
            )

            # 4. Addressability Score [0, 1]
            addr_res = self.addr_checker.evaluate(root_cause=rc)
            a_score = addr_res.score

            # Composite Opportunity Score
            opp_score = (
                (f_score * self.WEIGHT_FREQUENCY)
                + (s_score * self.WEIGHT_SEVERITY)
                + (c_score * self.WEIGHT_FIRST_6MO)
                + (a_score * self.WEIGHT_ADDRESSABILITY)
            )

            # Confidence Level determination
            if b.count >= 30 and f_score >= 0.2:
                conf = "High"
            elif b.count >= 10:
                conf = "Medium"
            else:
                conf = "Low"

            # Quotes & IDs
            supporting_ids = [it.item_id for it in b.sample_items[:5]]
            supporting_quotes = []
            for it in b.sample_items[:3]:
                q_text = it.cleaned_text.strip().replace("\n", " ")
                if len(q_text) > 140:
                    q_text = q_text[:137] + "..."
                supporting_quotes.append(f'"{q_text}" — (Source: {it.source}, Stage: {it.lifecycle_stage})')

            unranked.append({
                "root_cause": rc,
                "root_cause_name": ROOT_CAUSE_NAMES.get(rc, rc),
                "opportunity_label": OPPORTUNITY_LABELS.get(rc, f"Address {rc} churn factors"),
                "count": b.count,
                "percentage_of_corpus": b.percentage_of_corpus,
                "most_affected_stage": b.most_affected_stage,
                "frequency_score": f_score,
                "severity_score": s_score,
                "first_6mo_concentration": c_score,
                "addressability_score": a_score,
                "opportunity_score": opp_score,
                "confidence_level": conf,
                "intervention_type": addr_res.intervention_type,
                "rationale": addr_res.rationale,
                "supporting_item_ids": supporting_ids,
                "supporting_quotes": supporting_quotes,
            })

        # Sort descending by opportunity_score
        unranked.sort(key=lambda x: x["opportunity_score"], reverse=True)

        ranked: List[RankedOpportunity] = []
        for idx, item in enumerate(unranked, start=1):
            ranked.append(RankedOpportunity(
                rank=idx,
                root_cause=item["root_cause"],
                root_cause_name=item["root_cause_name"],
                opportunity_label=item["opportunity_label"],
                count=item["count"],
                percentage_of_corpus=item["percentage_of_corpus"],
                most_affected_stage=item["most_affected_stage"],
                frequency_score=item["frequency_score"],
                severity_score=item["severity_score"],
                first_6mo_concentration=item["first_6mo_concentration"],
                addressability_score=item["addressability_score"],
                opportunity_score=item["opportunity_score"],
                confidence_level=item["confidence_level"],
                intervention_type=item["intervention_type"],
                rationale=item["rationale"],
                supporting_item_ids=item["supporting_item_ids"],
                supporting_quotes=item["supporting_quotes"],
            ))

        return ranked

    def generate_ranking_report_markdown(
        self,
        ranked: List[RankedOpportunity],
        title: str = "SIP Insight Lab — Opportunity Ranking Report",
    ) -> str:
        """
        Generate transparent markdown table with visible formula breakdown.
        """
        lines = [
            f"# {title}",
            "",
            "## Opportunity Scoring Formula",
            "",
            "```",
            "Opportunity Score = (Frequency × 0.30) + (Severity × 0.25) + (First_6mo_Conc × 0.25) + (Addressability × 0.20)",
            "All components normalised to [0.0, 1.0].",
            "```",
            "",
            "## Ranked Priority Opportunities",
            "",
            "| Rank | Root Cause | Opportunity Focus | Items (%) | Stage Focus | Freq (30%) | Sev (25%) | 6mo (25%) | Addr (20%) | **Opp Score** | Confidence |",
            "|:---:|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
        ]

        for r in ranked:
            lines.append(
                f"| **#{r.rank}** | `{r.root_cause}` | {r.opportunity_label} | {r.count} ({r.percentage_of_corpus:.1f}%) | "
                f"`{r.most_affected_stage}` | {r.frequency_score:.2f} | {r.severity_score:.2f} | "
                f"{r.first_6mo_concentration:.2f} | {r.addressability_score:.2f} | **{r.opportunity_score:.3f}** | {r.confidence_level} |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## Detailed Opportunity Rationales",
            "",
        ])

        for r in ranked:
            lines.extend([
                f"### #{r.rank} `{r.root_cause}`: {r.opportunity_label}",
                f"- **Root Cause Category:** {r.root_cause_name} (`{r.root_cause}`)",
                f"- **Opportunity Score:** **{r.opportunity_score:.3f}** (Confidence: {r.confidence_level})",
                f"- **Volume in Corpus:** {r.count} items ({r.percentage_of_corpus:.2f}% of feedback corpus)",
                f"- **Early Churn Concentration:** {r.first_6mo_concentration * 100:.1f}% occurring in first 6 months",
                f"- **Addressability Assessment:** {r.rationale}",
                "",
                "**Representative Verbatim Quotes:**",
            ])
            for q in r.supporting_quotes:
                lines.append(f"- {q}")
            lines.append("")

        return "\n".join(lines)
