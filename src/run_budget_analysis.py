
"""Run household spending and budget analysis."""

import csv
import sys
from pathlib import Path

from src.budgets import (
    calculate_household_spending,
    compare_budgets,
)


def read_csv(path):
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def write_csv(path, rows, fieldnames):
    """Write a CSV file, including headers when there are no rows."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    root = Path(__file__).resolve().parent.parent
    data_dir = root / "data" / "generated"

    transactions_path = data_dir / "transactions.csv"
    budgets_path = data_dir / "budgets.csv"
    categories_path = data_dir / "categories.csv"

    for path in (transactions_path, budgets_path):
        if not path.exists():
            print(f"Missing required file: {path}")
            sys.exit(1)

    transactions = read_csv(transactions_path)
    budgets = read_csv(budgets_path)

    # Load valid categories when the categories file exists.
    valid_category_ids = None

    if categories_path.exists():
        category_rows = read_csv(categories_path)
        valid_category_ids = {
            row.get("category_id", "")
            for row in category_rows
            if row.get("category_id", "")
            and row.get("is_active", "true").strip().lower()
            not in {"false", "0", "no"}
        }

    spending, excluded, transaction_exceptions = (
        calculate_household_spending(transactions)
    )

    comparisons = compare_budgets(
        spending,
        budgets,
        valid_category_ids=valid_category_ids,
    )

    # Include over-budget and invalid-budget cases in the exceptions report.
    budget_exceptions = []

    for row in comparisons:
        if row["status"] in {
            "OVER_BUDGET",
            "REVIEW_INVALID_BUDGET",
        }:
            budget_exceptions.append({
                "transaction_id": "",
                "budget_id": row.get("budget_id", ""),
                "user_id": row.get("user_id", ""),
                "month": row.get("month", ""),
                "category_id": row.get("category_id", ""),
                "reason": row.get("exception_reason", "")
                or row["status"],
            })

    all_exceptions = []

    for exception in transaction_exceptions:
        all_exceptions.append({
            "transaction_id": exception.get("transaction_id", ""),
            "budget_id": "",
            "user_id": "",
            "month": "",
            "category_id": "",
            "reason": exception.get("reason", ""),
        })

    all_exceptions.extend(budget_exceptions)

    spending_path = data_dir / "household_spending.csv"
    comparison_path = data_dir / "budget_comparison.csv"
    exception_path = data_dir / "budget_exceptions.csv"

    write_csv(
        spending_path,
        spending,
        ["user_id", "month", "category_id", "net_spending"],
    )

    write_csv(
        comparison_path,
        comparisons,
        [
            "budget_id",
            "user_id",
            "month",
            "category_id",
            "budget_amount",
            "actual_spending",
            "remaining_budget",
            "status",
            "exception_reason",
        ],
    )

    write_csv(
        exception_path,
        all_exceptions,
        [
            "transaction_id",
            "budget_id",
            "user_id",
            "month",
            "category_id",
            "reason",
        ],
    )

    statuses = {}
    for row in comparisons:
        status = row["status"]
        statuses[status] = statuses.get(status, 0) + 1

    print("\n=== Household Budget Analysis ===")
    print(f"Transactions processed: {len(transactions):,}")
    print(f"Spending summaries: {len(spending):,}")
    print(f"Budgets compared: {len(comparisons):,}")
    print(f"Exceptions flagged: {len(all_exceptions):,}")
    print(f"Excluded transactions: {sum(excluded.values()):,}")

    print("\nExcluded transaction breakdown:")
    for reason, count in sorted(excluded.items()):
        print(f"  {reason}: {count:,}")

    print("\nBudget status breakdown:")
    for status, count in sorted(statuses.items()):
        print(f"  {status}: {count:,}")

    print(f"\nSpending report: {spending_path}")
    print(f"Budget comparison: {comparison_path}")
    print(f"Exceptions report: {exception_path}")


if __name__ == "__main__":
    main()
