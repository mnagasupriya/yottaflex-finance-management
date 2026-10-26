
import csv
from pathlib import Path


def test_generated_transactions_file_exists():
    path = Path("data/generated/transactions.csv")
    assert path.exists(), (
        "transactions.csv is missing. Generate the dataset first."
    )


def test_generated_transactions_have_expected_columns():
    path = Path("data/generated/transactions.csv")

    assert path.exists(), "transactions.csv is missing."

    with path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames

    assert columns is not None
    assert "transaction_id" in columns
    assert "user_id" in columns
    assert "amount" in columns
    assert "transaction_date" in columns
    assert "transaction_type" in columns


def test_generated_transactions_have_data():
    path = Path("data/generated/transactions.csv")

    assert path.exists(), "transactions.csv is missing."

    with path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        reader = csv.DictReader(file)
        first_row = next(reader, None)

    assert first_row is not None, (
        "transactions.csv contains no transaction rows."
    )