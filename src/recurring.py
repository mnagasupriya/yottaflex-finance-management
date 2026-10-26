
"""Detect recurring payments and identify missing or inconsistent cycles."""

import csv
import os
import calendar
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "generated")


def read_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def write_csv(filename, rows):
    path = os.path.join(DATA_DIR, filename)

    if not rows:
        print(f"No rows to write: {path}")
        return

    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def parse_date(value):
    try:
        return date.fromisoformat(value[:10])
    except (ValueError, TypeError, AttributeError):
        return None


def parse_amount(value):
    try:
        return abs(Decimal(str(value)))
    except (InvalidOperation, ValueError, TypeError):
        return None


def expected_dates(series, end_date):
    """Generate expected dates for a recurring series."""
    start = parse_date(series.get("effective_from", ""))
    if not start:
        return []

    effective_to = parse_date(series.get("effective_to", ""))
    end = min(end_date, effective_to) if effective_to else end_date

    if end < start:
        return []

    frequency = series.get("frequency", "").lower()
    expected_day = int(series.get("expected_day") or start.day)
    dates = []

    if frequency == "monthly":
        year, month = start.year, start.month

        while (year, month) <= (end.year, end.month):
            day = min(expected_day, calendar.monthrange(year, month)[1])
            candidate = date(year, month, day)

            if start <= candidate <= end:
                dates.append(candidate)

            month += 1
            if month > 12:
                year += 1
                month = 1

    elif frequency == "weekly":
        current = start
        while current <= end:
            dates.append(current)
            current = date.fromordinal(current.toordinal() + 7)

    elif frequency == "biweekly":
        current = start
        while current <= end:
            dates.append(current)
            current = date.fromordinal(current.toordinal() + 14)

    elif frequency == "yearly":
        for year in range(start.year, end.year + 1):
            day = min(expected_day, calendar.monthrange(year, start.month)[1])
            candidate = date(year, start.month, day)
            if start <= candidate <= end:
                dates.append(candidate)

    return dates


def detect_recurring_payments(transactions, series_records):
    valid_transactions = []
    data_exceptions = []

    for txn in transactions:
        txn_date = parse_date(txn.get("transaction_date", ""))
        amount = parse_amount(txn.get("amount", ""))

        if not txn_date or amount is None:
            data_exceptions.append({
                "transaction_id": txn.get("transaction_id", ""),
                "reason": "Invalid transaction date or amount",
            })
            continue

        valid_transactions.append((txn, txn_date, amount))

    if not valid_transactions:
        return [], [], data_exceptions

    last_transaction_date = max(item[1] for item in valid_transactions)

    # Match payments using user, account, merchant, and transaction direction.
    transaction_groups = defaultdict(list)

    for txn, txn_date, amount in valid_transactions:
        if txn.get("status", "").lower() != "posted":
            continue

        if txn.get("transaction_type", "").lower() not in {"debit", "income"}:
            continue

        key = (
            txn.get("user_id", ""),
            txn.get("account_id", ""),
            txn.get("merchant_id", ""),
            txn.get("transaction_type", "").lower(),
        )
        transaction_groups[key].append((txn, txn_date, amount))

    candidates = []
    cycle_exceptions = []
    seen_transactions = set()

    for series in series_records:
        if series.get("status", "").lower() != "active":
            continue

        key_income = series.get("category_id", "") == "CAT-INCOME"
        expected_type = "income" if key_income else "debit"

        key = (
            series.get("user_id", ""),
            series.get("account_id", ""),
            series.get("merchant_id", ""),
            expected_type,
        )

        matching = transaction_groups.get(key, [])
        expected_amount = parse_amount(series.get("expected_amount", ""))

        if expected_amount is None:
            cycle_exceptions.append({
                "recurring_id": series.get("recurring_id", ""),
                "expected_date": "",
                "exception_type": "INVALID_EXPECTED_AMOUNT",
                "details": "Recurring series has an invalid expected amount",
                "matched_transaction_ids": "",
            })
            continue

        start = parse_date(series.get("effective_from", ""))
        end = parse_date(series.get("effective_to", "")) or last_transaction_date

        if not start:
            continue

        schedule_end = min(end, last_transaction_date)
        dates = expected_dates(series, schedule_end)

        matched_count = 0
        missing_count = 0

        for expected_date in dates:
            # Allow a three-day window around the expected payment date.
            matches = [
                (txn, txn_date, amount)
                for txn, txn_date, amount in matching
                if abs((txn_date - expected_date).days) <= 3
                and txn.get("transaction_id") not in seen_transactions
            ]

            amount_matches = [
                item for item in matches
                if abs(item[2] - expected_amount) <= max(
                    Decimal("1.00"), expected_amount * Decimal("0.05")
                )
            ]

            if amount_matches:
                txn, txn_date, amount = min(
                    amount_matches,
                    key=lambda item: abs((item[1] - expected_date).days),
                )
                seen_transactions.add(txn.get("transaction_id"))
                matched_count += 1
            else:
                missing_count += 1
                cycle_exceptions.append({
                    "recurring_id": series.get("recurring_id", ""),
                    "expected_date": expected_date.isoformat(),
                    "exception_type": "POSSIBLE_MISSED_PAYMENT",
                    "details": (
                        "No posted transaction matched the expected date "
                        "and amount within the allowed window"
                    ),
                    "matched_transaction_ids": "",
                })

        candidates.append({
            "recurring_id": series.get("recurring_id", ""),
            "user_id": series.get("user_id", ""),
            "account_id": series.get("account_id", ""),
            "merchant_id": series.get("merchant_id", ""),
            "category_id": series.get("category_id", ""),
            "frequency": series.get("frequency", ""),
            "expected_amount": str(expected_amount),
            "expected_occurrences": len(dates),
            "matched_occurrences": matched_count,
            "possible_missed_occurrences": missing_count,
            "match_rate": (
                round(matched_count / len(dates), 4) if dates else 0
            ),
            "status": "MATCHED" if matched_count else "NO_MATCH",
        })

    return candidates, cycle_exceptions, data_exceptions


def main():
    transactions = read_csv("transactions.csv")
    series_records = read_csv("recurring_series.csv")

    candidates, cycle_exceptions, data_exceptions = (
        detect_recurring_payments(transactions, series_records)
    )

    write_csv("detected_recurring_payments.csv", candidates)
    write_csv("recurring_cycle_exceptions.csv", cycle_exceptions)
    write_csv("recurring_data_exceptions.csv", data_exceptions)

    print("\n=== Recurring Payment Detection ===")
    print(f"Transactions scanned: {len(transactions):,}")
    print(f"Recurring series examined: {len(series_records):,}")
    print(f"Recurring candidates: {len(candidates):,}")
    print(
        "Series with at least one matched payment: "
        f"{sum(row['matched_occurrences'] > 0 for row in candidates):,}"
    )
    print(f"Possible missed cycles: {len(cycle_exceptions):,}")
    print(f"Invalid transaction records: {len(data_exceptions):,}")
    print("Reports saved under data/generated/")


if __name__ == "__main__":
    main()
