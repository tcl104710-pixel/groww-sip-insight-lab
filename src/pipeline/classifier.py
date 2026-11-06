"""
Groww SIP Insight Lab — AI-Powered Classification Engine
=========================================================
Classifies SIP-relevant feedback across key analytical dimensions using Groq LLM
(openai/gpt-oss-120b) with robust rule-based fallbacks.

Classification Dimensions:
1. user_journey_stage:
   - Onboarding & Mandate Setup
   - Active Accumulation
   - Market Downturn & Volatility
   - Decision to Pause / Modify
   - Discontinuation & Redemption
   - Post-Exit / Platform Migration
2. problem_theme:
   - Mandate / Auto-Debit Failure
   - Market Volatility Panic & Loss
   - Cash Crunch & Affordability
   - Fund Rebalancing & Strategy Shift
   - Platform Delay & Allocation Error
   - Customer Support Gap
   - Product Usability & Guidance
   - Positive / Satisfied Experience
3. sentiment: positive | neutral | negative
4. sentiment_score: float (-1.0 to 1.0)
5. user_behaviour: continuing | pausing | stopping | withdrawing | switching | seeking_guidance
6. classification_type: practical_barrier | uncertainty | informed_decision | positive_reinforcement
7. evidence_quote: Verbatim excerpt from user feedback
8. confidence_score: float (0.0 to 1.0)
9. classification_reason: Objective reason based solely on stated words without assuming negative intent.

Deliverable:
- sip_feedback_classified.csv (root, data/, outputs/)
"""

import os
import sys
import re
import json
import time
import logging
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("pipeline.classifier")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")


SYSTEM_PROMPT = """You are an objective expert financial research analyst for the Groww SIP Insight Lab.
Your job is to analyze real user feedback about Systematic Investment Plans (SIP) and mutual fund investing.

CRITICAL RULES:
1. Never invent user motivations or speculate on hidden intentions. Rely strictly on what the user states.
2. Never assume that stopping or pausing a SIP is automatically a negative outcome. An investor pausing due to emergency cash crunch, or stopping an active fund to switch to a direct index fund, or redeeming after reaching a goal, is an informed financial decision.
3. Extract an exact verbatim quote from the text as evidence.

For each feedback text, produce a JSON object with EXACTLY these fields:
- user_journey_stage: One of ["Onboarding & Mandate Setup", "Active Accumulation", "Market Downturn & Volatility", "Decision to Pause / Modify", "Discontinuation & Redemption", "Post-Exit / Platform Migration"]
- problem_theme: One of ["Mandate / Auto-Debit Failure", "Market Volatility Panic & Loss", "Cash Crunch & Affordability", "Fund Rebalancing & Strategy Shift", "Platform Delay & Allocation Error", "Customer Support Gap", "Product Usability & Guidance", "Positive / Satisfied Experience"]
- sentiment: One of ["positive", "neutral", "negative"]
- sentiment_score: float from -1.0 to 1.0
- user_behaviour: One of ["continuing", "pausing", "stopping", "withdrawing", "switching", "seeking_guidance"]
- classification_type: One of ["practical_barrier", "uncertainty", "informed_decision", "positive_reinforcement"]
- evidence_quote: Exact short substring from the text supporting your classification
- confidence_score: float from 0.0 to 1.0
- classification_reason: Brief 1-2 sentence explanation based on the user's explicit words.

Output ONLY the JSON object.
"""


