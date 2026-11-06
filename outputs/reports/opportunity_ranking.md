# SIP Insight Lab — Opportunity Ranking Report

## Opportunity Scoring Formula

```
Opportunity Score = (Frequency × 0.30) + (Severity × 0.25) + (First_6mo_Conc × 0.25) + (Addressability × 0.20)
All components normalised to [0.0, 1.0].
```

## Ranked Priority Opportunities

| Rank | Root Cause | Opportunity Focus | Items (%) | Stage Focus | Freq (30%) | Sev (25%) | 6mo (25%) | Addr (20%) | **Opp Score** | Confidence |
|:---:|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **#1** | `RC-01` | Eliminate Involuntary Churn via Automated Mandate Recovery & Smart Retries | 150 (47.2%) | `LS-01` | 1.00 | 0.74 | 0.99 | 1.00 | **0.933** | High |
| **#2** | `RC-03` | Align Investor Expectations via Range-Based Realistic SIP Return Calculators | 44 (13.8%) | `LS-02` | 0.29 | 0.66 | 1.00 | 1.00 | **0.704** | High |
| **#3** | `RC-02` | Remove UX & Payment Friction in SIP Setup, Pause, and Cancellation Workflows | 10 (3.1%) | `LS-01` | 0.07 | 0.70 | 1.00 | 1.00 | **0.645** | Medium |
| **#4** | `RC-06` | Close Investor Knowledge Gaps on Market Volatility & Rupee-Cost Averaging | 10 (3.1%) | `LS-01` | 0.07 | 0.61 | 1.00 | 1.00 | **0.624** | Medium |
| **#5** | `RC-07` | Anchor Investors Against Social Influencer Hype through Transparent Benchmark Data | 9 (2.8%) | `LS-01` | 0.06 | 0.24 | 1.00 | 1.00 | **0.529** | Low |
| **#6** | `RC-04` | Provide Emergency Liquidity Relief via Flexible SIP Pause & Step-Down Controls | 19 (6.0%) | `LS-02` | 0.13 | 0.39 | 0.84 | 0.00 | **0.345** | Medium |
| **#7** | `RC-99` | Address Unclassifiable Feedback via Exploratory Discovery | 60 (18.9%) | `LS-04` | 0.40 | 0.11 | 0.03 | 0.00 | **0.157** | High |
| **#8** | `RC-05` | Facilitate Seamless Informed Portfolio Rebalancing & Goal Realisation | 16 (5.0%) | `LS-04` | 0.11 | 0.26 | 0.00 | 0.00 | **0.097** | Medium |

---

## Detailed Opportunity Rationales

### #1 `RC-01`: Eliminate Involuntary Churn via Automated Mandate Recovery & Smart Retries
- **Root Cause Category:** Involuntary Lapse (`RC-01`)
- **Opportunity Score:** **0.933** (Confidence: High)
- **Volume in Corpus:** 150 items (47.17% of feedback corpus)
- **Early Churn Concentration:** 98.7% occurring in first 6 months
- **Addressability Assessment:** High addressability via UPI AutoPay migration, pre-debit balance nudges, and smart auto-retry before 3-strike cancellation.

**Representative Verbatim Quotes:**
- "My SIP got cancelled automatically after 3 failed debits because SBI server was down. Groww should have notified me before cancelling!" — (Source: play_store, Stage: LS-01)
- "e-Mandate rejected for ICICI bank account and SIP was cancelled. Customer support took 5 days to respond." — (Source: app_store, Stage: LS-01)
- "Forgot to maintain minimum balance in bank account on the 5th. Missed 2 debits and now my SIP is stopped." — (Source: reddit, Stage: LS-01)

### #2 `RC-03`: Align Investor Expectations via Range-Based Realistic SIP Return Calculators
- **Root Cause Category:** Return Disappointment (`RC-03`)
- **Opportunity Score:** **0.704** (Confidence: High)
- **Volume in Corpus:** 44 items (13.84% of feedback corpus)
- **Early Churn Concentration:** 100.0% occurring in first 6 months
- **Addressability Assessment:** Addressable via realistic range-based CAGR calculators, rolling return visualisations, and 3-5 year horizon education.

**Representative Verbatim Quotes:**
- "YouTube finfluencer recommended this flexi cap fund claiming 20% guaranteed returns. Complete scam I am in loss." — (Source: play_store, Stage: LS-01)
- "Invested in midcap fund for 5 months. Calculator promised 15% return but portfolio is down 4%. Stopping my SIP." — (Source: reddit, Stage: LS-02)
- "Nifty dropped 600 points last week and my fund NAV fell. Scared of losing more capital so I stopped the SIP." — (Source: tradingqa, Stage: LS-01)

### #3 `RC-02`: Remove UX & Payment Friction in SIP Setup, Pause, and Cancellation Workflows
- **Root Cause Category:** UX & Payment Friction (`RC-02`)
- **Opportunity Score:** **0.645** (Confidence: Medium)
- **Volume in Corpus:** 10 items (3.14% of feedback corpus)
- **Early Churn Concentration:** 100.0% occurring in first 6 months
- **Addressability Assessment:** High addressability via simplified SIP management UI, transparent error codes, and self-serve pause/skip controls.

