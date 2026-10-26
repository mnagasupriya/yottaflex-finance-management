
"""Evaluate transaction categorization against independent ground truth."""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def read_csv(path):
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def safe_divide(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def evaluate(predictions, ground_truth):
    """Calculate classification metrics and per-category results."""

    prediction_by_id = {
        row["transaction_id"]: row
        for row in predictions
    }
    truth_by_id = {
        row["transaction_id"]: row
        for row in ground_truth
    }

    missing_predictions = set(truth_by_id) - set(prediction_by_id)
    extra_predictions = set(prediction_by_id) - set(truth_by_id)

    if missing_predictions:
        raise ValueError(
            f"{len(missing_predictions)} ground-truth transactions "
            "have no prediction."
        )

    categories = sorted({
        row["expected_category_id"]
        for row in ground_truth
        if row.get("expected_category_id")
    })

    confusion = Counter()
    expected_counts = Counter()
    predicted_counts = Counter()
    correct_counts = Counter()
    issue_counts = Counter()
    decision_counts = Counter()

    correct = 0
    classified = 0

    for transaction_id, truth in truth_by_id.items():
        prediction = prediction_by_id[transaction_id]

        expected = truth.get("expected_category_id", "").strip()
        predicted = prediction.get("predicted_category_id", "").strip()
        predicted = predicted or "UNCLASSIFIED"

        expected_counts[expected] += 1
        predicted_counts[predicted] += 1
        confusion[(expected, predicted)] += 1

        issue_counts[truth.get("issue_type", "unknown")] += 1
        decision_counts[
            truth.get("expected_decision", "unspecified")
        ] += 1

        if predicted != "UNCLASSIFIED":
            classified += 1

        if expected == predicted:
            correct += 1
            correct_counts[expected] += 1

    total = len(ground_truth)
    accuracy = safe_divide(correct, total)
    coverage = safe_divide(classified, total)

    per_category = {}
    precisions = []
    recalls = []
    f1_scores = []

    for category in categories:
        true_positive = correct_counts[category]
        predicted_positive = predicted_counts[category]
        actual_positive = expected_counts[category]

        precision = safe_divide(true_positive, predicted_positive)
        recall = safe_divide(true_positive, actual_positive)
        f1 = safe_divide(
            2 * precision * recall,
            precision + recall
        )

        per_category[category] = {
            "support": actual_positive,
            "predicted_count": predicted_positive,
            "correct": true_positive,
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1_score": round(f1, 6),
        }

        precisions.append(precision)
        recalls.append(recall)
        f1_scores.append(f1)

    macro_precision = safe_divide(sum(precisions), len(precisions))
    macro_recall = safe_divide(sum(recalls), len(recalls))
    macro_f1 = safe_divide(sum(f1_scores), len(f1_scores))

    return {
        "summary": {
            "ground_truth_rows": total,
            "prediction_rows": len(predictions),
            "matched_transaction_ids": total - len(missing_predictions),
            "extra_prediction_ids": len(extra_predictions),
            "correct_predictions": correct,
            "incorrect_predictions": total - correct,
            "accuracy": round(accuracy, 6),
            "coverage": round(coverage, 6),
            "classified_transactions": classified,
            "unclassified_transactions": total - classified,
            "macro_precision": round(macro_precision, 6),
            "macro_recall": round(macro_recall, 6),
            "macro_f1": round(macro_f1, 6),
        },
        "per_category": per_category,
        "issue_type_counts": dict(issue_counts),
        "expected_decision_counts": dict(decision_counts),
        "confusion_matrix": {
            expected: {
                predicted: confusion[(expected, predicted)]
                for predicted in sorted(
                    set(categories) | {"UNCLASSIFIED"}
                )
                if confusion[(expected, predicted)]
            }
            for expected in categories
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate categorized transactions against ground truth."
    )
    parser.add_argument(
        "--predictions",
        default="data/generated/categorized_transactions.csv"
    )
    parser.add_argument(
        "--ground-truth",
        default="data/ground_truth/ground_truth.csv"
    )
    parser.add_argument(
        "--report",
        default="docs/evaluation_report.json"
    )
    parser.add_argument(
        "--confusion-csv",
        default="data/generated/category_confusion_matrix.csv"
    )
    args = parser.parse_args()

    predictions = read_csv(Path(args.predictions))
    ground_truth = read_csv(Path(args.ground_truth))

    report = evaluate(predictions, ground_truth)

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    # Export a flat confusion matrix for spreadsheet inspection.
    confusion_rows = []
    for expected, predicted_counts in report["confusion_matrix"].items():
        for predicted, count in predicted_counts.items():
            confusion_rows.append({
                "expected_category_id": expected,
                "predicted_category_id": predicted,
                "count": count,
            })

    confusion_path = Path(args.confusion_csv)
    confusion_path.parent.mkdir(parents=True, exist_ok=True)

    with confusion_path.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "expected_category_id",
                "predicted_category_id",
                "count",
            ],
        )
        writer.writeheader()
        writer.writerows(confusion_rows)

    print("\n=== Categorization Evaluation ===")
    for key, value in report["summary"].items():
        print(f"{key}: {value}")

    print("\nPer-category metrics:")
    for category, metrics in report["per_category"].items():
        print(
            f"{category}: precision={metrics['precision']:.3f}, "
            f"recall={metrics['recall']:.3f}, "
            f"F1={metrics['f1_score']:.3f}, "
            f"support={metrics['support']}"
        )

    print(f"\nJSON report: {report_path}")
    print(f"Confusion matrix: {confusion_path}")


if __name__ == "__main__":
    main()