def rule_based_fallback(text: str, rating=None) -> dict:
    """
    Deterministic fallback classification engine matching exact linguistic signals.
    Ensures 100% coverage even when rate limits or offline conditions occur.
    """
    text_lower = text.lower()

    # Default values
    stage = "Active Accumulation"
    theme = "Positive / Satisfied Experience"
    sentiment = "neutral"
    sentiment_score = 0.0
    behaviour = "continuing"
    class_type = "informed_decision"
    confidence = 0.85
    reason = "User discusses general SIP investment experience."

    # Substring search for quote extraction
    sentences = re.split(r"[.!?\n]+", text.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 8]
    evidence_quote = sentences[0] if sentences else text[:80]

    # Mandate / Payment failure
    if any(k in text_lower for k in ["mandate", "auto-debit", "autodebit", "autopay", "auto pay", "enach", "nach", "debit failed", "deducted but not", "bounce charge", "bank charge"]):
        stage = "Onboarding & Mandate Setup" if "setup" in text_lower or "create" in text_lower or "bank" in text_lower else "Active Accumulation"
        theme = "Mandate / Auto-Debit Failure"
        sentiment = "negative"
        sentiment_score = -0.75
        behaviour = "pausing" if "pause" in text_lower else ("stopping" if "cancel" in text_lower else "continuing")
        class_type = "practical_barrier"
        reason = "User reports operational friction with bank mandate or auto-debit failure."
        for s in sentences:
            if any(k in s.lower() for k in ["mandate", "debit", "failed", "deducted", "bounce", "charge"]):
                evidence_quote = s
                break

    # Volatility / Market panic / Negative returns
    elif any(k in text_lower for k in ["loss", "losses", "in the red", "market down", "crash", "negative return", "falling", "dip", "underperform"]):
        stage = "Market Downturn & Volatility"
        theme = "Market Volatility Panic & Loss"
        sentiment = "negative"
        sentiment_score = -0.60
        behaviour = "seeking_guidance" if "?" in text or "should i" in text_lower or "advice" in text_lower else ("stopping" if "stop" in text_lower else "continuing")
        class_type = "uncertainty"
        reason = "User expresses anxiety or uncertainty regarding market fluctuations and negative returns."
        for s in sentences:
            if any(k in s.lower() for k in ["loss", "down", "crash", "negative", "fall", "red"]):
                evidence_quote = s
                break

    # Affordability / Cash crunch
    elif any(k in text_lower for k in ["afford", "salary", "cash crunch", "emergency", "no money", "job loss", "tight budget", "financial constraint"]):
        stage = "Decision to Pause / Modify"
        theme = "Cash Crunch & Affordability"
        sentiment = "neutral" if "pause" in text_lower else "negative"
        sentiment_score = -0.40
        behaviour = "pausing" if "pause" in text_lower else "stopping"
        class_type = "practical_barrier"
        reason = "User faces financial or cash flow constraints impacting monthly SIP commitments."
        for s in sentences:
            if any(k in s.lower() for k in ["afford", "salary", "money", "budget", "emergency", "pause"]):
                evidence_quote = s
                break

    # Rebalancing / Strategy shift
    elif any(k in text_lower for k in ["switch", "index fund", "direct plan", "ter", "expense ratio", "rebalance", "portfolio review", "overlap"]):
        stage = "Decision to Pause / Modify" if "pause" in text_lower else "Discontinuation & Redemption"
        theme = "Fund Rebalancing & Strategy Shift"
        sentiment = "neutral"
        sentiment_score = 0.10
        behaviour = "switching" if "switch" in text_lower else "stopping"
        class_type = "informed_decision"
        reason = "User deliberately adjusts or reallocates investments based on portfolio analysis."
        for s in sentences:
            if any(k in s.lower() for k in ["switch", "index", "direct", "expense", "rebalance"]):
                evidence_quote = s
                break

    # Platform delay / NAV allocation
    elif any(k in text_lower for k in ["nav delay", "unit not allocated", "allocation", "units delayed", "wrong nav", "statement mismatch", "cams"]):
        stage = "Active Accumulation"
        theme = "Platform Delay & Allocation Error"
        sentiment = "negative"
        sentiment_score = -0.65
        behaviour = "continuing"
        class_type = "practical_barrier"
        reason = "User reports platform delay in NAV allotment or unit credit."
        for s in sentences:
            if any(k in s.lower() for k in ["nav", "unit", "allocat", "delay"]):
                evidence_quote = s
                break

    # Customer support gap
    elif any(k in text_lower for k in ["customer care", "customer support", "ticket", "helpdesk", "no response", "helpless", "worst support"]):
        stage = "Active Accumulation"
        theme = "Customer Support Gap"
        sentiment = "negative"
        sentiment_score = -0.85
        behaviour = "seeking_guidance" if "help" in text_lower else "stopping"
        class_type = "practical_barrier"
        reason = "User expresses dissatisfaction with customer support responsiveness."
        for s in sentences:
            if any(k in s.lower() for k in ["support", "ticket", "care", "response"]):
                evidence_quote = s
                break

    # Discontinuation / Exit
    elif any(k in text_lower for k in ["stopped sip", "cancel sip", "cancelled sip", "close sip", "redeem all", "exit load"]):
        stage = "Discontinuation & Redemption"
        theme = "Product Usability & Guidance" if "hard to cancel" in text_lower or "where is" in text_lower else "Fund Rebalancing & Strategy Shift"
        sentiment = "negative" if rating and rating <= 2 else "neutral"
        sentiment_score = -0.30
        behaviour = "stopping"
        class_type = "informed_decision" if "goal" in text_lower or "profit" in text_lower else "practical_barrier"
        reason = "User explicitly mentions stopping or cancelling SIP installments."
        for s in sentences:
            if any(k in s.lower() for k in ["stop", "cancel", "redeem", "close"]):
                evidence_quote = s
                break

    # Positive experience
    elif any(k in text_lower for k in ["good app", "great app", "smooth", "best for sip", "easy to use", "simple ui", "love groww", "excellent"]):
        stage = "Active Accumulation"
        theme = "Positive / Satisfied Experience"
        sentiment = "positive"
        sentiment_score = 0.85
        behaviour = "continuing"
        class_type = "positive_reinforcement"
        reason = "User highlights positive, seamless SIP investing experience."
        for s in sentences:
            if any(k in s.lower() for k in ["good", "great", "best", "easy", "smooth", "love"]):
                evidence_quote = s
                break

    # Rating adjustments
    if rating:
        if rating <= 2 and sentiment == "positive":
            sentiment = "negative"
            sentiment_score = -0.5
        elif rating >= 4 and sentiment == "negative" and theme == "Positive / Satisfied Experience":
            sentiment = "positive"
            sentiment_score = 0.7

    return {
        "user_journey_stage": stage,
        "problem_theme": theme,
        "sentiment": sentiment,
        "sentiment_score": sentiment_score,
        "user_behaviour": behaviour,
        "classification_type": class_type,
        "evidence_quote": evidence_quote[:150],
        "confidence_score": confidence,
        "classification_reason": reason,
    }


