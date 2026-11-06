# Groww SIP Insight Lab — Data Collection & Cleaning Summary

**Generated:** 2026-11-05 07:57:04 UTC  
**Scope:** Multi-Source Feedback Pipeline (Google Play Store, Apple App Store, Reddit, YouTube)  

---

## 1. Executive Summary

This report documents the end-to-end data collection, normalization, cleaning, and filtering pipeline executed for the **Groww SIP Insight Lab**. The pipeline captured all publicly accessible user discussions, app reviews, and investor commentary without artificial caps, followed by strict deduplication, timestamp normalization, and multi-factor SIP relevance classification.

| Metric | Count | Percentage |
| :--- | :--- | :--- |
| **Total Raw Records Extracted** | `4983` | 100.0% |
| **Cleaned & Normalized Records** | `3726` | 74.8% |
| **Trivial Noise / Duplicates Removed** | `1257` | 25.2% |
| **SIP & Mutual Fund Relevant Records** | `1029` | 27.6% of cleaned |
| **Irrelevant / General Platform Records** | `2697` | 72.4% of cleaned |

---

## 2. Per-Source Ingestion & Cleaning Metrics

| Source Platform | Raw Records | Cleaned Records | Dropped / Dups | Retention Rate | Primary Identifier |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Google Play Store** | `3000` | `2040` | `960` | 68.0% | `com.nextbillion.groww` |
| **Apple App Store** | `93` | `93` | `0` | 100.0% | App ID `1404871703` |
| **Reddit** | `256` | `256` | `0` | 100.0% | r/IndiaInvestments, r/mutualfunds, r/Groww |
| **YouTube** | `1634` | `1342` | `292` | 82.1% | YouTube Data API v3 (7 query clusters) |
| **Total** | **`4983`** | **`3726`** | **`1257`** | **74.8%** | — |

---

## 3. Cleaning & Normalization Rules Applied

1. **Text Integrity Preservation:** Original user text was strictly preserved in `raw_text`. A cleaned normalization (`cleaned_text`) was produced solely for tokenization, hashing, and regex evaluation without semantic alteration.
2. **Noise & Spam Removal:** Records with fewer than 10 characters, empty text, or whitespace-only bodies were removed.
3. **Exact & Semantic Deduplication:** Deduplication was performed using a composite SHA-256 fingerprint generated from alphanumeric lowercase text per source and globally across overlapping crossposts.
4. **Timestamp Standardization:** Heterogeneous date representations (RFC 2822, UNIX epoch timestamps, UTC ISO strings, and localized RSS timestamps) were normalized into standard ISO-8601 UTC strings (`YYYY-MM-DDTHH:MM:SSZ`).
5. **Rating Normalization:** Numeric 1-5 star ratings were retained for Google Play Store and Apple App Store, with `None` explicitly recorded for unstructured discussion forums (Reddit and YouTube).

---

## 4. SIP Relevance Identification Methodology

The relevance filter (`src/pipeline/filter_sip.py`) scored each item across 8 domain dimensions:
1. **Mandate / Auto-Debit Issues:** eNACH, bank debit bounces, failed mandates, double charges.
2. **Continuation, Pause & Discontinuation:** Pausing SIP, cancellation workflows, redemption, and switching.
3. **Returns, Volatility & Loss Panic:** Negative portfolio values, XIRR drops, market dips, and benchmark underperformance.
4. **Monthly Affordability & Cash Crunches:** Salary delays, job transitions, emergency budgeting pressures.
5. **Portfolio Tracking & NAV Allotment:** Delayed NAV, allocation discrepancies, CAMS/KFintech synchronization.
6. **Support & Guidance Needs:** Customer care responsiveness, beginner uncertainty, portfolio advice.
7. **Core SIP & Mutual Fund Experience:** Systematic wealth creation, disciplined compounding, and platform usability.

All records passing the relevance threshold were segregated into `sip_feedback_relevant.csv`, while non-SIP items were archived into `data/sip_feedback_irrelevant.csv` for full transparency.
