
from src.budgets import (
    calculate_household_spending,
    compare_budgets,
)


def test_expense_is_counted_as_spending():
    transactions = [
        {
            "transaction_id": "T1",
            "user_id": "U1",
            "transaction_type": "debit",
            "status": "posted",
            "category_id": "food",
            "transaction_date": "2026-01-10",
            "amount": "-100.00",
        }
    ]

    spending, excluded, exceptions = calculate_household_spending(
        transactions
    )

    assert len(spending) == 1
    assert spending[0]["net_spending"] == "100.00"
    assert exceptions == []


def test_income_and_transfer_are_excluded():
    transactions = [
        {
            "transaction_id": "T1",
            "user_id": "U1",
            "transaction_type": "income",
            "status": "posted",
            "category_id": "income",
            "transaction_date": "2026-01-10",
            "amount": "1000.00",
        },
        {
            "transaction_id": "T2",
            "user_id": "U1",
            "transaction_type": "transfer",
            "status": "posted",
            "category_id": "transfer",
            "transaction_date": "2026-01-11",
            "amount": "-200.00",
        },
    ]

    spending, excluded, exceptions = calculate_household_spending(
        transactions
    )

    assert spending == []
    assert excluded["income"] == 1
    assert excluded["internal_transfer"] == 1
    assert exceptions == []


def test_refund_reduces_spending():
    transactions = [
        {
            "transaction_id": "T1",
            "user_id": "U1",
            "transaction_type": "debit",
            "status": "posted",
            "category_id": "food",
            "transaction_date": "2026-01-10",
            "amount": "-100.00",
        },
        {
            "transaction_id": "T2",
            "user_id": "U1",
            "transaction_type": "refund",
            "status": "posted",
            "category_id": "food",
            "transaction_date": "2026-01-15",
            "amount": "20.00",
        },
    ]

    spending, _, exceptions = calculate_household_spending(transactions)

    assert spending[0]["net_spending"] == "80.00"
    assert exceptions == []


def test_over_budget_is_detected():
    spending = [
        {
            "user_id": "U1",
            "month": "2026-01",
            "category_id": "food",
            "net_spending": "120.00",
        }
    ]

    budgets = [
        {
            "budget_id": "B1",
            "user_id": "U1",
            "month": "2026-01",
            "category_id": "food",
            "budget_amount": "100.00",
        }
    ]

    result = compare_budgets(spending, budgets)

    assert result[0]["status"] == "OVER_BUDGET"
    assert result[0]["remaining_budget"] == "-20.00"


def test_invalid_budget_category_is_flagged():
    budgets = [
        {
            "budget_id": "B1",
            "user_id": "U1",
            "month": "2026-01",
            "category_id": "unknown",
            "budget_amount": "100.00",
        }
    ]

    result = compare_budgets(
        [],
        budgets,
        valid_category_ids={"food", "transport"},
    )

    assert result[0]["status"] == "REVIEW_INVALID_BUDGET"
    assert result[0]["exception_reason"] == "Invalid budget category"
