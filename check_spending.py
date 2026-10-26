
import csv
from collections import defaultdict
from decimal import Decimal

file_path = "data/generated/transactions.csv"
totals = defaultdict(lambda: {"count": 0, "amount": Decimal("0")})

with open(file_path, encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)

    for row in reader:
        key = (row["category_id"], row["transaction_type"])
        totals[key]["count"] += 1
        totals[key]["amount"] += Decimal(row["amount"])

for key, value in sorted(totals.items()):
    print(
        f"{key} | count={value['count']:,} "
        f"| total={value['amount']:,.2f}"
    )
