# SIP Insight Lab — Quality Assurance Report (V1)

- **Evaluation Timestamp:** 2026-11-01T05:12:46.991678+00:00
- **Prompt Version Tested:** `v1`
- **Golden Set Size:** 25 items
- **Exact-Match Overall Accuracy:** **20.0%** (Target: ≥ 80% — **FAIL**)
- **All Per-Field F1 ≥ 0.75:** **NO (ACTION REQUIRED)**

---

## 1. Per-Field Performance Summary

| Taxonomy Field | Accuracy | Macro F1 | Weighted F1 | Target (≥0.75) | Status |
|---|---|---|---|---|---|
| `root_cause` | 60.0% | 0.561 | **0.582** | ≥ 0.75 | **FAIL** |
| `stop_type` | 52.0% | 0.515 | **0.581** | ≥ 0.75 | **FAIL** |
| `lifecycle_stage` | 40.0% | 0.440 | **0.465** | ≥ 0.75 | **FAIL** |
| `stated_intent` | 52.0% | 0.339 | **0.509** | ≥ 0.75 | **FAIL** |
| `actual_action` | 56.0% | 0.382 | **0.611** | ≥ 0.75 | **FAIL** |

---

## 2. Root Cause (RC) Per-Class Performance Breakdown

| Root Cause Code | Support | Precision | Recall | F1 Score |
|---|---|---|---|---|
| `RC-01` | 4 | 1.000 | 0.750 | **0.857** |
| `RC-02` | 3 | 0.500 | 0.333 | **0.400** |
| `RC-03` | 4 | 0.667 | 1.000 | **0.800** |
| `RC-04` | 3 | 1.000 | 0.333 | **0.500** |
| `RC-05` | 2 | 1.000 | 1.000 | **1.000** |
| `RC-06` | 3 | 1.000 | 0.333 | **0.500** |
| `RC-07` | 2 | 0.000 | 0.000 | **0.000** |
| `RC-99` | 4 | 0.300 | 0.750 | **0.429** |

---

## 3. Error Analysis and Misclassifications

Total field mismatches detected: **60**

