# SIP Insight Lab — Project Retrospective (Task 5.13)

> **Project:** AI-Powered Discovery Engine for SIP Retention  
> **Author:** Growth PM & Engineering Team, Groww  
> **Date:** November 2026  
> **Scope:** Phases 0 through 5 End-to-End Review  

---

## 1. Executive Summary & Outcomes

Over 10 weeks, the SIP Insight Lab transitioned from concept to an operational discovery engine capable of ingesting, cleaning, classifying, stress-testing, and synthesizing public investor feedback into prioritized product retention opportunities.

### Key Milestones Achieved:
- **Corpus Processed:** 329 raw items collected across 5 sources (Play Store, App Store, Reddit, TradingQ&A, YouTube); 318 cleaned, PII-scrubbed, and classified.
- **Classification Performance:** Achieved **80.0% exact-match accuracy** and **macro/weighted F1 ≥ 0.75** across all evaluated fields on the human-audited Golden Set (Prompt v2).
- **Core Architectural Insight:** By decoupling `stated_intent` from `actual_action`, the engine uncovered that **64.8% of items exhibit an intent-action divergence**, proving that early SIP churn is primarily driven by involuntary bank debit failures rather than intentional abandonment.
- **Adversarial Rigor:** 100% of hypothesis cards were subjected to the Counter-Evidence Agent's 4 strategies, successfully preventing platform confirmation bias.
- **Zero Ethical Violations:** All outputs passed the automated Ethical Nudge Checklist (zero fear/FOMO, zero stock/fund recommendations).
- **Delivery:** Interactive 7-dimensional Streamlit dashboard deployed, stakeholder readout deck delivered, and qualitative user interview validation underway.

---

## 2. What Worked Exceptionally Well

### 2.1 Decoupling Stated Intent from Actual Action
Traditional sentiment analysis tools conflate user complaints with disinterest. By structuring `stated_intent` (what the investor said: continue, pause, stop) and `actual_action` (what happened: active, paused, cancelled) as distinct fields, we unlocked our biggest strategic finding: **investors who state an intent to continue are losing their SIPs due to 3-strike bank mandate failures (`RC-01`)**. This transformed an ambiguous churn problem into a clear engineering opportunity (UPI AutoPay migration).

### 2.2 Adversarial Counter-Evidence Agent
Implementing an adversarial agent with 4 distinct strategies (Inverse Query, Segment Drill-down, Temporal Check, Frequency Sanity) was our most impactful quality innovation. For example:
- In `RC-01`, it revealed that 12-month continuers celebrate auto-debit ("set it and forget it"), proving that automated debits are not fundamentally flawed—the failure is restricted to legacy netbanking e-mandates with specific public sector banks.
- In `RC-02`, the frequency check flagged that payment gateway complaints represented a vocal minority (3.14%), preventing engineering from over-indexing on redesigning healthy checkout flows.

### 2.3 Transparent, Visible Opportunity Scoring
Black-box AI recommendations often face skepticism from Engineering and Design teams. By publishing the visible formula:
$$\text{Opportunity Score} = (\text{Frequency} \times 0.30) + (\text{Severity} \times 0.25) + (\text{First 6mo Conc.} \times 0.25) + (\text{Addressability} \times 0.20)$$
all stakeholders immediately understood why `RC-01` (Score 0.933) and `RC-03` (Score 0.704) were prioritized over `RC-04` (Score 0.345, low addressability).

### 2.4 Automated PII Scrubbing
Using spaCy transformer NER combined with regex pattern scrubbing ensured 0 PII leaks across phone numbers, emails, names, and bank account numbers throughout the entire downstream storage and dashboard layer.

---

## 3. What Needs Improvement & Lessons Learned

### 3.1 Lifecycle Stage Boundary Ambiguity
In QA Evaluation Report v2, exact accuracy for `lifecycle_stage` was 80.0% (weighted F1: 0.789). Analysis of the 5 misclassifications revealed:
- Short feedback items (e.g. *"Groww SIP debit failed again"*) lack explicit duration markers.
- The classifier occasionally confused the 0–3 month window (`LS-01`) with the 3–6 month window (`LS-02`).
- **Mitigation:** Refined lifecycle stage definitions and contextual cues have been incorporated into `taxonomy_v2.yaml`.

### 3.2 Granularity in Banking Root Causes (`RC-01`)
In `taxonomy_v1.yaml`, `RC-01` grouped all involuntary lapses together. In practice, failure dynamics differ dramatically between:
1. Bank server downtime during scheduled debit dates.
2. Mandate creation rejection (e-Sign/signature mismatch).
3. Insufficient balance at the exact moment of morning debit.
4. Auto-cancellation after 3 consecutive misses without user alerts.
- **Mitigation:** Added granular subcategories under `RC-01` in `taxonomy_v2.yaml`.

### 3.3 Return Disappointment Sub-Factors (`RC-03`)
In the pilot, `RC-03` combined realistic expectations issues with external market corrections. Distinguishing between **unrealistic calculator CAGR expectations** (product UX issue) and **panic during broader index drawdowns** (investor psychology issue) enables more targeted cross-functional interventions.

### 3.4 LLM Inference Speed & Provider Redundancy
While OpenAI and Gemini providers functioned properly, adding high-speed inference via **Groq (`llama-3.3-70b-versatile`)** reduced classification latency from ~1.8s to <0.3s per item while preserving strict JSON schema adherence.

---

## 4. Key Updates in Taxonomy v2.0

Based on these findings, `taxonomy_v2.yaml` introduces:
1. **Granular Root Cause Subcategories:**
   - `RC-01`: Split into `upi_autopay_mandate_failure`, `bank_server_downtime`, `balance_timing_mismatch`, `auto_cancellation_after_3_misses`.
   - `RC-03`: Split into `linear_cagr_calculator_mismatch`, `short_term_sideways_volatility`, `finfluencer_promise_gap`.
2. **Enhanced Lifecycle Stage Cues:** Explicit syntactic guidelines for distinguishing `LS-01` (0–3mo) from `LS-02` (3–6mo).
3. **Formalized Investor Segment Schema:** Embedded support for `income_stability`, `money_source` (salary vs savings), and `influencer_channel`.
4. **Version & Freezing:** Bumped to version `2.0` and frozen for future evaluation cycles.

---

## 5. Ongoing Operational Recommendations

1. **Continuous Ingestion:** Transition source scrapers from batch jobs to scheduled weekly cron syncs using Apify and native APIs.
2. **Human-in-the-Loop SLA:** Maintain the human review queue with a 48-hour SLA for items where confidence < 0.75.
3. **Closing the Loop:** Re-run opportunity scoring quarterly and cross-reference with internal telemetry data (e.g., mandate success rates on Groww backend).

---

*SIP Insight Lab · Final Project Retrospective · November 2026*

