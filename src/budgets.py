
"""Household spending calculations and budget comparisons."""

from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation


ZERO = Decimal("0.00")


def as_decimal(value):
    """Convert a value to Decimal safely."""
    try:
        amount = Decimal(str(value))
        if not amount.is_finite():
            return ZERO
        return amount
    except (InvalidOperation, ValueError, TypeError):
        return ZERO


def valid_month(month):
    """Check that a month uses the YYYY-MM format."""
    try:
        datetime.strptime(month, "%Y-%m")
        return len(month) == 7
    except (ValueError, TypeError):
        return False


def calculate_household_spending(transactions):
    """
    Calculate monthly net spending by user and category.

    Rules:
    - Only posted transactions are counted.
    - Income and internal transfers are excluded.
    - Expense amounts must be zero or negative.
    - Refunds must be zero or positive and reduce spending.
    - Invalid transactions are recorded as exceptions.
    """
    spending = defaultdict(Decimal)
    excluded = defaultdict(int)
    exceptions = []

    for txn in transactions:
        txn_id = txn.get("transaction_id", "")
        user_id = txn.get("user_id", "")
        txn_type = str(
            txn.get("transaction_type", "")
        ).strip().lower()
        status = str(txn.get("status", "")).strip().lower()
        category = txn.get("category_id", "")
        txn_date = str(
            txn.get("transaction_date", "")
        ).strip()

        if status != "posted":
            excluded["not_posted"] += 1
            continue

        if txn_type == "transfer":
            excluded["internal_transfer"] += 1
            continue

        if txn_type == "income":
            excluded["income"] += 1
            continue

        if not user_id:
            exceptions.append({
                "transaction_id": txn_id,
                "reason": "Missing user ID",
            })
            continue

        if not valid_month(txn_date[:7]) or len(txn_date) < 10:
            exceptions.append({
                "transaction_id": txn_id,
                "reason": "Missing or invalid transaction date",
            })
            continue

        if not category:
            exceptions.append({
                "transaction_id": txn_id,
                "reason": "Missing transaction category",
            })
            continue

        month = txn_date[:7]
        amount = as_decimal(txn.get("amount", "0"))

        if txn_type in {"debit", "expense"}:
            if amount > 0:
                exceptions.append({
                    "transaction_id": txn_id,
                    "reason": "Expense has a positive amount",
                })
                continue

            spending[(user_id, month, category)] += abs(amount)

        elif txn_type == "refund":
            if amount < 0:
                exceptions.append({
                    "transaction_id": txn_id,
                    "reason": "Refund has a negative amount",
                })
                continue

            spending[(user_id, month, category)] -= amount

        else:
            exceptions.append({
                "transaction_id": txn_id,
                "reason": f"Unsupported transaction type: {txn_type}",
            })

    rows = []

    for (user_id, month, category), amount in sorted(spending.items()):
        rows.append({
            "user_id": user_id,
            "month": month,
            "category_id": category,
            "net_spending": str(amount.quantize(Decimal("0.01"))),
        })

    return rows, dict(excluded), exceptions


def compare_budgets(
    spending_rows,
    budgets,
    valid_category_ids=None,
):
    """
    Compare monthly spending with budgets.

    If valid_category_ids is supplied, budget categories must
    exist in that set.
    """
    spending_lookup = {
        (
            row["user_id"],
            row["month"],
            row["category_id"],
        ): as_decimal(row["net_spending"])
        for row in spending_rows
    }

    comparisons = []

    for budget in budgets:
        budget_id = budget.get("budget_id", "")
        user_id = budget.get("user_id", "")
        month = budget.get("month", "")
        category = budget.get("category_id", "")
        raw_amount = budget.get("budget_amount", "")

        reason = ""

        if not user_id or not month or not category:
            reason = "Missing required budget field"
        elif not valid_month(month):
            reason = "Invalid budget month"
        elif (
            valid_category_ids is not None
            and category not in valid_category_ids
        ):
            reason = "Invalid budget category"
        else:
            try:
                budget_amount = Decimal(str(raw_amount))
                if (
                    not budget_amount.is_finite()
                    or budget_amount < 0
                ):
                    reason = "Budget amount must be non-negative"
            except (InvalidOperation, ValueError, TypeError):
                reason = "Invalid budget amount"

        if reason:
            comparisons.append({
                "budget_id": budget_id,
                "user_id": user_id,
                "month": month,
                "category_id": category,
                "budget_amount": raw_amount,
                "actual_spending": "",
                "remaining_budget": "",
                "status": "REVIEW_INVALID_BUDGET",
                "exception_reason": reason,
            })
            continue

        actual = spending_lookup.get(
            (user_id, month, category),
            ZERO,
        )
        remaining = budget_amount - actual

        if actual > budget_amount:
            status = "OVER_BUDGET"
        elif (
            budget_amount > ZERO
            and actual >= budget_amount * Decimal("0.80")
        ) or (
            budget_amount == ZERO and actual == ZERO
        ):
            status = "NEAR_BUDGET"
        else:
            status = "WITHIN_BUDGET"

        comparisons.append({
            "budget_id": budget_id,
            "user_id": user_id,
            "month": month,
            "category_id": category,
            "budget_amount": str(
                budget_amount.quantize(Decimal("0.01"))
            ),
            "actual_spending": str(
                actual.quantize(Decimal("0.01"))
            ),
            "remaining_budget": str(
                remaining.quantize(Decimal("0.01"))
            ),
            "status": status,
            "exception_reason": (
                "Spending exceeds budget"
                if status == "OVER_BUDGET"
                else ""
            ),
        })

    return comparisons