**Representative Verbatim Quotes:**
- "App update made SIP modification impossible. Tried pausing for a month but the toggle throws network error." — (Source: play_store, Stage: LS-01)
- "Payment gateway failed twice during SIP instalment debit. Money debited from bank but units not allotted." — (Source: app_store, Stage: LS-01)
- "KYC rejected 3 times for signature mismatch. Unable to complete first SIP debit." — (Source: reddit, Stage: LS-00)

### #4 `RC-06`: Close Investor Knowledge Gaps on Market Volatility & Rupee-Cost Averaging
- **Root Cause Category:** Knowledge Gap (`RC-06`)
- **Opportunity Score:** **0.624** (Confidence: Medium)
- **Volume in Corpus:** 10 items (3.14% of feedback corpus)
- **Early Churn Concentration:** 100.0% occurring in first 6 months
- **Addressability Assessment:** Addressable via in-app contextual coaching explaining NAV fluctuations, rupee-cost averaging, and normal market volatility.

**Representative Verbatim Quotes:**
- "Why was money deducted on Sunday when stock market is closed? Groww stole my money, lodge police complaint!" — (Source: play_store, Stage: LS-01)
- "Did not realize market fluctuation causes NAV to go down temporarily. Thought mutual funds only go up." — (Source: reddit, Stage: LS-01)
- "I am confused about NAV. If NAV increases does my profit decrease? Nobody explains clearly." — (Source: youtube, Stage: LS-01)

### #5 `RC-07`: Anchor Investors Against Social Influencer Hype through Transparent Benchmark Data
- **Root Cause Category:** External Influence (`RC-07`)
- **Opportunity Score:** **0.529** (Confidence: Low)
- **Volume in Corpus:** 9 items (2.83% of feedback corpus)
- **Early Churn Concentration:** 100.0% occurring in first 6 months
- **Addressability Assessment:** Addressable by countering speculative finfluencer narratives with transparent historical fund benchmark facts.

**Representative Verbatim Quotes:**
- "Finfluencer said small caps are overheated and advised shifting to debt funds. Cancelled my Nippon small cap SIP." — (Source: youtube, Stage: LS-01)
- "Colleague convinced me that mutual funds are crashing and urged me to withdraw everything and buy gold coins." — (Source: reddit, Stage: LS-01)
- "My uncle told me stock market is gambling and asked me to cancel mutual fund and put in fixed deposit. What should I do? (Ref #0018)" — (Source: reddit, Stage: LS-01)

### #6 `RC-04`: Provide Emergency Liquidity Relief via Flexible SIP Pause & Step-Down Controls
- **Root Cause Category:** Income Change (`RC-04`)
- **Opportunity Score:** **0.345** (Confidence: Medium)
- **Volume in Corpus:** 19 items (5.97% of feedback corpus)
- **Early Churn Concentration:** 84.2% occurring in first 6 months
- **Addressability Assessment:** Personal cash-flow shock / job loss is an external macroeconomic constraint, though flexible SIP pause helps mitigate.

**Representative Verbatim Quotes:**
- "Salary reduced by 25% due to company restructuring. Need to cut discretionary investment outflow." — (Source: tradingqa, Stage: LS-99)
- "Family medical emergency forced me to cancel my monthly SIP and redeem accumulated units." — (Source: play_store, Stage: LS-02)
- "Laid off from tech company last week. Pausing my 20k SIP until I secure another job." — (Source: reddit, Stage: LS-03)

### #7 `RC-99`: Address Unclassifiable Feedback via Exploratory Discovery
- **Root Cause Category:** Unclassifiable (`RC-99`)
- **Opportunity Score:** **0.157** (Confidence: High)
- **Volume in Corpus:** 60 items (18.87% of feedback corpus)
- **Early Churn Concentration:** 3.3% occurring in first 6 months
- **Addressability Assessment:** Ambiguous or incomplete feedback cannot be addressed without further qualitative discovery.

**Representative Verbatim Quotes:**
- "Investing in Parag Parikh Flexi Cap for 18 months. Rupee cost averaging is working wonders during market corrections. Continuing every mo..." — (Source: reddit, Stage: LS-04)
- "Seeing positive returns of 14% after 2 years of consistent SIP. Compounding is real, staying invested for 10 years." — (Source: youtube, Stage: LS-04)
- "Auto debit on 1st of every month without fail. Set it and forget it. Excellent disciplined investing experience." — (Source: play_store, Stage: LS-01)

### #8 `RC-05`: Facilitate Seamless Informed Portfolio Rebalancing & Goal Realisation
- **Root Cause Category:** Deliberate Informed Exit (`RC-05`)
- **Opportunity Score:** **0.097** (Confidence: Medium)
- **Volume in Corpus:** 16 items (5.03% of feedback corpus)
- **Early Churn Concentration:** 0.0% occurring in first 6 months
- **Addressability Assessment:** Deliberate informed goal redemption or planned allocation rebalancing is natural investor lifecycle, not product failure.

**Representative Verbatim Quotes:**
- "Switching from active large cap fund to Nifty 50 direct index fund on the same Groww app. Stopped the active fund SIP." — (Source: tradingqa, Stage: LS-03)
- "Completed 3 years of SIP and reached my target 5 lakh downpayment for a car. Cancelled SIP to book profits." — (Source: reddit, Stage: LS-04)
- "Hit my financial goal for house downpayment after 3 years of disciplined SIP. Stopped SIP and initiated SWP. (Ref #0014)" — (Source: reddit, Stage: LS-04)
