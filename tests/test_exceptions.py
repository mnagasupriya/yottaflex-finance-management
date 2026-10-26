
from src.budgets import (
    calculate_household_spending,
    compare_budgets,
)


def test_invalid_transaction_date_is_flagged():
    transactions = [
        {
            "transaction_id": "T1",
            "user_id": "U1",
            "transaction_type": "debit",
            "status": "posted",
            "category_id": "food",
            "transaction_date": "invalid-date",
            "amount": "-50.00",
        }
    ]

    spending, _, exceptions = calculate_household_spending(transactions)

    assert spending == []
    assert len(exceptions) == 1
    assert exceptions[0]["reason"] == (
        "Missing or invalid transaction date"
    )


def test_positive_expense_amount_is_flagged():
    transactions = [
        {
            "transaction_id": "T1",
            "user_id": "U1",
            "transaction_type": "debit",
            "status": "posted",
            "category_id": "food",
            "transaction_date": "2026-01-10",
            "amount": "50.00",
        }
    ]

    spending, _, exceptions = calculate_household_spending(transactions)

    assert spending == []
    assert len(exceptions) == 1
    assert exceptions[0]["reason"] == (
        "Expense has a positive amount"
    )


def test_invalid_budget_amount_is_flagged():
    budgets = [
        {
            "budget_id": "B1",
            "user_id": "U1",
            "month": "2026-01",
            "category_id": "food",
            "budget_amount": "invalid",
        }
    ]

    result = compare_budgets([], budgets)

    assert result[0]["status"] == "REVIEW_INVALID_BUDGET"
    assert result[0]["exception_reason"] == "Invalid budget amount"


def test_negative_budget_amount_is_flagged():
    budgets = [
        {
            "budget_id": "B2",
            "user_id": "U1",
            "month": "2026-01",
            "category_id": "food",
            "budget_amount": "-100.00",
        }
    ]

    result = compare_budgets([], budgets)

    assert result[0]["status"] == "REVIEW_INVALID_BUDGET"
    assert result[0]["exception_reason"] == (
        "Budget amount must be non-negative"
    )