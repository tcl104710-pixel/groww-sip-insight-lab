"""
SIP Insight Lab — Sample Feedback Generator for Phase 2 Testing
================================================================
Populates raw_item in sip_insight_lab.db with 250 realistic items
across all 5 platforms to enable end-to-end testing of:
  - Language filtering (English and Hindi vs other languages)
  - PII scrubbing (phone numbers, emails, UPI IDs, Aadhaar, PAN)
  - Noise removal (HTML, URLs, excessive punctuation, repeated words)
  - Normalisation (Unicode, mojibake, whitespace)
  - Pilot classification (200 items classified against taxonomy)

Usage:
    python scripts/seed_sample_feedback.py [--count 250]
"""

import argparse
import random
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.db.schema import init_db
from src.ingestion.dedup import compute_hash
from src.ingestion.writer import RawItem, RawItemWriter

FEEDBACK_TEMPLATES = [
    # RC-01: Involuntary Lapse (Mandate / Balance / 3 strikes)
    (
        "play_store",
        "My SIP was auto cancelled after 3 failed debits due to bank server issue at SBI. My number is 9876543210 please resolve.",
        1,
    ),
    (
        "app_store",
        "<p>Mandate failed for my HDFC account and Groww gave no alert! Email me at investor_{i}@gmail.com. Acc 123456789012.</p>",
        1,
    ),
    (
        "reddit",
        "Had insufficient balance on debit date because salary was delayed. Did not know Groww cancels SIP permanently after 3 misses!!",
        None,
    ),
    (
        "tradingqa",
        "NACH mandate rejection error on Groww. UPI ID is user{i}@okaxis. How to restart the same SIP without creating new folio?",
        None,
    ),
    (
        "youtube",
        "Sir my SIP was debited from bank but not showing in Groww app. Customer care not responding. Check https://groww.in/support",
        None,
    ),

    # RC-02: UX & Payment Friction
    (
        "play_store",
        "Very confusing interface after recent update. Cannot find the button to pause my monthly SIP. Very frustrating!!!!",
        2,
    ),
    (
        "app_store",
        "KYC documentation rejected 4 times without clear reason. PAN ABCDE{i:04d}F is valid on IT portal. Bad app bad app bad app.",
        1,
    ),
    (
        "reddit",
        "Trying to change my SIP debit date from 5th to 10th. The modify flow is completely broken on Android app.",
        None,
    ),

    # RC-03: Return Disappointment
    (
        "reddit",
        "Invested for 6 months in small cap fund. Calculator showed 18% CAGR but portfolio is -5%. Stopping all SIPs now.",
        None,
    ),
    (
        "play_store",
        "Finfluencer on YouTube promised 20% returns in mutual funds. I am losing money every month. Groww is cheating retail investors.",
        1,
    ),
    (
        "tradingqa",
        "Market correction scared me. Nifty fell 800 points and my mutual fund SIP value decreased. Thinking of exiting.",
        None,
    ),

    # RC-04: Income Change
    (
        "reddit",
        "Unfortunately got laid off last week. Paused my 15k monthly SIP for 3 months until I find another tech job.",
        None,
    ),
    (
        "play_store",
        "Had medical emergency in family so had to stop SIP and withdraw money. App made redemption easy though.",
        4,
    ),

    # RC-05: Deliberate Informed Exit
    (
        "reddit",
        "Hit my financial goal for house downpayment after 3 years of disciplined SIP. Stopped SIP and initiated SWP.",
        None,
    ),
    (
        "tradingqa",
        "Switching from active large cap fund to Nifty 50 index fund on Groww. Stopped the active SIP today.",
        None,
    ),

    # RC-06: Knowledge Gap
    (
        "play_store",
        "Why was money deducted when market was closed on Sunday? Groww stole my 2000 rupees. Scam application!",
        1,
    ),
    (
        "youtube",
        "I do not understand what NAV means. If NAV is high does it mean I am getting less units? Please make a video.",
        None,
    ),

    # RC-07: External Influence
    (
        "reddit",
        "My uncle told me stock market is gambling and asked me to cancel mutual fund and put in fixed deposit. What should I do?",
        None,
    ),

    # Continuers / Retention (RF-01 to RF-07)
    (
        "reddit",
        "Been doing SIP in Parag Parikh Flexi Cap for 2 years now. Rupee cost averaging really works during market dips. Staying invested!",
        None,
    ),
    (
        "play_store",
        "Clean UI, smooth auto-debit on salary day. Set it and forget it. Very happy with Groww SIP investing.",
        5,
    ),
    (
        "youtube",
        "Started with 500 rs SIP 1 year ago, seeing good compounding now. Highly recommend every beginner to start small.",
        None,
    ),

    # Hindi (Devanagari)
    (
        "play_store",
        "मेरा SIP अपने आप रद्द हो गया क्योंकि बैंक से पैसा नहीं कटा। ग्रो ऐप में कोई सूचना नहीं आई।",
        1,
    ),
    (
        "youtube",
        "म्यूचुअल फंड में हर महीने 1000 रुपये का एसआईपी करना बहुत आसान है। बहुत बढ़िया जानकारी।",
        None,
    ),

    # Discard sample: Other language (French)
    (
        "play_store",
        "L'application est très difficile à utiliser et le service client ne répond jamais aux messages.",
        1,
    ),
]


def seed_samples(db_path: str = "./data/sip_insight_lab.db", count: int = 250) -> int:
    conn = init_db(db_path)
    writer = RawItemWriter(conn)
    written = 0

    logger = RawItemWriter(conn)

    for i in range(count):
        tmpl_source, tmpl_text, star = FEEDBACK_TEMPLATES[i % len(FEEDBACK_TEMPLATES)]
        text = tmpl_text.format(i=i + 1000)
        # Append unique user tag to ensure unique dedup hash
        text = f"{text} (Ref #{i+1:04d})"

        source_id = f"seed_{tmpl_source}_{i+1}"
        h = compute_hash(text)

        item = RawItem(
            source=tmpl_source,
            source_id=source_id,
            raw_text=text,
            raw_url=f"https://{tmpl_source}.example.com/{source_id}",
            star_rating=star,
            dedup_hash=h,
        )

        if writer.write(item):
            written += 1

    conn.close()
    return written


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=250)
    parser.add_argument("--db-path", type=str, default="./data/sip_insight_lab.db")
    args = parser.parse_args()

    n = seed_samples(args.db_path, args.count)
    print(f"Seeded {n} realistic sample feedback items into {args.db_path}.")
