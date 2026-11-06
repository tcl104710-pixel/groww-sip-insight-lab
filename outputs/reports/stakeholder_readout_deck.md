# SIP Insight Lab — Executive Stakeholder Readout Deck (Phase 5)

> **Initiative:** AI-Powered Discovery Engine for First-Time Investor SIP Retention  
> **Prepared For:** Growth, Design, and Engineering Leadership — Groww  
> **Date:** November 2026  
> **Status:** Final Readout & Validation Handoff  

---

## 1. Executive Summary & Problem Context

### The Retention Challenge
First-time mutual fund investors experience the steepest retention drop-off within the first **0 to 6 months** of starting their first SIP. Traditionally, product decisions relied on fragmented play store reviews, customer support escalation tickets, and subjective opinions. 

### What SIP Insight Lab Achieved
We built and deployed an end-to-end discovery engine that replaces opinion with **traceable, AI-classified evidence** across 5 public investor channels (Google Play Store, Apple App Store, Reddit r/IndiaInvestments, TradingQ&A, YouTube mutual fund communities):

1. **Cleaned & Scrubbed Corpus:** 318 classified items rigorously scrubbed of PII (names, emails, phone numbers, account numbers, folio numbers).
2. **Decoupled Architecture:** Stated Intent and Actual Action stored as separate dimensions, revealing that **64.8% of items exhibit an Intent vs. Action Gap**—unmasking massive involuntary churn previously misattributed to voluntary loss of interest.
3. **Rigorous Quality Gate:** Evaluated against an audited golden set, achieving **80.0% exact accuracy** and **macro/weighted F1 ≥ 0.75** across all taxonomy fields.
4. **Adversarial Counter-Evidence:** Every hypothesis was stress-tested by a specialized counter-evidence agent to eliminate confirmation bias.
5. **Ethical Guardrails:** 100% of hypothesis cards passed the ethical nudge checklist—guaranteeing **zero FOMO language, zero urgency manipulation, and zero specific stock/fund recommendations**.

---

## 2. Core Discovery Engine Architecture & Scoring Formula

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Opportunity Score = (Frequency × 0.30) + (Severity × 0.25)                            │
│                     + (First_6mo_Conc × 0.25) + (Addressability × 0.20)                 │
│                                                                                        │
│ • Frequency: Volume share of feedback corpus [0.0–1.0]                                 │
│ • Severity: Mean absolute sentiment intensity of affected investors [0.0–1.0]          │
│ • First 6mo Conc: % of issues occurring in the vulnerable 0–6 month window [0.0–1.0]   │
│ • Addressability: Binary filter (1.0 = solvable via product/UX; 0.0 = external macro)  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Executive Priority Ranking Overview

| Rank | Root Cause Code | Opportunity Description | Volume | First 6mo Conc. | Severity | Opp. Score | Confidence | Recommended Action |
|:---:|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **#1** | `RC-01` | **Automated Mandate Recovery & Smart Retries** | 150 (47.2%) | 98.7% | 0.74 | **0.933** | High | **Immediate Product Sprint** |
| **#2** | `RC-03` | **Range-Based Realistic Return Calculators** | 44 (13.8%) | 100.0% | 0.66 | **0.704** | High | **User Interview Validation** |
| **#3** | `RC-02` | **UX & Payment Friction in Pause/Cancel Flows** | 10 (3.1%) | 100.0% | 0.70 | **0.645** | Medium | **Design & Eng Quick-Fix** |
| **#4** | `RC-06` | **Investor Volatility & Rupee-Cost Education** | 10 (3.1%) | 100.0% | 0.61 | **0.624** | Medium | **Content & Nudge Experiment** |
| **#5** | `RC-07` | **Transparent Benchmark vs. Finfluencer Hype** | 9 (2.8%) | 100.0% | 0.24 | **0.529** | Low | **Exploratory Research** |
| #6 | `RC-04` | Flexible Pause Controls for Income Shocks | 19 (6.0%) | 84.2% | 0.39 | **0.345** | Medium | Product Backlog |
| #7 | `RC-99` | Unclassifiable Feedback Bucket | 60 (18.9%) | 3.3% | 0.11 | **0.157** | High | Long-term Monitoring |
| #8 | `RC-05` | Goal Realisation & Voluntary Rebalancing | 16 (5.0%) | 0.0% | 0.26 | **0.097** | Medium | Normal Lifecycle (Non-Churn) |

---

## 4. Top 5 Ranked Opportunities In Depth

### #1 Opportunity: `RC-01` — Eliminate Involuntary Churn via Automated Mandate Recovery & Smart Retries
- **Opportunity Score:** **0.933** | **Confidence:** High | **Corpus Share:** 47.2% (150 items)
- **Problem Statement:** 
  Investors intend to continue investing, but their SIP auto-cancels after 3 consecutive bank debit failures caused by public sector bank downtime (SBI, ICICI, PNB) or balance timing mismatches.
- **Traceable Verbatim Evidence:**
  - *"My SIP got cancelled automatically after 3 failed debits because SBI server was down. Groww should have notified me before cancelling!"* (Play Store, LS-01)
  - *"e-Mandate rejected for ICICI bank account and SIP was cancelled. Customer support took 5 days to respond."* (App Store, LS-01)
  - *"Forgot to maintain minimum balance in bank account on the 5th. Missed 2 debits and now my SIP is stopped."* (Reddit, LS-01)
- **Adversarial Counter-Evidence Finding:**
  Active long-term continuers (`LS-04`) celebrate automated debits (*"Set it and forget it"*). Adversarial analysis proves this is not a general failure of auto-debit, but a cohort-specific breakdown on legacy e-mandate integrations with specific public sector banks.
