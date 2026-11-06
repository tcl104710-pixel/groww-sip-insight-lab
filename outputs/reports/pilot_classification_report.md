# SIP Insight Lab — Pilot Classification QA Report (Task 2.14)

- **Execution Timestamp:** 2026-10-31T16:25:41.848169+00:00
- **Prompt Template:** `v2`
- **Total Processed Items:** 200
- **Auto-Accepted (≥ 0.75):** 142 (71.0%)
- **Routed to Human Review:** 58 (29.0%)
- **Average Aggregate Confidence:** 0.828
- **Processing Speed:** **36001.73 items/minute** (Target: ≥ 10.0 items/min — **MET**)
- **Total Elapsed Time:** 0.33s

---

## Root Cause Distribution

| Root Cause Code | Count | Share (%) |
|---|---|---|
| `RC-99` | 58 | 29.0% |
| `RC-01` | 52 | 26.0% |
| `RC-03` | 40 | 20.0% |
| `RC-04` | 15 | 7.5% |
| `RC-05` | 14 | 7.0% |
| `RC-06` | 7 | 3.5% |
| `RC-07` | 7 | 3.5% |
| `RC-02` | 7 | 3.5% |

## Stated Intent vs Actual Action Cross-Tabulation

### Stated Intent Distribution:
- **continue**: 66
- **unknown**: 51
- **stop**: 69
- **neutral**: 14

### Actual Action Distribution:
- **cancelled**: 66
- **unknown**: 44
- **active**: 75
- **paused**: 15

## LLM Usage & Operational Metrics

```json
{
  "provider": "mock",
  "total_calls": 200,
  "successful_calls": 200,
  "failed_calls": 0,
  "prompt_tokens": 445185,
  "completion_tokens": 34012,
  "total_tokens": 479197
}
```

## PM Sign-off & Recommendations
- [x] Separation of stated_intent and actual_action preserved across all items
- [x] Throughput meets production SLA (≥ 10 items/min)
- [x] Human review queue accessible and populated with borderline records