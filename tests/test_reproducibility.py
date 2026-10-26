
import csv
import hashlib
from pathlib import Path


def file_hash(path):
    """Return a hash of a file's contents."""
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def test_generated_transactions_are_not_empty():
    path = Path("data/generated/transactions.csv")

    assert path.exists(), "Generate the dataset first."
    assert path.stat().st_size > 0


def test_generated_transactions_have_unique_ids():
    path = Path("data/generated/transactions.csv")

    assert path.exists(), "Generate the dataset first."

    with path.open(
        "r", newline="", encoding="utf-8-sig"
    ) as file:
        reader = csv.DictReader(file)
        ids = [row["transaction_id"] for row in reader]

    assert ids, "No transactions were found."
    assert all(ids), "A transaction ID is missing."
    assert len(ids) == len(set(ids)), "Duplicate transaction IDs found."


def test_generated_transactions_file_hash_is_stable():
    path = Path("data/generated/transactions.csv")

    assert path.exists(), "Generate the dataset first."

    first_hash = file_hash(path)
    second_hash = file_hash(path)

    assert first_hash == second_hash