- **Strategic Recommendations:**
  - **Engineering:** Migrate users from legacy netbanking mandates to **UPI AutoPay 2.0** with dynamic retry windows.
  - **Product & Design:** Create a **"Fix Mandate in 1-Tap"** recovery card with clear bank error explanations.
  - **Growth:** Introduce a **Pre-Debit Balance Nudge (T-24h)** alert via WhatsApp/Push before debit attempts.

---

### #2 Opportunity: `RC-03` — Align Investor Expectations via Range-Based Realistic SIP Return Calculators
- **Opportunity Score:** **0.704** | **Confidence:** High | **Corpus Share:** 13.8% (44 items)
- **Problem Statement:**
  First-time investors experience severe return disappointment between **months 3 and 6 (`LS-02`)**. In-app static calculators show linear 15%–20% compounding curves, creating unrealistic expectations that collide with short-term sideways market volatility.
- **Traceable Verbatim Evidence:**
  - *"Invested in midcap fund for 5 months. Calculator promised 15% return but portfolio is down 4%. Stopping my SIP."* (Reddit, LS-02)
  - *"YouTube finfluencer recommended this flexi cap fund claiming 20% guaranteed returns. Complete scam I am in loss."* (Play Store, LS-01)
  - *"Nifty dropped 600 points last week and my fund NAV fell. Scared of losing more capital so I stopped the SIP."* (TradingQ&A, LS-01)
- **Adversarial Counter-Evidence Finding:**
  Temporal checks reveal that 12-month retained investors (`LS-04`) experienced identical flat returns during months 3–6, but persisted because they understood rupee-cost averaging. Disappointment stems from calculator framing, not fund underperformance.
- **Strategic Recommendations:**
  - **Design/Product:** Deprecate single-point static CAGR calculators in favor of **Range-Based Rolling Return Visualizers** showing worst-case, median, and best-case 3-year outcomes.
  - **Growth:** Deploy educational nudges at Month 3 explaining how sideways markets accumulate more units at lower NAV.

---

### #3 Opportunity: `RC-02` — Remove UX & Payment Friction in SIP Setup, Pause, and Cancellation Workflows
- **Opportunity Score:** **0.645** | **Confidence:** Medium | **Corpus Share:** 3.1% (10 items)
- **Problem Statement:**
  Investors encounter edge-case payment gateway timeouts and confusing UI toggles when attempting to modify or temporarily pause SIP dates.
- **Traceable Verbatim Evidence:**
  - *"App update made SIP modification impossible. Tried pausing for a month but the toggle throws network error."* (Play Store, LS-01)
  - *"Payment gateway failed twice during SIP instalment debit. Money debited from bank but units not allotted."* (App Store, LS-01)
- **Strategic Recommendations:**
  - **Engineering:** Implement idempotent payment polling for debited funds pending unit allotment; auto-resolve status within 2 hours.
  - **Design:** Simplify the pause toggle into an intuitive "Skip Next Installment" action without requiring SIP cancellation.

---

### #4 Opportunity: `RC-06` — Close Investor Knowledge Gaps on Market Volatility & Rupee-Cost Averaging
- **Opportunity Score:** **0.624** | **Confidence:** Medium | **Corpus Share:** 3.1% (10 items)
- **Problem Statement:**
  First-time investors panic during index corrections, conflating temporary market pullbacks with irreversible capital loss.
- **Strategic Recommendations:**
  - **Product/Content:** In-app contextual tooltip when NAV falls: *"Market dip alert: Your next installment will purchase units at a lower price."*

---

### #5 Opportunity: `RC-07` — Anchor Investors Against Social Influencer Hype through Transparent Benchmark Data
- **Opportunity Score:** **0.529** | **Confidence:** Low | **Corpus Share:** 2.8% (9 items)
- **Problem Statement:**
  Investors onboarding via influencer hype pick volatile sectoral/thematic funds without understanding risks.
- **Strategic Recommendations:**
  - **Design:** Display fund benchmark comparisons (Nifty 50, category average) alongside riskometers on fund discovery pages.

---

## 5. Intent vs. Action Gap Analysis

Our classification engine explicitly uncoupled `stated_intent` from `actual_action`. The results:

```
Total Items Analyzed : 318
Intent-Action Gaps   : 206 items (64.8%)
Aligned Items        : 112 items (35.2%)
```

- **The Big Insight:** Over 60% of investors whose SIP was cancelled had stated an intent to **"continue"** or **"pause"**. They did not churn because they lost confidence in investing; their SIP was killed by banking infrastructure timeouts.
- **Product Impact:** Fixing mandate recovery directly addresses the single largest segment of early SIP churn.

---

## 6. Action Items & Validation Roadmap

| Workstream | Action Item | Owner | Target Date |
|---|---|---|---|
| **Product & Eng** | UPI AutoPay 2.0 migration & Pre-Debit SMS/WhatsApp Alerts | Engineering Lead | Sprint 46 |
| **UX & Design** | Range-based Return Calculator & 1-Tap Mandate Recovery UI | Product Design Lead | Sprint 47 |
| **User Research** | Conduct 5 validation interviews using attached guides | User Research Lead | Nov 10–18 |
| **Growth Ops** | Launch Month 3 & Month 6 Rupee-Cost Averaging lifecycle emails | Growth Marketing | Sprint 48 |
| **Compliance** | Maintain audit log archive & enforce nudge checklist on all future copy | PM & Legal | Ongoing |

---

*Delivered by SIP Insight Lab · Phase 5 Delivery, Validation & Handoff*

