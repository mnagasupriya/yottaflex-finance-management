
"""Explainable transaction categorization using merchant ID rules."""

import argparse
import csv
from datetime import date
from pathlib import Path


def read_csv(path):
    """Read a CSV file and return its rows."""
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def write_csv(path, rows):
    """Write rows to CSV, including headers when rows are empty."""
    path.parent.mkdir(parents=True, exist_ok=True)

    if rows:
        fieldnames = list(rows[0].keys())
    else:
        # Preserve a predictable schema for empty output files.
        fieldnames = [
            "transaction_id",
            "user_id",
            "account_id",
            "merchant_id",
            "transaction_date",
            "transaction_type",
            "amount",
            "category_id",
            "predicted_category_id",
            "category_confidence",
            "matched_rule_id",
            "categorization_reason",
            "needs_manual_review",
            "source_category_id",
            "category_matches_source",
        ]

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def is_active_on(rule, transaction_date):
    """Check whether a rule is active on the transaction date."""
    if rule.get("active", "").strip().lower() not in {
        "true", "1", "yes"
    }:
        return False

    try:
        txn_date = date.fromisoformat(transaction_date)
        start = date.fromisoformat(rule["effective_from"])
    except (ValueError, KeyError, TypeError):
        return False

    if txn_date < start:
        return False

    end_text = rule.get("effective_to", "").strip()

    if end_text:
        try:
            end = date.fromisoformat(end_text)
        except ValueError:
            return False

        if txn_date > end:
            return False

    return True


def get_matching_rules(merchant_id, txn_date, rules):
    """Return active rules matching a merchant in deterministic order."""
    candidates = []

    for rule in rules:
        if rule.get("merchant_id", "").strip() != merchant_id:
            continue

        if not is_active_on(rule, txn_date):
            continue

        try:
            priority = int(rule.get("priority") or 999999)
        except (ValueError, TypeError):
            priority = 999999

        candidates.append((priority, rule.get("rule_id", ""), rule))

    candidates.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in candidates]


def review_result(reason):
    """Return a standard result requiring manual review."""
    return {
        "predicted_category_id": "",
        "category_confidence": 0.0,
        "matched_rule_id": "",
        "categorization_reason": reason,
        "needs_manual_review": True,
    }


def categorize_transaction(transaction, rules):
    """Predict a category using transaction type and active merchant rules."""
    merchant_id = transaction.get("merchant_id", "").strip()
    txn_date = transaction.get("transaction_date", "").strip()
    txn_type = transaction.get("transaction_type", "").strip().lower()

    # Transfers are identified by their transaction type.
    if txn_type == "transfer":
        return {
            "predicted_category_id": "CAT-TRANSFER",
            "category_confidence": 1.0,
            "matched_rule_id": "",
            "categorization_reason": (
                "Category assigned from the transfer transaction type."
            ),
            "needs_manual_review": False,
        }

    # Refunds use merchant rules rather than copying the source category.
    # Original purchase linkage must still be verified separately.
    if txn_type == "refund":
        candidates = get_matching_rules(merchant_id, txn_date, rules)

        if not candidates:
            return review_result(
                "Refund has no active merchant rule; verify its "
                "original transaction and category."
            )

        rule = candidates[0]

        return {
            "predicted_category_id": rule.get("category_id", ""),
            "category_confidence": 0.80,
            "matched_rule_id": rule.get("rule_id", ""),
            "categorization_reason": (
                "Refund category inferred from the active merchant rule; "
                "verify the original transaction linkage."
            ),
            "needs_manual_review": True,
        }

    # Validate required information before applying normal merchant rules.
    if not merchant_id:
        return review_result("Missing merchant ID.")

    if not txn_date:
        return review_result("Missing transaction date.")

    try:
        date.fromisoformat(txn_date)
    except ValueError:
        return review_result("Invalid transaction date.")

    candidates = get_matching_rules(merchant_id, txn_date, rules)

    if not candidates:
        return review_result(
            "No active merchant rule matched on the transaction date."
        )

    rule = candidates[0]
    predicted_category = rule.get("category_id", "").strip()

    if not predicted_category:
        return review_result(
            "Matched merchant rule has no category; manual review required."
        )

    priority = rule.get("priority", "")

    return {
        "predicted_category_id": predicted_category,
        "category_confidence": 0.95,
        "matched_rule_id": rule.get("rule_id", ""),
        "categorization_reason": (
            f"Matched merchant {merchant_id} using rule "
            f"{rule.get('rule_id', '')} (priority {priority})."
        ),
        "needs_manual_review": False,
    }


def categorize_all(transactions, rules):
    """Categorize all transactions and preserve source labels for auditing."""
    results = []

    for transaction in transactions:
        row = dict(transaction)
        prediction = categorize_transaction(transaction, rules)
        row.update(prediction)

        # This is an audit comparison, not independent ground-truth evaluation.
        source_category = transaction.get("category_id", "").strip()
        predicted = prediction["predicted_category_id"]

        row["source_category_id"] = source_category
        row["category_matches_source"] = (
            bool(predicted) and predicted == source_category
        )

        results.append(row)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Categorize transactions using explainable merchant rules."
    )
    parser.add_argument(
        "--input",
        default="data/generated/transactions.csv",
        help="Input transactions CSV.",
    )
    parser.add_argument(
        "--rules",
        default="data/generated/category_rules.csv",
        help="Merchant category rules CSV.",
    )
    parser.add_argument(
        "--output",
        default="data/generated/categorized_transactions.csv",
        help="Output categorized transactions CSV.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    rules_path = Path(args.rules)
    output_path = Path(args.output)

    if not input_path.exists():
        parser.error(f"Transactions file not found: {input_path}")

    if not rules_path.exists():
        parser.error(f"Category rules file not found: {rules_path}")

    transactions = read_csv(input_path)
    rules = read_csv(rules_path)

    results = categorize_all(transactions, rules)
    write_csv(output_path, results)

    matched_rules = sum(bool(row["matched_rule_id"]) for row in results)
    manual_review = sum(
        row["needs_manual_review"] is True for row in results
    )
    source_matches = sum(
        bool(row["category_matches_source"]) for row in results
    )
    transfers = sum(
        row.get("transaction_type", "").strip().lower() == "transfer"
        for row in results
    )
    refunds = sum(
        row.get("transaction_type", "").strip().lower() == "refund"
        for row in results
    )

    print("Categorization complete.")
    print(f"Transactions processed: {len(results):,}")
    print(f"Matched merchant rules: {matched_rules:,}")
    print(f"Transfer transactions: {transfers:,}")
    print(f"Refund transactions: {refunds:,}")
    print(f"Flagged for manual review: {manual_review:,}")
    print(
        "Predictions matching source category (audit only): "
        f"{source_matches:,}"
    )
    print(f"Output file: {output_path}")


if __name__ == "__main__":
    main()
