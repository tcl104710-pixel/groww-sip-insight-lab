"""
SIP Insight Lab — QA Comparison Module (Task 3.3)
==================================================
Compares AI classification outputs against human ground truth (Golden Set).
Calculates:
  - Exact-match Overall Accuracy (target ≥ 80%)
  - Per-field Precision, Recall, and F1 scores (target ≥ 0.75 per field)
  - Confusion matrices for categorical fields (root_cause, stop_type, etc.)
  - Granular error analysis per misclassified item

Usage:
    from src.qa.comparator import QAComparator
    comparator = QAComparator(conn)
    metrics = comparator.evaluate(predictions)
    print(metrics.summary())
"""

import json
import logging
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

EVALUATED_FIELDS = [
    "root_cause",
    "stop_type",
    "lifecycle_stage",
    "stated_intent",
    "actual_action",
]


@dataclass
class FieldMetric:
    field_name: str
    accuracy: float
    precision_macro: float
    recall_macro: float
    f1_macro: float
    f1_weighted: float
    class_metrics: Dict[str, Dict[str, float]]
    confusion_matrix: Dict[str, Dict[str, int]]
    meets_target: bool  # f1_weighted >= 0.75


@dataclass
class Misclassification:
    item_id: str
    text_snippet: str
    field_name: str
    ground_truth: str
    predicted: str
    confidence: float
    possible_cause: str


@dataclass
class QAEvaluationResult:
    timestamp: str
    total_golden_items: int
    exact_match_accuracy: float
    meets_overall_target: bool  # accuracy >= 0.80
    field_metrics: Dict[str, FieldMetric]
    all_fields_meet_target: bool
    errors: List[Misclassification]
    prompt_version: str = "v1"

    def summary(self) -> Dict[str, Any]:
        return {
            "overall_accuracy": round(self.exact_match_accuracy, 4),
            "meets_overall_target": self.meets_overall_target,
            "all_fields_meet_target": self.all_fields_meet_target,
            "field_f1_scores": {
                f: round(m.f1_weighted, 4) for f, m in self.field_metrics.items()
            },
            "error_count": len(self.errors),
        }


