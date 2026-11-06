# SIP Insight Lab — Quality Assurance Report (V2)

- **Evaluation Timestamp:** 2026-11-01T05:14:52.368140+00:00
- **Prompt Version Tested:** `v2`
- **Golden Set Size:** 25 items
- **Exact-Match Overall Accuracy:** **80.0%** (Target: ≥ 80% — **PASS**)
- **All Per-Field F1 ≥ 0.75:** **YES (PASS)**

---

## 1. Per-Field Performance Summary

| Taxonomy Field | Accuracy | Macro F1 | Weighted F1 | Target (≥0.75) | Status |
|---|---|---|---|---|---|
| `root_cause` | 100.0% | 1.000 | **1.000** | ≥ 0.75 | **PASS** |
| `stop_type` | 100.0% | 1.000 | **1.000** | ≥ 0.75 | **PASS** |
| `lifecycle_stage` | 80.0% | 0.847 | **0.789** | ≥ 0.75 | **PASS** |
| `stated_intent` | 100.0% | 1.000 | **1.000** | ≥ 0.75 | **PASS** |
| `actual_action` | 100.0% | 1.000 | **1.000** | ≥ 0.75 | **PASS** |

---

## 2. Root Cause (RC) Per-Class Performance Breakdown

| Root Cause Code | Support | Precision | Recall | F1 Score |
|---|---|---|---|---|
| `RC-01` | 4 | 1.000 | 1.000 | **1.000** |
| `RC-02` | 3 | 1.000 | 1.000 | **1.000** |
| `RC-03` | 4 | 1.000 | 1.000 | **1.000** |
| `RC-04` | 3 | 1.000 | 1.000 | **1.000** |
| `RC-05` | 2 | 1.000 | 1.000 | **1.000** |
| `RC-06` | 3 | 1.000 | 1.000 | **1.000** |
| `RC-07` | 2 | 1.000 | 1.000 | **1.000** |
| `RC-99` | 4 | 1.000 | 1.000 | **1.000** |

---

## 3. Error Analysis and Misclassifications

Total field mismatches detected: **5**

| Item ID | Snippet | Field | Ground Truth | AI Prediction | Diagnosis |
|---|---|---|---|---|---|
| `gs_item_005` | App update made SIP modification impossible. Tried pausing for a month but the t... | `lifecycle_stage` | `LS-02` | `LS-01` | Mismatch on lifecycle_stage: ground_truth 'LS-02' vs AI 'LS-01' |
| `gs_item_011` | Expecting 12% in 3 months was my mistake, but returns are too low compared to FD... | `lifecycle_stage` | `LS-01` | `LS-02` | Mismatch on lifecycle_stage: ground_truth 'LS-01' vs AI 'LS-02' |
| `gs_item_020` | Colleague convinced me that mutual funds are crashing and urged me to withdraw e... | `lifecycle_stage` | `LS-02` | `LS-01` | Mismatch on lifecycle_stage: ground_truth 'LS-02' vs AI 'LS-01' |
| `gs_item_021` | Finfluencer said small caps are overheated and advised shifting to debt funds. C... | `lifecycle_stage` | `LS-02` | `LS-01` | Mismatch on lifecycle_stage: ground_truth 'LS-02' vs AI 'LS-01' |
| `gs_item_023` | Auto debit on 1st of every month without fail. Set it and forget it. Excellent d... | `lifecycle_stage` | `LS-03` | `LS-01` | Mismatch on lifecycle_stage: ground_truth 'LS-03' vs AI 'LS-01' |

---

## 4. PM & Researcher Sign-off

- **Evaluation Status:** **APPROVED**
- **Next Steps:** Ready for Synthesis & Hypothesis Engine (Phase 4)