| Item ID | Snippet | Field | Ground Truth | AI Prediction | Diagnosis |
|---|---|---|---|---|---|
| `gs_item_001` | My SIP got cancelled automatically after 3 failed debits because SBI server was ... | `stated_intent` | `unknown` | `continue` | Mismatch on stated_intent: ground_truth 'unknown' vs AI 'continue' |
| `gs_item_002` | e-Mandate rejected for ICICI bank account and SIP was cancelled. Customer suppor... | `stated_intent` | `unknown` | `continue` | Mismatch on stated_intent: ground_truth 'unknown' vs AI 'continue' |
| `gs_item_003` | Forgot to maintain minimum balance in bank account on the 5th. Missed 2 debits a... | `root_cause` | `RC-01` | `RC-99` | Model under-confident; defaulted to unclassifiable |
| `gs_item_003` | Forgot to maintain minimum balance in bank account on the 5th. Missed 2 debits a... | `stop_type` | `ST-01` | `ST-99` | Mismatch on stop_type: ground_truth 'ST-01' vs AI 'ST-99' |
| `gs_item_003` | Forgot to maintain minimum balance in bank account on the 5th. Missed 2 debits a... | `lifecycle_stage` | `LS-01` | `LS-99` | Mismatch on lifecycle_stage: ground_truth 'LS-01' vs AI 'LS-99' |
| `gs_item_003` | Forgot to maintain minimum balance in bank account on the 5th. Missed 2 debits a... | `actual_action` | `cancelled` | `unknown` | Mismatch on actual_action: ground_truth 'cancelled' vs AI 'unknown' |
| `gs_item_004` | NACH mandate expired after 1 year without any email alert. Unable to resume the ... | `lifecycle_stage` | `LS-04` | `LS-01` | Mismatch on lifecycle_stage: ground_truth 'LS-04' vs AI 'LS-01' |
| `gs_item_005` | App update made SIP modification impossible. Tried pausing for a month but the t... | `root_cause` | `RC-02` | `RC-99` | Model under-confident; defaulted to unclassifiable |
| `gs_item_005` | App update made SIP modification impossible. Tried pausing for a month but the t... | `stop_type` | `ST-02` | `ST-99` | Mismatch on stop_type: ground_truth 'ST-02' vs AI 'ST-99' |
| `gs_item_005` | App update made SIP modification impossible. Tried pausing for a month but the t... | `lifecycle_stage` | `LS-02` | `LS-99` | Mismatch on lifecycle_stage: ground_truth 'LS-02' vs AI 'LS-99' |
| `gs_item_005` | App update made SIP modification impossible. Tried pausing for a month but the t... | `stated_intent` | `pause` | `unknown` | Mismatch on stated_intent: ground_truth 'pause' vs AI 'unknown' |
| `gs_item_005` | App update made SIP modification impossible. Tried pausing for a month but the t... | `actual_action` | `active` | `unknown` | Mismatch on actual_action: ground_truth 'active' vs AI 'unknown' |
| `gs_item_006` | Payment gateway failed twice during SIP instalment debit. Money debited from ban... | `root_cause` | `RC-02` | `RC-99` | Model under-confident; defaulted to unclassifiable |
| `gs_item_006` | Payment gateway failed twice during SIP instalment debit. Money debited from ban... | `stop_type` | `ST-03` | `ST-99` | Mismatch on stop_type: ground_truth 'ST-03' vs AI 'ST-99' |
| `gs_item_006` | Payment gateway failed twice during SIP instalment debit. Money debited from ban... | `lifecycle_stage` | `LS-01` | `LS-99` | Mismatch on lifecycle_stage: ground_truth 'LS-01' vs AI 'LS-99' |
| `gs_item_006` | Payment gateway failed twice during SIP instalment debit. Money debited from ban... | `stated_intent` | `neutral` | `unknown` | Mismatch on stated_intent: ground_truth 'neutral' vs AI 'unknown' |
| `gs_item_006` | Payment gateway failed twice during SIP instalment debit. Money debited from ban... | `actual_action` | `active` | `unknown` | Mismatch on actual_action: ground_truth 'active' vs AI 'unknown' |
| `gs_item_007` | KYC rejected 3 times for signature mismatch. Unable to complete first SIP debit. | `stop_type` | `ST-01` | `ST-03` | Mismatch on stop_type: ground_truth 'ST-01' vs AI 'ST-03' |
| `gs_item_007` | KYC rejected 3 times for signature mismatch. Unable to complete first SIP debit. | `stated_intent` | `continue` | `neutral` | Mismatch on stated_intent: ground_truth 'continue' vs AI 'neutral' |
| `gs_item_007` | KYC rejected 3 times for signature mismatch. Unable to complete first SIP debit. | `actual_action` | `unknown` | `active` | Mismatch on actual_action: ground_truth 'unknown' vs AI 'active' |
| `gs_item_008` | Invested in midcap fund for 5 months. Calculator promised 15% return but portfol... | `stop_type` | `ST-02` | `ST-03` | Mismatch on stop_type: ground_truth 'ST-02' vs AI 'ST-03' |
| `gs_item_008` | Invested in midcap fund for 5 months. Calculator promised 15% return but portfol... | `actual_action` | `cancelled` | `active` | Mismatch on actual_action: ground_truth 'cancelled' vs AI 'active' |
| `gs_item_009` | YouTube finfluencer recommended this flexi cap fund claiming 20% guaranteed retu... | `stop_type` | `ST-02` | `ST-03` | Mismatch on stop_type: ground_truth 'ST-02' vs AI 'ST-03' |
| `gs_item_009` | YouTube finfluencer recommended this flexi cap fund claiming 20% guaranteed retu... | `lifecycle_stage` | `LS-01` | `LS-02` | Mismatch on lifecycle_stage: ground_truth 'LS-01' vs AI 'LS-02' |
| `gs_item_010` | Nifty dropped 600 points last week and my fund NAV fell. Scared of losing more c... | `lifecycle_stage` | `LS-01` | `LS-02` | Mismatch on lifecycle_stage: ground_truth 'LS-01' vs AI 'LS-02' |
| `gs_item_011` | Expecting 12% in 3 months was my mistake, but returns are too low compared to FD... | `stop_type` | `ST-02` | `ST-03` | Mismatch on stop_type: ground_truth 'ST-02' vs AI 'ST-03' |
| `gs_item_011` | Expecting 12% in 3 months was my mistake, but returns are too low compared to FD... | `lifecycle_stage` | `LS-01` | `LS-02` | Mismatch on lifecycle_stage: ground_truth 'LS-01' vs AI 'LS-02' |
| `gs_item_011` | Expecting 12% in 3 months was my mistake, but returns are too low compared to FD... | `actual_action` | `cancelled` | `active` | Mismatch on actual_action: ground_truth 'cancelled' vs AI 'active' |
| `gs_item_012` | Laid off from tech company last week. Pausing my 20k SIP until I secure another ... | `root_cause` | `RC-04` | `RC-99` | Model under-confident; defaulted to unclassifiable |
| `gs_item_012` | Laid off from tech company last week. Pausing my 20k SIP until I secure another ... | `stop_type` | `ST-02` | `ST-99` | Mismatch on stop_type: ground_truth 'ST-02' vs AI 'ST-99' |
| `gs_item_012` | Laid off from tech company last week. Pausing my 20k SIP until I secure another ... | `lifecycle_stage` | `LS-03` | `LS-99` | Mismatch on lifecycle_stage: ground_truth 'LS-03' vs AI 'LS-99' |
| `gs_item_012` | Laid off from tech company last week. Pausing my 20k SIP until I secure another ... | `stated_intent` | `continue` | `unknown` | Mismatch on stated_intent: ground_truth 'continue' vs AI 'unknown' |
| `gs_item_012` | Laid off from tech company last week. Pausing my 20k SIP until I secure another ... | `actual_action` | `paused` | `unknown` | Mismatch on actual_action: ground_truth 'paused' vs AI 'unknown' |
| `gs_item_014` | Salary reduced by 25% due to company restructuring. Need to cut discretionary in... | `root_cause` | `RC-04` | `RC-03` | Mismatch on root_cause: ground_truth 'RC-04' vs AI 'RC-03' |
| `gs_item_014` | Salary reduced by 25% due to company restructuring. Need to cut discretionary in... | `stop_type` | `ST-02` | `ST-03` | Mismatch on stop_type: ground_truth 'ST-02' vs AI 'ST-03' |
| `gs_item_014` | Salary reduced by 25% due to company restructuring. Need to cut discretionary in... | `lifecycle_stage` | `LS-99` | `LS-02` | Mismatch on lifecycle_stage: ground_truth 'LS-99' vs AI 'LS-02' |
| `gs_item_014` | Salary reduced by 25% due to company restructuring. Need to cut discretionary in... | `actual_action` | `cancelled` | `active` | Mismatch on actual_action: ground_truth 'cancelled' vs AI 'active' |
| `gs_item_016` | Switching from active large cap fund to Nifty 50 direct index fund on the same G... | `lifecycle_stage` | `LS-03` | `LS-04` | Mismatch on lifecycle_stage: ground_truth 'LS-03' vs AI 'LS-04' |
| `gs_item_016` | Switching from active large cap fund to Nifty 50 direct index fund on the same G... | `stated_intent` | `continue` | `stop` | Inferred intent to stop from past cancellation action |
| `gs_item_018` | I am confused about NAV. If NAV increases does my profit decrease? Nobody explai... | `root_cause` | `RC-06` | `RC-99` | Model under-confident; defaulted to unclassifiable |
| `gs_item_018` | I am confused about NAV. If NAV increases does my profit decrease? Nobody explai... | `stop_type` | `ST-03` | `ST-99` | Mismatch on stop_type: ground_truth 'ST-03' vs AI 'ST-99' |
| `gs_item_018` | I am confused about NAV. If NAV increases does my profit decrease? Nobody explai... | `lifecycle_stage` | `LS-01` | `LS-99` | Mismatch on lifecycle_stage: ground_truth 'LS-01' vs AI 'LS-99' |
| `gs_item_018` | I am confused about NAV. If NAV increases does my profit decrease? Nobody explai... | `stated_intent` | `neutral` | `unknown` | Mismatch on stated_intent: ground_truth 'neutral' vs AI 'unknown' |
| `gs_item_018` | I am confused about NAV. If NAV increases does my profit decrease? Nobody explai... | `actual_action` | `active` | `unknown` | Mismatch on actual_action: ground_truth 'active' vs AI 'unknown' |
| `gs_item_019` | Did not realize market fluctuation causes NAV to go down temporarily. Thought mu... | `root_cause` | `RC-06` | `RC-99` | Model under-confident; defaulted to unclassifiable |
| `gs_item_019` | Did not realize market fluctuation causes NAV to go down temporarily. Thought mu... | `stop_type` | `ST-03` | `ST-99` | Mismatch on stop_type: ground_truth 'ST-03' vs AI 'ST-99' |
| `gs_item_019` | Did not realize market fluctuation causes NAV to go down temporarily. Thought mu... | `lifecycle_stage` | `LS-01` | `LS-99` | Mismatch on lifecycle_stage: ground_truth 'LS-01' vs AI 'LS-99' |
| `gs_item_019` | Did not realize market fluctuation causes NAV to go down temporarily. Thought mu... | `stated_intent` | `neutral` | `unknown` | Mismatch on stated_intent: ground_truth 'neutral' vs AI 'unknown' |
| `gs_item_019` | Did not realize market fluctuation causes NAV to go down temporarily. Thought mu... | `actual_action` | `active` | `unknown` | Mismatch on actual_action: ground_truth 'active' vs AI 'unknown' |
| `gs_item_020` | Colleague convinced me that mutual funds are crashing and urged me to withdraw e... | `root_cause` | `RC-07` | `RC-99` | Model under-confident; defaulted to unclassifiable |
| `gs_item_020` | Colleague convinced me that mutual funds are crashing and urged me to withdraw e... | `stop_type` | `ST-02` | `ST-99` | Mismatch on stop_type: ground_truth 'ST-02' vs AI 'ST-99' |
| `gs_item_020` | Colleague convinced me that mutual funds are crashing and urged me to withdraw e... | `lifecycle_stage` | `LS-02` | `LS-99` | Mismatch on lifecycle_stage: ground_truth 'LS-02' vs AI 'LS-99' |
| `gs_item_020` | Colleague convinced me that mutual funds are crashing and urged me to withdraw e... | `stated_intent` | `stop` | `unknown` | Mismatch on stated_intent: ground_truth 'stop' vs AI 'unknown' |
| `gs_item_020` | Colleague convinced me that mutual funds are crashing and urged me to withdraw e... | `actual_action` | `active` | `unknown` | Mismatch on actual_action: ground_truth 'active' vs AI 'unknown' |
| `gs_item_021` | Finfluencer said small caps are overheated and advised shifting to debt funds. C... | `root_cause` | `RC-07` | `RC-03` | Finfluencer advice confused with direct calculator mismatch |
| `gs_item_022` | Investing in Parag Parikh Flexi Cap for 18 months. Rupee cost averaging is worki... | `root_cause` | `RC-99` | `RC-02` | Mismatch on root_cause: ground_truth 'RC-99' vs AI 'RC-02' |
| `gs_item_022` | Investing in Parag Parikh Flexi Cap for 18 months. Rupee cost averaging is worki... | `lifecycle_stage` | `LS-04` | `LS-01` | Mismatch on lifecycle_stage: ground_truth 'LS-04' vs AI 'LS-01' |
| `gs_item_022` | Investing in Parag Parikh Flexi Cap for 18 months. Rupee cost averaging is worki... | `stated_intent` | `continue` | `neutral` | Mismatch on stated_intent: ground_truth 'continue' vs AI 'neutral' |
| `gs_item_025` | Just started researching personal finance. What is the difference between direct... | `lifecycle_stage` | `LS-00` | `LS-99` | Mismatch on lifecycle_stage: ground_truth 'LS-00' vs AI 'LS-99' |
| `gs_item_025` | Just started researching personal finance. What is the difference between direct... | `stated_intent` | `neutral` | `unknown` | Mismatch on stated_intent: ground_truth 'neutral' vs AI 'unknown' |

---

## 4. PM & Researcher Sign-off

- **Evaluation Status:** **ITERATION REQUIRED**
- **Next Steps:** Apply prompt refinement and re-run comparison