class QAComparator:
    """
    Evaluates AI predictions against the ground truth golden set.
    """

    def __init__(
        self,
        conn: Optional[sqlite3.Connection] = None,
        target_overall_accuracy: float = 0.80,
        target_field_f1: float = 0.75,
    ):
        self.conn = conn
        self.target_overall_accuracy = target_overall_accuracy
        self.target_field_f1 = target_field_f1

    def load_golden_set_from_db(self) -> Dict[str, Tuple[str, dict]]:
        """
        Load golden set items from SQLite database.
        Returns: {item_id: (cleaned_text, ground_truth_dict)}
        """
        if not self.conn:
            raise ValueError("Database connection required to load golden set from DB.")

        cursor = self.conn.cursor()
        query = """
            SELECT g.item_id, c.cleaned_text, g.human_labels
            FROM golden_set g
            JOIN cleaned_item c ON g.item_id = c.item_id;
        """
        rows = cursor.execute(query).fetchall()
        result = {}
        for item_id, text, labels_json in rows:
            labels = json.loads(labels_json) if isinstance(labels_json, str) else labels_json
            result[item_id] = (text, labels)
        return result

    def load_golden_set_from_csv(
        self,
        items_csv: str = "./golden_set/items.csv",
        labels_csv: str = "./golden_set/labels.csv",
    ) -> Dict[str, Tuple[str, dict]]:
        """
        Load golden set items from CSV files.
        """
        import csv

        texts = {}
        with open(items_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                texts[row["item_id"]] = row["text"]

        result = {}
        with open(labels_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                item_id = row["item_id"]
                rec = json.loads(row["reconciled_labels"])
                result[item_id] = (texts.get(item_id, ""), rec)

        return result

    def evaluate(
        self,
        predictions: Dict[str, dict],
        golden_set: Optional[Dict[str, Tuple[str, dict]]] = None,
        prompt_version: str = "v1",
    ) -> QAEvaluationResult:
        """
        Compare predictions dict against golden set ground truth.

        Args:
            predictions: {item_id: parsed_classification_dict}
            golden_set: Optional ground truth override; defaults to DB golden set.
            prompt_version: Identifier of prompt template tested.
        """
        if golden_set is None:
            golden_set = self.load_golden_set_from_db()

        total_items = len(golden_set)
        if total_items == 0:
            raise ValueError("Golden set is empty; cannot evaluate QA metrics.")

        exact_matches = 0
        all_errors: List[Misclassification] = []
        field_eval_data: Dict[str, Dict[str, list]] = {
            f: {"y_true": [], "y_pred": [], "items": []} for f in EVALUATED_FIELDS
        }

        for item_id, (text, y_true_labels) in golden_set.items():
            y_pred_labels = predictions.get(item_id, {})

            # Check exact match across all 5 key fields
            is_exact = True
            for f in EVALUATED_FIELDS:
                true_val = str(y_true_labels.get(f, "")).strip()
                pred_val = str(y_pred_labels.get(f, "")).strip()

                field_eval_data[f]["y_true"].append(true_val)
                field_eval_data[f]["y_pred"].append(pred_val)
                field_eval_data[f]["items"].append((item_id, text, true_val, pred_val))

                if true_val != pred_val:
                    is_exact = False
                    conf = float(y_pred_labels.get("confidence_score", 0.0))
                    all_errors.append(
                        Misclassification(
                            item_id=item_id,
                            text_snippet=text[:80] + ("..." if len(text) > 80 else ""),
                            field_name=f,
                            ground_truth=true_val,
                            predicted=pred_val,
                            confidence=conf,
                            possible_cause=self._diagnose_error(f, true_val, pred_val),
                        )
                    )

            if is_exact:
                exact_matches += 1

        overall_accuracy = exact_matches / total_items
        meets_overall = overall_accuracy >= self.target_overall_accuracy

        # Calculate per-field precision, recall, F1, confusion matrix
        field_metrics: Dict[str, FieldMetric] = {}
        all_fields_meet = True

        for f in EVALUATED_FIELDS:
            y_true = field_eval_data[f]["y_true"]
            y_pred = field_eval_data[f]["y_pred"]
            f_metric = self._compute_field_metrics(f, y_true, y_pred)
            field_metrics[f] = f_metric
            if not f_metric.meets_target:
                all_fields_meet = False

        return QAEvaluationResult(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_golden_items=total_items,
            exact_match_accuracy=overall_accuracy,
            meets_overall_target=meets_overall,
            field_metrics=field_metrics,
            all_fields_meet_target=all_fields_meet,
            errors=all_errors,
            prompt_version=prompt_version,
        )

    def _compute_field_metrics(
        self, field_name: str, y_true: List[str], y_pred: List[str]
    ) -> FieldMetric:
        """
        Compute precision, recall, F1 (macro and weighted), and confusion matrix.
        """
        total = len(y_true)
        correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
        accuracy = correct / max(total, 1)

        # Classes present in ground truth or predictions
        classes = sorted(list(set(y_true) | set(y_pred)))

        # Build confusion matrix: matrix[true_class][pred_class]
        confusion: Dict[str, Dict[str, int]] = {c1: {c2: 0 for c2 in classes} for c1 in classes}
        for t, p in zip(y_true, y_pred):
            confusion[t][p] = confusion[t].get(p, 0) + 1

        # Per-class metrics
        class_metrics = {}
        f1_list = []
        prec_list = []
        rec_list = []
        weights = []

        for c in classes:
            tp = confusion[c].get(c, 0)
            fp = sum(confusion[other].get(c, 0) for other in classes if other != c)
            fn = sum(confusion[c].get(other, 0) for other in classes if other != c)
            support = tp + fn

            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

            class_metrics[c] = {
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1": round(f1, 4),
                "support": support,
            }

            if support > 0:
                f1_list.append(f1)
                prec_list.append(prec)
                rec_list.append(rec)
                weights.append(support)

        # Macro average
        f1_macro = sum(f1_list) / max(len(f1_list), 1)
        prec_macro = sum(prec_list) / max(len(prec_list), 1)
        rec_macro = sum(rec_list) / max(len(rec_list), 1)

        # Weighted average
        total_support = sum(weights)
        f1_weighted = (
            sum(f1 * w for f1, w in zip(f1_list, weights)) / total_support
            if total_support > 0
            else 0.0
        )

        meets_target = f1_weighted >= self.target_field_f1

        return FieldMetric(
            field_name=field_name,
            accuracy=round(accuracy, 4),
            precision_macro=round(prec_macro, 4),
            recall_macro=round(rec_macro, 4),
            f1_macro=round(f1_macro, 4),
            f1_weighted=round(f1_weighted, 4),
            class_metrics=class_metrics,
            confusion_matrix=confusion,
            meets_target=meets_target,
        )

    def _diagnose_error(self, field_name: str, true_val: str, pred_val: str) -> str:
        """Provide automated diagnosis of common misclassifications."""
        if field_name == "root_cause":
            if true_val == "RC-01" and pred_val == "RC-02":
                return "Mandate/debit failure confused with app payment UX failure"
            if true_val == "RC-03" and pred_val == "RC-06":
                return "Return disappointment confused with volatility knowledge gap"
            if true_val == "RC-07" and pred_val == "RC-03":
                return "Finfluencer advice confused with direct calculator mismatch"
            if true_val == "RC-05" and pred_val == "RC-04":
                return "Goal achievement confused with income constraint"
            if pred_val == "RC-99":
                return "Model under-confident; defaulted to unclassifiable"
        elif field_name == "stated_intent":
            if true_val == "continue" and pred_val == "stop":
                return "Inferred intent to stop from past cancellation action"
        elif field_name == "stop_type":
            if true_val == "ST-01" and pred_val == "ST-02":
                return "Involuntary debit lapse misclassified as deliberate exit"
        return f"Mismatch on {field_name}: ground_truth '{true_val}' vs AI '{pred_val}'"

    def generate_report_markdown(
        self, result: QAEvaluationResult, title: str = "QA Evaluation Report"
    ) -> str:
        """
        Generate comprehensive, human-readable markdown QA report.
        """
        lines = [
            f"# SIP Insight Lab — {title}",
            "",
            f"- **Evaluation Timestamp:** {result.timestamp}",
            f"- **Prompt Version Tested:** `{result.prompt_version}`",
            f"- **Golden Set Size:** {result.total_golden_items} items",
            f"- **Exact-Match Overall Accuracy:** **{result.exact_match_accuracy * 100:.1f}%** "
            f"(Target: ≥ {self.target_overall_accuracy * 100:.0f}% — **{'PASS' if result.meets_overall_target else 'FAIL'}**)",
            f"- **All Per-Field F1 ≥ {self.target_field_f1:.2f}:** **{'YES (PASS)' if result.all_fields_meet_target else 'NO (ACTION REQUIRED)'}**",
            "",
            "---",
            "",
            "## 1. Per-Field Performance Summary",
            "",
            "| Taxonomy Field | Accuracy | Macro F1 | Weighted F1 | Target (≥0.75) | Status |",
            "|---|---|---|---|---|---|",
        ]

        for f in EVALUATED_FIELDS:
            m = result.field_metrics[f]
            status = "PASS" if m.meets_target else "FAIL"
            lines.append(
                f"| `{m.field_name}` | {m.accuracy * 100:.1f}% | {m.f1_macro:.3f} | **{m.f1_weighted:.3f}** | ≥ {self.target_field_f1:.2f} | **{status}** |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## 2. Root Cause (RC) Per-Class Performance Breakdown",
            "",
            "| Root Cause Code | Support | Precision | Recall | F1 Score |",
            "|---|---|---|---|---|",
        ])

        rc_metric = result.field_metrics.get("root_cause")
        if rc_metric:
            for cls_code, cdata in sorted(rc_metric.class_metrics.items()):
                if cdata["support"] > 0:
                    lines.append(
                        f"| `{cls_code}` | {cdata['support']} | {cdata['precision']:.3f} | {cdata['recall']:.3f} | **{cdata['f1']:.3f}** |"
                    )

        lines.extend([
            "",
            "---",
            "",
            "## 3. Error Analysis and Misclassifications",
            "",
        ])

        if not result.errors:
            lines.append("✓ **Zero misclassifications detected.** All fields matched human ground truth perfectly.")
        else:
            lines.append(f"Total field mismatches detected: **{len(result.errors)}**\n")
            lines.append("| Item ID | Snippet | Field | Ground Truth | AI Prediction | Diagnosis |")
            lines.append("|---|---|---|---|---|---|")
            for err in result.errors:
                snip = err.text_snippet.replace("|", "\\|").replace("\n", " ")
                lines.append(
                    f"| `{err.item_id}` | {snip} | `{err.field_name}` | `{err.ground_truth}` | `{err.predicted}` | {err.possible_cause} |"
                )

        lines.extend([
            "",
            "---",
            "",
            "## 4. PM & Researcher Sign-off",
            "",
            f"- **Evaluation Status:** **{'APPROVED' if (result.meets_overall_target and result.all_fields_meet_target) else 'ITERATION REQUIRED'}**",
            f"- **Next Steps:** {'Ready for Synthesis & Hypothesis Engine (Phase 4)' if (result.meets_overall_target and result.all_fields_meet_target) else 'Apply prompt refinement and re-run comparison'}",
            "",
        ])

        return "\n".join(lines)


if __name__ == "__main__":
    from src.db.schema import init_db

    conn = init_db()
    comparator = QAComparator(conn)
    golden = comparator.load_golden_set_from_db()
    print(f"Loaded {len(golden)} golden items from DB.")
