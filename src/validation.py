
import argparse
import csv
import json
from collections import Counter
from datetime import date, datetime
from pathlib import Path


def read_csv(path):
    """Read a CSV file as a list of dictionaries."""
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def check_unique(rows, key, table_name, errors):
    """Check that a primary-key column is present and unique."""
    values = [row.get(key, "").strip() for row in rows]

    if any(not value for value in values):
        errors.append(f"{table_name}: blank {key} found.")

    duplicates = [value for value, count in Counter(values).items()
                  if value and count > 1]

    if duplicates:
        errors.append(
            f"{table_name}: {len(duplicates)} duplicate {key} value(s)."
        )


def check_foreign_key(rows, field, valid_ids, table_name, errors,
                      allow_blank=False):
    """Check that foreign-key values reference existing records."""
    for row_number, row in enumerate(rows, start=2):
        value = row.get(field, "").strip()

        if not value and allow_blank:
            continue

        if value not in valid_ids:
            errors.append(
                f"{table_name}, row {row_number}: invalid "
                f"{field} reference '{value}'."
            )


def validate_dataset(data_dir, ground_truth_dir=None,
                     expected_users=None, expected_transactions=None):
    data_dir = Path(data_dir)
    ground_truth_dir = (
        Path(ground_truth_dir)
        if ground_truth_dir
        else data_dir.parent / "ground_truth"
    )

    errors = []
    warnings = []
    counts = {}

    # Load all required input tables.
    filenames = {
        "users": "users.csv",
        "accounts": "accounts.csv",
        "merchants": "merchants.csv",
        "categories": "categories.csv",
        "rules": "category_rules.csv",
        "budgets": "budgets.csv",
        "recurring": "recurring_series.csv",
        "transactions": "transactions.csv",
    }

    tables = {}

    try:
        for table_name, filename in filenames.items():
            tables[table_name] = read_csv(data_dir / filename)
            counts[table_name] = len(tables[table_name])
    except (FileNotFoundError, OSError, csv.Error) as exc:
        return {
            "status": "FAIL",
            "errors": [str(exc)],
            "warnings": warnings,
            "row_counts": counts,
        }

    users = tables["users"]
    accounts = tables["accounts"]
    merchants = tables["merchants"]
    categories = tables["categories"]
    rules = tables["rules"]
    budgets = tables["budgets"]
    recurring = tables["recurring"]
    transactions = tables["transactions"]

    # 1. Primary keys.
    primary_keys = {
        "users": ("user_id", users),
        "accounts": ("account_id", accounts),
        "merchants": ("merchant_id", merchants),
        "categories": ("category_id", categories),
        "rules": ("rule_id", rules),
        "budgets": ("budget_id", budgets),
        "recurring": ("recurring_id", recurring),
        "transactions": ("transaction_id", transactions),
    }

    for table_name, (key, rows) in primary_keys.items():
        check_unique(rows, key, table_name, errors)

    # 2. Foreign keys.
    user_ids = {row["user_id"] for row in users}
    account_ids = {row["account_id"] for row in accounts}
    merchant_ids = {row["merchant_id"] for row in merchants}
    category_ids = {row["category_id"] for row in categories}

    check_foreign_key(accounts, "user_id", user_ids, "accounts", errors)
    check_foreign_key(
        merchants, "default_category_id", category_ids, "merchants", errors
    )
    check_foreign_key(rules, "merchant_id", merchant_ids, "rules", errors)
    check_foreign_key(rules, "category_id", category_ids, "rules", errors)
    check_foreign_key(budgets, "user_id", user_ids, "budgets", errors)
    check_foreign_key(budgets, "category_id", category_ids, "budgets", errors)
    check_foreign_key(recurring, "user_id", user_ids, "recurring", errors)
    check_foreign_key(recurring, "account_id", account_ids, "recurring", errors)
    check_foreign_key(recurring, "merchant_id", merchant_ids, "recurring", errors)
    check_foreign_key(recurring, "category_id", category_ids, "recurring", errors)

    check_foreign_key(
        transactions, "user_id", user_ids, "transactions", errors
    )
    check_foreign_key(
        transactions, "account_id", account_ids, "transactions", errors
    )
    check_foreign_key(
        transactions, "merchant_id", merchant_ids, "transactions", errors
    )
    check_foreign_key(
        transactions, "category_id", category_ids, "transactions", errors
    )
    check_foreign_key(
        transactions, "counterpart_account_id", account_ids,
        "transactions", errors, allow_blank=True
    )

    # 3. Check ownership consistency.
    account_owner = {
        row["account_id"]: row["user_id"] for row in accounts
    }

    for number, row in enumerate(transactions, start=2):
        if account_owner.get(row["account_id"]) != row["user_id"]:
            errors.append(
                f"transactions row {number}: account owner does not "
                "match transaction user."
            )

        counterpart = row.get("counterpart_account_id", "").strip()
        if counterpart and counterpart == row["account_id"]:
            errors.append(
                f"transactions row {number}: account cannot transfer "
                "to itself."
            )

    for number, row in enumerate(recurring, start=2):
        if account_owner.get(row["account_id"]) != row["user_id"]:
            errors.append(
                f"recurring row {number}: account owner does not "
                "match recurring-series user."
            )

    # 4. Enum and amount checks.
    valid_statuses = {"posted", "pending", "reversed", "cancelled"}
    valid_types = {"debit", "credit", "refund", "income", "transfer"}

    category_type = {
        row["category_id"]: row["category_type"] for row in categories
    }

    for number, row in enumerate(transactions, start=2):
        txn_type = row.get("transaction_type", "")
        status = row.get("status", "")

        if txn_type not in valid_types:
            errors.append(
                f"transactions row {number}: invalid transaction_type "
                f"'{txn_type}'."
            )

        if status not in valid_statuses:
            errors.append(
                f"transactions row {number}: invalid status '{status}'."
            )

        try:
            amount = float(row["amount"])
        except (ValueError, TypeError, KeyError):
            errors.append(
                f"transactions row {number}: invalid transaction amount."
            )
            continue

        if amount == 0:
            errors.append(
                f"transactions row {number}: zero-value transaction."
            )

        if txn_type == "debit" and amount >= 0:
            errors.append(
                f"transactions row {number}: debit should be negative."
            )

        if txn_type == "income" and amount <= 0:
            errors.append(
                f"transactions row {number}: income should be positive."
            )

        if txn_type == "refund" and amount <= 0:
            errors.append(
                f"transactions row {number}: refund should be positive."
            )

        if txn_type == "credit" and amount <= 0:
            errors.append(
                f"transactions row {number}: credit should be positive."
            )

        if txn_type == "transfer" and not row.get(
            "counterpart_account_id", ""
        ).strip():
            errors.append(
                f"transactions row {number}: transfer missing counterpart."
            )

        if txn_type == "income" and category_type.get(
            row["category_id"]
        ) != "income":
            errors.append(
                f"transactions row {number}: income category mismatch."
            )

    # 5. Date and lifecycle checks.
    for table_name in ("transactions", "budgets", "rules", "recurring"):
        for number, row in enumerate(tables[table_name], start=2):
            field = (
                "transaction_date" if table_name == "transactions"
                else "month" if table_name == "budgets"
                else "effective_from"
            )

            value = row.get(field, "").strip()

            try:
                if table_name == "budgets":
                    datetime.strptime(value, "%Y-%m")
                else:
                    date.fromisoformat(value[:10])
            except (ValueError, TypeError):
                errors.append(
                    f"{table_name} row {number}: invalid {field} '{value}'."
                )

    for table_name in ("accounts", "budgets", "recurring", "categories"):
        for number, row in enumerate(tables[table_name], start=2):
            if "status" in row and row["status"] not in {
                "active", "inactive", "closed", "cancelled", "completed"
            }:
                errors.append(
                    f"{table_name} row {number}: unknown status "
                    f"'{row['status']}'."
                )

    # 6. Expected dataset volume.
    if expected_users is not None and len(users) != expected_users:
        errors.append(
            f"Expected {expected_users} users; found {len(users)}."
        )

    if (
        expected_transactions is not None
        and len(transactions) != expected_transactions
    ):
        errors.append(
            f"Expected {expected_transactions} transactions; "
            f"found {len(transactions)}."
        )

    # 7. Ground-truth separation and labels.
    try:
        truth_rows = read_csv(ground_truth_dir / "ground_truth.csv")
        anomaly_rows = read_csv(ground_truth_dir / "anomaly_cases.csv")
        counts["ground_truth_labels"] = len(truth_rows)
        counts["anomaly_cases"] = len(anomaly_rows)

        transaction_ids = {
            row["transaction_id"] for row in transactions
        }
        truth_ids = [row.get("transaction_id", "") for row in truth_rows]

        if len(truth_ids) != len(set(truth_ids)):
            errors.append("Ground truth contains duplicate transaction IDs.")

        missing_labels = transaction_ids - set(truth_ids)
        extra_labels = set(truth_ids) - transaction_ids

        if missing_labels:
            errors.append(
                f"{len(missing_labels)} transaction(s) have no ground-truth label."
            )

        if extra_labels:
            errors.append(
                f"{len(extra_labels)} ground-truth transaction ID(s) "
                "are not in the input transaction table."
            )

        if any(not row.get("issue_type", "").strip() for row in anomaly_rows):
            warnings.append("Some anomaly cases have a blank issue_type.")

    except (FileNotFoundError, OSError, csv.Error) as exc:
        errors.append(f"Ground-truth validation failed: {exc}")

    return {
        "status": "PASS" if not errors else "FAIL",
        "row_counts": counts,
        "errors": errors,
        "warnings": warnings,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Validate the generated YottaFlex finance dataset."
    )
    parser.add_argument("--data", default="data/generated")
    parser.add_argument("--ground-truth", default=None)
    parser.add_argument("--expected-users", type=int, default=None)
    parser.add_argument("--expected-transactions", type=int, default=None)
    parser.add_argument("--report", default="docs/validation_report.json")
    args = parser.parse_args()

    result = validate_dataset(
        args.data,
        args.ground_truth,
        args.expected_users,
        args.expected_transactions,
    )

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"Validation status: {result['status']}")
    print("\nRow counts:")
    for table, count in result["row_counts"].items():
        print(f"  {table}: {count:,}")

    for warning in result["warnings"]:
        print(f"WARNING: {warning}")

    for error in result["errors"][:50]:
        print(f"ERROR: {error}")

    if len(result["errors"]) > 50:
        print(f"... and {len(result['errors']) - 50} more errors.")

    print(f"\nReport saved to: {report_path}")

    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
