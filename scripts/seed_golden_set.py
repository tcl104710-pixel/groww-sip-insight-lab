"""
SIP Insight Lab — Golden Set Builder and Seeder (Tasks 3.1 & 3.2)
=================================================================
Constructs the hand-labelled golden set (≥20 items) spanning all
root causes and lifecycle stages. Simulates two independent human
labellers (PM and Senior Researcher) and generates reconciled ground truth.

Outputs:
  - golden_set/items.csv
  - golden_set/labels.csv
  - Populates golden_set, raw_item, cleaned_item tables in sip_insight_lab.db

Usage:
    python scripts/seed_golden_set.py
"""

import csv
import json
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.db.schema import init_db
from src.ingestion.dedup import compute_hash

# 25 hand-curated items with dual-annotator and reconciled labels
GOLDEN_SET_DATA = [
    {
        "item_id": "gs_item_001",
        "source": "play_store",
        "source_id": "rev_play_001",
        "star_rating": 1,
        "text": "My SIP got cancelled automatically after 3 failed debits because SBI server was down. Groww should have notified me before cancelling!",
        "l1": {"root_cause": "RC-01", "stop_type": "ST-01", "lifecycle_stage": "LS-01", "stated_intent": "continue", "actual_action": "cancelled", "retention_factor": None},
        "l2": {"root_cause": "RC-01", "stop_type": "ST-01", "lifecycle_stage": "LS-01", "stated_intent": "unknown", "actual_action": "cancelled", "retention_factor": None},
        "reconciled": {
            "root_cause": "RC-01",
            "root_cause_sub": "Auto-cancellation after 3 misses",
            "stop_type": "ST-01",
            "lifecycle_stage": "LS-01",
            "stated_intent": "unknown",
            "actual_action": "cancelled",
            "trigger_moment": "SBI server down causing 3 missed debits",
            "help_sources": ["none_mentioned"],
            "retention_factor": None,
            "sentiment_score": -0.80,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "Agreed on RC-01 and ST-01; resolved stated_intent to unknown as user did not explicitly declare future action.",
    },
    {
        "item_id": "gs_item_002",
        "source": "app_store",
        "source_id": "rev_app_002",
        "star_rating": 1,
        "text": "e-Mandate rejected for ICICI bank account and SIP was cancelled. Customer support took 5 days to respond.",
        "l1": {"root_cause": "RC-01", "stop_type": "ST-01", "lifecycle_stage": "LS-01", "stated_intent": "unknown", "actual_action": "cancelled", "retention_factor": None},
        "l2": {"root_cause": "RC-02", "stop_type": "ST-01", "lifecycle_stage": "LS-01", "stated_intent": "unknown", "actual_action": "cancelled", "retention_factor": None},
        "reconciled": {
            "root_cause": "RC-01",
            "root_cause_sub": "Bank mandate failure",
            "stop_type": "ST-01",
            "lifecycle_stage": "LS-01",
            "stated_intent": "unknown",
            "actual_action": "cancelled",
            "trigger_moment": "e-Mandate rejected for ICICI bank",
            "help_sources": ["groww_customer_support"],
            "retention_factor": None,
            "sentiment_score": -0.85,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "L2 flagged customer support delay (RC-02), but primary root cause of SIP cancellation was e-Mandate failure (RC-01).",
    },
    {
        "item_id": "gs_item_003",
        "source": "reddit",
        "source_id": "post_red_003",
        "star_rating": None,
        "text": "Forgot to maintain minimum balance in bank account on the 5th. Missed 2 debits and now my SIP is stopped.",
        "l1": {"root_cause": "RC-01", "stop_type": "ST-01", "lifecycle_stage": "LS-01", "stated_intent": "unknown", "actual_action": "cancelled", "retention_factor": None},
        "l2": {"root_cause": "RC-01", "stop_type": "ST-01", "lifecycle_stage": "LS-01", "stated_intent": "unknown", "actual_action": "cancelled", "retention_factor": None},
        "reconciled": {
            "root_cause": "RC-01",
            "root_cause_sub": "Insufficient balance",
            "stop_type": "ST-01",
            "lifecycle_stage": "LS-01",
            "stated_intent": "unknown",
            "actual_action": "cancelled",
            "trigger_moment": "Insufficient balance on debit date",
            "help_sources": ["reddit"],
            "retention_factor": None,
            "sentiment_score": -0.50,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "Consensus on RC-01 Insufficient balance.",
    },
    {
        "item_id": "gs_item_004",
        "source": "tradingqa",
        "source_id": "tqa_004",
        "star_rating": None,
        "text": "NACH mandate expired after 1 year without any email alert. Unable to resume the same folio.",
        "l1": {"root_cause": "RC-01", "stop_type": "ST-01", "lifecycle_stage": "LS-04", "stated_intent": "continue", "actual_action": "cancelled", "retention_factor": None},
        "l2": {"root_cause": "RC-01", "stop_type": "ST-01", "lifecycle_stage": "LS-04", "stated_intent": "continue", "actual_action": "cancelled", "retention_factor": None},
        "reconciled": {
            "root_cause": "RC-01",
            "root_cause_sub": "Bank mandate failure",
            "stop_type": "ST-01",
            "lifecycle_stage": "LS-04",
            "stated_intent": "continue",
            "actual_action": "cancelled",
            "trigger_moment": "NACH mandate expired after 1 year",
            "help_sources": ["tradingqa"],
            "retention_factor": None,
            "sentiment_score": -0.60,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "Consensus reached. User wants to continue but SIP involuntarily cancelled due to expired NACH mandate.",
    },
    {
        "item_id": "gs_item_005",
        "source": "play_store",
        "source_id": "rev_play_005",
        "star_rating": 1,
        "text": "App update made SIP modification impossible. Tried pausing for a month but the toggle throws network error.",
        "l1": {"root_cause": "RC-02", "stop_type": "ST-02", "lifecycle_stage": "LS-02", "stated_intent": "pause", "actual_action": "active", "retention_factor": None},
        "l2": {"root_cause": "RC-02", "stop_type": "ST-02", "lifecycle_stage": "LS-02", "stated_intent": "pause", "actual_action": "active", "retention_factor": None},
        "reconciled": {
            "root_cause": "RC-02",
            "root_cause_sub": "Difficult SIP modification flow",
            "stop_type": "ST-02",
            "lifecycle_stage": "LS-02",
            "stated_intent": "pause",
            "actual_action": "active",
            "trigger_moment": "Toggle throws network error on pause",
            "help_sources": ["none_mentioned"],
            "retention_factor": None,
            "sentiment_score": -0.75,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "Consensus on RC-02 UX friction; stated intent is pause but actual action remains active due to UI error.",
    },
    {
        "item_id": "gs_item_006",
        "source": "app_store",
        "source_id": "rev_app_006",
        "star_rating": 2,
        "text": "Payment gateway failed twice during SIP instalment debit. Money debited from bank but units not allotted.",
        "l1": {"root_cause": "RC-02", "stop_type": "ST-03", "lifecycle_stage": "LS-01", "stated_intent": "neutral", "actual_action": "active", "retention_factor": None},
        "l2": {"root_cause": "RC-01", "stop_type": "ST-01", "lifecycle_stage": "LS-01", "stated_intent": "neutral", "actual_action": "active", "retention_factor": None},
        "reconciled": {
            "root_cause": "RC-02",
            "root_cause_sub": "Payment gateway failure",
            "stop_type": "ST-03",
            "lifecycle_stage": "LS-01",
            "stated_intent": "neutral",
            "actual_action": "active",
            "trigger_moment": "Payment gateway drop during debit",
            "help_sources": ["none_mentioned"],
            "retention_factor": None,
            "sentiment_score": -0.70,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "Resolved to RC-02 (Payment gateway failure). User has not cancelled SIP so stop_type is ST-03 (not_applicable).",
    },
    {
        "item_id": "gs_item_007",
        "source": "reddit",
        "source_id": "post_red_007",
        "star_rating": None,
        "text": "KYC rejected 3 times for signature mismatch. Unable to complete first SIP debit.",
        "l1": {"root_cause": "RC-02", "stop_type": "ST-01", "lifecycle_stage": "LS-00", "stated_intent": "continue", "actual_action": "unknown", "retention_factor": None},
        "l2": {"root_cause": "RC-02", "stop_type": "ST-01", "lifecycle_stage": "LS-00", "stated_intent": "continue", "actual_action": "unknown", "retention_factor": None},
        "reconciled": {
            "root_cause": "RC-02",
            "root_cause_sub": "KYC / documentation issues",
            "stop_type": "ST-01",
            "lifecycle_stage": "LS-00",
            "stated_intent": "continue",
            "actual_action": "unknown",
            "trigger_moment": "KYC signature mismatch rejection",
            "help_sources": ["reddit"],
            "retention_factor": None,
            "sentiment_score": -0.65,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "Consensus on pre-first SIP stage (LS-00) blocked by KYC.",
    },
    {
        "item_id": "gs_item_008",
        "source": "reddit",
        "source_id": "post_red_008",
        "star_rating": None,
        "text": "Invested in midcap fund for 5 months. Calculator promised 15% return but portfolio is down 4%. Stopping my SIP.",
        "l1": {"root_cause": "RC-03", "stop_type": "ST-02", "lifecycle_stage": "LS-02", "stated_intent": "stop", "actual_action": "cancelled", "retention_factor": None},
        "l2": {"root_cause": "RC-03", "stop_type": "ST-02", "lifecycle_stage": "LS-02", "stated_intent": "stop", "actual_action": "cancelled", "retention_factor": None},
        "reconciled": {
            "root_cause": "RC-03",
            "root_cause_sub": "Calculator mismatch",
            "stop_type": "ST-02",
            "lifecycle_stage": "LS-02",
            "stated_intent": "stop",
            "actual_action": "cancelled",
            "trigger_moment": "Portfolio down 4% after 5 months vs 15% calculator promise",
            "help_sources": ["reddit"],
            "retention_factor": None,
            "sentiment_score": -0.85,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "Unanimous agreement: RC-03 (Calculator mismatch) in 3-6mo window (LS-02).",
    },
    {
        "item_id": "gs_item_009",
        "source": "play_store",
        "source_id": "rev_play_009",
        "star_rating": 1,
        "text": "YouTube finfluencer recommended this flexi cap fund claiming 20% guaranteed returns. Complete scam I am in loss.",
        "l1": {"root_cause": "RC-03", "stop_type": "ST-02", "lifecycle_stage": "LS-01", "stated_intent": "stop", "actual_action": "active", "retention_factor": None},
        "l2": {"root_cause": "RC-07", "stop_type": "ST-02", "lifecycle_stage": "LS-01", "stated_intent": "stop", "actual_action": "active", "retention_factor": None},
        "reconciled": {
            "root_cause": "RC-03",
            "root_cause_sub": "Finfluencer promise gap",
            "stop_type": "ST-02",
            "lifecycle_stage": "LS-01",
            "stated_intent": "stop",
            "actual_action": "active",
            "trigger_moment": "Unrealistic return gap from YouTube influencer recommendation",
            "help_sources": ["youtube"],
            "retention_factor": None,
            "sentiment_score": -0.90,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "Reconciled to RC-03 with subcategory 'Finfluencer promise gap'.",
    },
    {
        "item_id": "gs_item_010",
        "source": "tradingqa",
        "source_id": "tqa_010",
        "star_rating": None,
        "text": "Nifty dropped 600 points last week and my fund NAV fell. Scared of losing more capital so I stopped the SIP.",
        "l1": {"root_cause": "RC-03", "stop_type": "ST-02", "lifecycle_stage": "LS-01", "stated_intent": "stop", "actual_action": "cancelled", "retention_factor": None},
        "l2": {"root_cause": "RC-03", "stop_type": "ST-02", "lifecycle_stage": "LS-01", "stated_intent": "stop", "actual_action": "cancelled", "retention_factor": None},
        "reconciled": {
            "root_cause": "RC-03",
            "root_cause_sub": "Market downturn fear",
            "stop_type": "ST-02",
            "lifecycle_stage": "LS-01",
            "stated_intent": "stop",
            "actual_action": "cancelled",
            "trigger_moment": "Nifty 600 pt market drop",
            "help_sources": ["tradingqa"],
            "retention_factor": None,
            "sentiment_score": -0.75,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "Consensus: deliberate stop driven by panic/market correction (RC-03 Market downturn fear).",
    },
    {
        "item_id": "gs_item_011",
        "source": "reddit",
        "source_id": "post_red_011",
        "star_rating": None,
        "text": "Expecting 12% in 3 months was my mistake, but returns are too low compared to FD right now. Exiting.",
        "l1": {"root_cause": "RC-03", "stop_type": "ST-02", "lifecycle_stage": "LS-01", "stated_intent": "stop", "actual_action": "cancelled", "retention_factor": None},
        "l2": {"root_cause": "RC-03", "stop_type": "ST-02", "lifecycle_stage": "LS-01", "stated_intent": "stop", "actual_action": "cancelled", "retention_factor": None},
        "reconciled": {
            "root_cause": "RC-03",
            "root_cause_sub": "Short-term return focus",
            "stop_type": "ST-02",
            "lifecycle_stage": "LS-01",
            "stated_intent": "stop",
            "actual_action": "cancelled",
            "trigger_moment": "3-month returns lower than fixed deposit",
            "help_sources": ["reddit"],
            "retention_factor": None,
            "sentiment_score": -0.60,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "Consensus on RC-03 Short-term return focus.",
    },
    {
        "item_id": "gs_item_012",
        "source": "reddit",
        "source_id": "post_red_012",
        "star_rating": None,
        "text": "Laid off from tech company last week. Pausing my 20k SIP until I secure another job.",
        "l1": {"root_cause": "RC-04", "stop_type": "ST-02", "lifecycle_stage": "LS-03", "stated_intent": "continue", "actual_action": "paused", "retention_factor": None},
        "l2": {"root_cause": "RC-04", "stop_type": "ST-02", "lifecycle_stage": "LS-03", "stated_intent": "pause", "actual_action": "paused", "retention_factor": None},
        "reconciled": {
            "root_cause": "RC-04",
            "root_cause_sub": "Job loss",
            "stop_type": "ST-02",
            "lifecycle_stage": "LS-03",
            "stated_intent": "continue",
            "actual_action": "paused",
            "trigger_moment": "Layoff from tech company",
            "help_sources": ["reddit"],
            "retention_factor": None,
            "sentiment_score": -0.40,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "L1 noted user states intention to restart ('until I secure another job') -> stated_intent=continue, actual_action=paused.",
    },
    {
        "item_id": "gs_item_013",
        "source": "play_store",
        "source_id": "rev_play_013",
        "star_rating": 3,
        "text": "Family medical emergency forced me to cancel my monthly SIP and redeem accumulated units.",
        "l1": {"root_cause": "RC-04", "stop_type": "ST-02", "lifecycle_stage": "LS-02", "stated_intent": "stop", "actual_action": "cancelled", "retention_factor": None},
        "l2": {"root_cause": "RC-04", "stop_type": "ST-02", "lifecycle_stage": "LS-02", "stated_intent": "stop", "actual_action": "cancelled", "retention_factor": None},
        "reconciled": {
            "root_cause": "RC-04",
            "root_cause_sub": "Emergency expense",
            "stop_type": "ST-02",
            "lifecycle_stage": "LS-02",
            "stated_intent": "stop",
            "actual_action": "cancelled",
            "trigger_moment": "Family medical emergency",
            "help_sources": ["none_mentioned"],
            "retention_factor": None,
            "sentiment_score": -0.30,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "Consensus on RC-04 Emergency expense.",
    },
    {
        "item_id": "gs_item_014",
        "source": "tradingqa",
        "source_id": "tqa_014",
        "star_rating": None,
        "text": "Salary reduced by 25% due to company restructuring. Need to cut discretionary investment outflow.",
        "l1": {"root_cause": "RC-04", "stop_type": "ST-02", "lifecycle_stage": "LS-99", "stated_intent": "stop", "actual_action": "cancelled", "retention_factor": None},
        "l2": {"root_cause": "RC-04", "stop_type": "ST-02", "lifecycle_stage": "LS-99", "stated_intent": "stop", "actual_action": "cancelled", "retention_factor": None},
        "reconciled": {
            "root_cause": "RC-04",
            "root_cause_sub": "Salary reduction",
            "stop_type": "ST-02",
            "lifecycle_stage": "LS-99",
            "stated_intent": "stop",
            "actual_action": "cancelled",
            "trigger_moment": "25% salary cut",
            "help_sources": ["tradingqa"],
            "retention_factor": None,
            "sentiment_score": -0.50,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "Consensus on RC-04 Salary reduction.",
    },
    {
        "item_id": "gs_item_015",
        "source": "reddit",
        "source_id": "post_red_015",
        "star_rating": None,
        "text": "Completed 3 years of SIP and reached my target 5 lakh downpayment for a car. Cancelled SIP to book profits.",
        "l1": {"root_cause": "RC-05", "stop_type": "ST-02", "lifecycle_stage": "LS-04", "stated_intent": "stop", "actual_action": "cancelled", "retention_factor": None},
        "l2": {"root_cause": "RC-05", "stop_type": "ST-02", "lifecycle_stage": "LS-04", "stated_intent": "stop", "actual_action": "cancelled", "retention_factor": None},
        "reconciled": {
            "root_cause": "RC-05",
            "root_cause_sub": "Goal achieved",
            "stop_type": "ST-02",
            "lifecycle_stage": "LS-04",
            "stated_intent": "stop",
            "actual_action": "cancelled",
            "trigger_moment": "Reached 5 lakh car downpayment goal",
            "help_sources": ["reddit"],
            "retention_factor": None,
            "sentiment_score": 0.80,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "Healthy positive exit (RC-05 Goal achieved). Unanimous.",
    },
    {
        "item_id": "gs_item_016",
        "source": "tradingqa",
        "source_id": "tqa_016",
        "star_rating": None,
        "text": "Switching from active large cap fund to Nifty 50 direct index fund on the same Groww app. Stopped the active fund SIP.",
        "l1": {"root_cause": "RC-05", "stop_type": "ST-02", "lifecycle_stage": "LS-03", "stated_intent": "continue", "actual_action": "cancelled", "retention_factor": None},
        "l2": {"root_cause": "RC-05", "stop_type": "ST-02", "lifecycle_stage": "LS-03", "stated_intent": "continue", "actual_action": "cancelled", "retention_factor": None},
        "reconciled": {
            "root_cause": "RC-05",
            "root_cause_sub": "Fund switch (same platform)",
            "stop_type": "ST-02",
            "lifecycle_stage": "LS-03",
            "stated_intent": "continue",
            "actual_action": "cancelled",
            "trigger_moment": "Decision to switch to lower cost index fund",
            "help_sources": ["tradingqa"],
            "retention_factor": None,
            "sentiment_score": 0.50,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "Consensus on RC-05 Fund switch. User cancelled specific active SIP but stated intent is to continue investing in index fund.",
    },
    {
        "item_id": "gs_item_017",
        "source": "play_store",
        "source_id": "rev_play_017",
        "star_rating": 1,
        "text": "Why was money deducted on Sunday when stock market is closed? Groww stole my money, lodge police complaint!",
        "l1": {"root_cause": "RC-06", "stop_type": "ST-03", "lifecycle_stage": "LS-01", "stated_intent": "unknown", "actual_action": "active", "retention_factor": None},
        "l2": {"root_cause": "RC-06", "stop_type": "ST-03", "lifecycle_stage": "LS-01", "stated_intent": "stop", "actual_action": "active", "retention_factor": None},
        "reconciled": {
            "root_cause": "RC-06",
            "root_cause_sub": "Did not understand SIP mechanics",
            "stop_type": "ST-03",
            "lifecycle_stage": "LS-01",
            "stated_intent": "unknown",
            "actual_action": "active",
            "trigger_moment": "Bank debit occurring on weekend",
            "help_sources": ["none_mentioned"],
            "retention_factor": None,
            "sentiment_score": -0.90,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "Consensus on RC-06 Knowledge gap regarding banking NACH vs exchange trading days.",
    },
    {
        "item_id": "gs_item_018",
        "source": "youtube",
        "source_id": "yt_018",
        "star_rating": None,
        "text": "I am confused about NAV. If NAV increases does my profit decrease? Nobody explains clearly.",
        "l1": {"root_cause": "RC-06", "stop_type": "ST-03", "lifecycle_stage": "LS-01", "stated_intent": "neutral", "actual_action": "active", "retention_factor": None},
        "l2": {"root_cause": "RC-06", "stop_type": "ST-03", "lifecycle_stage": "LS-01", "stated_intent": "neutral", "actual_action": "active", "retention_factor": None},
        "reconciled": {
            "root_cause": "RC-06",
            "root_cause_sub": "Confused about NAV calculation",
            "stop_type": "ST-03",
            "lifecycle_stage": "LS-01",
            "stated_intent": "neutral",
            "actual_action": "active",
            "trigger_moment": "Confusion regarding NAV calculation",
            "help_sources": ["youtube"],
            "retention_factor": None,
            "sentiment_score": -0.40,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "Consensus on RC-06 Confused about NAV.",
    },
    {
        "item_id": "gs_item_019",
        "source": "reddit",
        "source_id": "post_red_019",
        "star_rating": None,
        "text": "Did not realize market fluctuation causes NAV to go down temporarily. Thought mutual funds only go up.",
        "l1": {"root_cause": "RC-06", "stop_type": "ST-03", "lifecycle_stage": "LS-01", "stated_intent": "neutral", "actual_action": "active", "retention_factor": None},
        "l2": {"root_cause": "RC-06", "stop_type": "ST-03", "lifecycle_stage": "LS-01", "stated_intent": "neutral", "actual_action": "active", "retention_factor": None},
        "reconciled": {
            "root_cause": "RC-06",
            "root_cause_sub": "Did not understand market volatility is normal",
            "stop_type": "ST-03",
            "lifecycle_stage": "LS-01",
            "stated_intent": "neutral",
            "actual_action": "active",
            "trigger_moment": "First encounter with portfolio NAV drawdown",
            "help_sources": ["reddit"],
            "retention_factor": None,
            "sentiment_score": -0.45,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "Consensus on RC-06 Volatility misunderstanding.",
    },
    {
        "item_id": "gs_item_020",
        "source": "reddit",
        "source_id": "post_red_020",
        "star_rating": None,
        "text": "Colleague convinced me that mutual funds are crashing and urged me to withdraw everything and buy gold coins.",
        "l1": {"root_cause": "RC-07", "stop_type": "ST-02", "lifecycle_stage": "LS-02", "stated_intent": "stop", "actual_action": "active", "retention_factor": None},
        "l2": {"root_cause": "RC-07", "stop_type": "ST-02", "lifecycle_stage": "LS-02", "stated_intent": "stop", "actual_action": "active", "retention_factor": None},
        "reconciled": {
            "root_cause": "RC-07",
            "root_cause_sub": "Peer advice (negative / stop advice)",
            "stop_type": "ST-02",
            "lifecycle_stage": "LS-02",
            "stated_intent": "stop",
            "actual_action": "active",
            "trigger_moment": "Colleague advice to exit for gold",
            "help_sources": ["peer_friend", "reddit"],
            "retention_factor": None,
            "sentiment_score": -0.50,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "Consensus on RC-07 Peer advice.",
    },
    {
        "item_id": "gs_item_021",
        "source": "youtube",
        "source_id": "yt_021",
        "star_rating": None,
        "text": "Finfluencer said small caps are overheated and advised shifting to debt funds. Cancelled my Nippon small cap SIP.",
        "l1": {"root_cause": "RC-07", "stop_type": "ST-02", "lifecycle_stage": "LS-02", "stated_intent": "stop", "actual_action": "cancelled", "retention_factor": None},
        "l2": {"root_cause": "RC-07", "stop_type": "ST-02", "lifecycle_stage": "LS-02", "stated_intent": "stop", "actual_action": "cancelled", "retention_factor": None},
        "reconciled": {
            "root_cause": "RC-07",
            "root_cause_sub": "Finfluencer recommendation (negative / switch advice)",
            "stop_type": "ST-02",
            "lifecycle_stage": "LS-02",
            "stated_intent": "stop",
            "actual_action": "cancelled",
            "trigger_moment": "YouTube finfluencer smallcap exit call",
            "help_sources": ["youtube"],
            "retention_factor": None,
            "sentiment_score": -0.30,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "Consensus on RC-07 Finfluencer advice resulting in SIP stop.",
    },
    {
        "item_id": "gs_item_022",
        "source": "reddit",
        "source_id": "post_red_022",
        "star_rating": None,
        "text": "Investing in Parag Parikh Flexi Cap for 18 months. Rupee cost averaging is working wonders during market corrections. Continuing every month!",
        "l1": {"root_cause": "RC-99", "stop_type": "ST-03", "lifecycle_stage": "LS-04", "stated_intent": "continue", "actual_action": "active", "retention_factor": "RF-07"},
        "l2": {"root_cause": "RC-99", "stop_type": "ST-03", "lifecycle_stage": "LS-04", "stated_intent": "continue", "actual_action": "active", "retention_factor": "RF-07"},
        "reconciled": {
            "root_cause": "RC-99",
            "root_cause_sub": None,
            "stop_type": "ST-03",
            "lifecycle_stage": "LS-04",
            "stated_intent": "continue",
            "actual_action": "active",
            "trigger_moment": "Market corrections validated DCA strategy",
            "help_sources": ["reddit"],
            "retention_factor": "RF-07",
            "sentiment_score": 0.85,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "Retained investor: RF-07 (Rupee cost averaging understanding).",
    },
    {
        "item_id": "gs_item_023",
        "source": "play_store",
        "source_id": "rev_play_023",
        "star_rating": 5,
        "text": "Auto debit on 1st of every month without fail. Set it and forget it. Excellent disciplined investing experience.",
        "l1": {"root_cause": "RC-99", "stop_type": "ST-03", "lifecycle_stage": "LS-03", "stated_intent": "continue", "actual_action": "active", "retention_factor": "RF-06"},
        "l2": {"root_cause": "RC-99", "stop_type": "ST-03", "lifecycle_stage": "LS-03", "stated_intent": "continue", "actual_action": "active", "retention_factor": "RF-06"},
        "reconciled": {
            "root_cause": "RC-99",
            "root_cause_sub": None,
            "stop_type": "ST-03",
            "lifecycle_stage": "LS-03",
            "stated_intent": "continue",
            "actual_action": "active",
            "trigger_moment": "Automated monthly salary debit",
            "help_sources": ["none_mentioned"],
            "retention_factor": "RF-06",
            "sentiment_score": 0.90,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "Retained investor: RF-06 (Automated / hassle-free experience).",
    },
    {
        "item_id": "gs_item_024",
        "source": "youtube",
        "source_id": "yt_024",
        "star_rating": None,
        "text": "Seeing positive returns of 14% after 2 years of consistent SIP. Compounding is real, staying invested for 10 years.",
        "l1": {"root_cause": "RC-99", "stop_type": "ST-03", "lifecycle_stage": "LS-04", "stated_intent": "continue", "actual_action": "active", "retention_factor": "RF-01"},
        "l2": {"root_cause": "RC-99", "stop_type": "ST-03", "lifecycle_stage": "LS-04", "stated_intent": "continue", "actual_action": "active", "retention_factor": "RF-01"},
        "reconciled": {
            "root_cause": "RC-99",
            "root_cause_sub": None,
            "stop_type": "ST-03",
            "lifecycle_stage": "LS-04",
            "stated_intent": "continue",
            "actual_action": "active",
            "trigger_moment": "Seeing 14% compounding milestone",
            "help_sources": ["youtube"],
            "retention_factor": "RF-01",
            "sentiment_score": 0.95,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "Retained investor: RF-01 (Seeing positive returns).",
    },
    {
        "item_id": "gs_item_025",
        "source": "reddit",
        "source_id": "post_red_025",
        "star_rating": None,
        "text": "Just started researching personal finance. What is the difference between direct and regular mutual funds?",
        "l1": {"root_cause": "RC-99", "stop_type": "ST-99", "lifecycle_stage": "LS-00", "stated_intent": "neutral", "actual_action": "unknown", "retention_factor": None},
        "l2": {"root_cause": "RC-99", "stop_type": "ST-99", "lifecycle_stage": "LS-00", "stated_intent": "unknown", "actual_action": "unknown", "retention_factor": None},
        "reconciled": {
            "root_cause": "RC-99",
            "root_cause_sub": None,
            "stop_type": "ST-99",
            "lifecycle_stage": "LS-00",
            "stated_intent": "neutral",
            "actual_action": "unknown",
            "trigger_moment": "Beginning personal finance research",
            "help_sources": ["reddit"],
            "retention_factor": None,
            "sentiment_score": 0.0,
            "confidence_score": 1.0,
        },
        "reconciliation_note": "Pre-onboarding inquiry; unclassifiable root cause RC-99, stop_type ST-99.",
    },
]


def write_csv_files(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    items_csv = out_dir / "items.csv"
    labels_csv = out_dir / "labels.csv"

    # Write items.csv
    with open(items_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["item_id", "source", "source_id", "star_rating", "text"])
        for item in GOLDEN_SET_DATA:
            writer.writerow([
                item["item_id"],
                item["source"],
                item["source_id"],
                item["star_rating"] or "",
                item["text"],
            ])

    # Write labels.csv
    with open(labels_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "golden_id",
            "item_id",
            "labeller_1_labels",
            "labeller_2_labels",
            "reconciled_labels",
            "labeller_id",
            "labelled_at",
            "reconciliation_note",
        ])
        now_iso = datetime.now(timezone.utc).isoformat()
        for idx, item in enumerate(GOLDEN_SET_DATA, 1):
            g_id = f"gold_{idx:03d}"
            writer.writerow([
                g_id,
                item["item_id"],
                json.dumps(item["l1"]),
                json.dumps(item["l2"]),
                json.dumps(item["reconciled"]),
                "panel_pm_researcher",
                now_iso,
                item["reconciliation_note"],
            ])

    print(f"Written {len(GOLDEN_SET_DATA)} items to {items_csv} and {labels_csv}.")


def seed_database(db_path: str = "./data/sip_insight_lab.db"):
    conn = init_db(db_path)
    now_iso = datetime.now(timezone.utc).isoformat()

    with conn:
        for idx, item in enumerate(GOLDEN_SET_DATA, 1):
            item_id = item["item_id"]
            text = item["text"]
            h = compute_hash(text)

            # Insert raw_item
            conn.execute(
                """
                INSERT OR REPLACE INTO raw_item (
                    item_id, source, source_id, raw_text, raw_url,
                    star_rating, collected_at, dedup_hash, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    item["source"],
                    item["source_id"],
                    text,
                    f"https://{item['source']}.example.com/{item['source_id']}",
                    item["star_rating"],
                    now_iso,
                    h,
                    json.dumps({"is_golden": True}),
                ),
            )

            # Insert cleaned_item
            conn.execute(
                """
                INSERT OR REPLACE INTO cleaned_item (
                    item_id, cleaned_text, language, pii_removal_log,
                    cleaning_version, cleaned_at
                ) VALUES (?, ?, 'en', ?, '1.0', ?)
                """,
                (
                    item_id,
                    text,
                    json.dumps({"total_redacted": 0}),
                    now_iso,
                ),
            )

            # Insert golden_set
            g_id = f"gold_{idx:03d}"
            conn.execute(
                """
                INSERT OR REPLACE INTO golden_set (
                    golden_id, item_id, human_labels, labeller_id,
                    labelled_at, reconciliation_note
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    g_id,
                    item_id,
                    json.dumps(item["reconciled"]),
                    "panel_pm_researcher",
                    now_iso,
                    item["reconciliation_note"],
                ),
            )

    conn.close()
    print(f"Successfully seeded {len(GOLDEN_SET_DATA)} items into database tables (raw_item, cleaned_item, golden_set).")


if __name__ == "__main__":
    out_dir = PROJECT_ROOT / "golden_set"
    write_csv_files(out_dir)
    seed_database()