def classify_record_with_llm(client, text: str, rating=None) -> dict:
    """Invokes Groq LLM for nuanced classification with structured output."""
    if not client:
        return rule_based_fallback(text, rating)

    prompt = f"User Feedback Text:\n\"\"\"{text[:1000]}\"\"\"\nUser Rating (if available): {rating}\n\nClassify this feedback as JSON."
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=600,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        data = json.loads(content)

        # Validate required fields
        required_fields = [
            "user_journey_stage", "problem_theme", "sentiment", "sentiment_score",
            "user_behaviour", "classification_type", "evidence_quote", "confidence_score", "classification_reason"
        ]
        if all(k in data for k in required_fields):
            return data
        else:
            fb = rule_based_fallback(text, rating)
            fb.update({k: v for k, v in data.items() if k in required_fields})
            return fb
    except Exception as e:
        logger.warning("Groq API error on item: %s. Using robust fallback.", e)
        return rule_based_fallback(text, rating)


def classify_feedback_dataset(df_relevant: pd.DataFrame = None, sample_llm_limit: int = 15) -> pd.DataFrame:
    """
    Classifies all relevant records. Runs Groq LLM on a representative sample
    and robust deterministic classification on the rest to respect rate limits.
    """
    if df_relevant is None:
        rel_path = PROJECT_ROOT / "sip_feedback_relevant.csv"
        if not rel_path.exists():
            rel_path = DATA_DIR / "sip_feedback_relevant.csv"
        if not rel_path.exists():
            raise FileNotFoundError(f"Relevant feedback file not found at {rel_path}")
        df_relevant = pd.read_csv(rel_path, encoding="utf-8")

    logger.info("Classifying %d relevant feedback records ...", len(df_relevant))

    # Initialize Groq client if key is available
    groq_client = None
    if GROQ_API_KEY and not GROQ_API_KEY.startswith("your_"):
        try:
            from groq import Groq
            groq_client = Groq(api_key=GROQ_API_KEY, max_retries=1)
            logger.info("Groq client initialized with model %s.", GROQ_MODEL)
        except Exception as e:
            logger.warning("Failed to initialize Groq client: %s", e)

    results = []
    total = len(df_relevant)

    for i, (_, row) in enumerate(df_relevant.iterrows()):
        text = str(row.get("cleaned_text") or row.get("raw_text") or "")
        rating = row.get("rating")

        # Use LLM for first 15 representative items, fast robust rule engine for remainder
        use_llm = groq_client is not None and (i < sample_llm_limit)

        if use_llm:
            cls_dict = classify_record_with_llm(groq_client, text, rating)
            time.sleep(1.2)  # respectful delay to stay comfortably within TPM limits
        else:
            cls_dict = rule_based_fallback(text, rating)

        # Merge with original row data
        merged = row.to_dict()
        merged.update(cls_dict)
        results.append(merged)

        if (i + 1) % 50 == 0 or (i + 1) == total:
            logger.info("Classified %d / %d records (%.1f%%)", i + 1, total, (i + 1) / total * 100)

    df_classified = pd.DataFrame(results)

    # Save to all target locations
    root_path = PROJECT_ROOT / "sip_feedback_classified.csv"
    data_path = DATA_DIR / "sip_feedback_classified.csv"
    outputs_path = OUTPUTS_DIR / "sip_feedback_classified.csv"

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    df_classified.to_csv(root_path, index=False, encoding="utf-8")
    df_classified.to_csv(data_path, index=False, encoding="utf-8")
    df_classified.to_csv(outputs_path, index=False, encoding="utf-8")

    logger.info("Saved %d classified records to %s, %s, and %s", len(df_classified), root_path, data_path, outputs_path)
    return df_classified


if __name__ == "__main__":
    df_cls = classify_feedback_dataset()
    print(f"Classification Complete: {len(df_cls)} records.")
    print("Theme Breakdown:\n", df_cls["problem_theme"].value_counts())
    print("Classification Type Breakdown:\n", df_cls["classification_type"].value_counts())
