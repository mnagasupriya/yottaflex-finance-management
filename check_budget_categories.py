
import csv
from collections import defaultdict
from decimal import Decimal

data_dir = "data/generated"

spending = defaultdict(Decimal)
budgets = defaultdict(list)

with open(f"{data_dir}/transactions.csv", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        if row["status"].strip().lower() != "posted":
            continue

        if row["transaction_type"].strip().lower() not in {"debit", "expense", "refund"}:
            continue

        category = row["category_id"]
        month = row["transaction_date"][:7]
        key = (row["user_id"], month, category)
        amount = Decimal(row["amount"])

        if row["transaction_type"].strip().lower() == "refund":
            spending[key] -= amount
        else:
            spending[key] += abs(amount)

with open(f"{data_dir}/budgets.csv", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        if row["category_id"] in {"CAT-RENT", "CAT-SUBSCRIPTIONS"}:
            key = (row["user_id"], row["month"], row["category_id"])
            budgets[key].append(Decimal(row["budget_amount"]))

for category in ("CAT-RENT", "CAT-SUBSCRIPTIONS"):
    keys = [key for key in budgets if key[2] == category]
    over = sum(spending[key] > budgets[key][0] for key in keys)
    print(f"\n{category}")
    print(f"Budget records: {len(keys):,}")
    print(f"Over-budget records: {over:,}")

    for key in keys[:5]:
        print(
            f"User={key[0]}, Month={key[1]}, "
            f"Budget=₹{budgets[key][0]:,.2f}, "
            f"Actual=₹{spending[key]:,.2f}"
        )
