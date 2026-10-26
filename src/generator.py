import argparse
import csv
import hashlib
import json
import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

DEFAULT_SEED = 20261022

CATEGORIES = [
    ("CAT-GROCERIES", "Groceries", "groceries"),
    ("CAT-RENT", "Rent", "rent"),
    ("CAT-UTILITIES", "Utilities", "utilities"),
    ("CAT-TRANSPORT", "Transport", "transport"),
    ("CAT-SUBSCRIPTIONS", "Subscriptions", "subscriptions"),
    ("CAT-HEALTH", "Healthcare", "healthcare"),
    ("CAT-DINING", "Dining", "dining"),
    ("CAT-SHOPPING", "Shopping", "shopping"),
    ("CAT-INCOME", "Income", "income"),
    ("CAT-TRANSFER", "Internal Transfer", "transfer"),
]

MERCHANTS = [
    ("MER-000001", "FreshMart", "CAT-GROCERIES", ["Fresh Mart", "FRESHMART"]),
    ("MER-000002", "HomeRent", "CAT-RENT", ["Home Rent", "HOMERENT"]),
    ("MER-000003", "PowerGrid", "CAT-UTILITIES", ["Power Grid", "POWERGRID"]),
    ("MER-000004", "CityTransit", "CAT-TRANSPORT", ["City Transit", "CITYTRANSIT"]),
    ("MER-000005", "StreamBox", "CAT-SUBSCRIPTIONS", ["Stream Box", "STREAMBOX"]),
    ("MER-000006", "HealthPlus", "CAT-HEALTH", ["Health Plus", "HEALTHPLUS"]),
    ("MER-000007", "FoodCorner", "CAT-DINING", ["Food Corner", "FOODCORNER"]),
    ("MER-000008", "ShopWorld", "CAT-SHOPPING", ["Shop World", "SHOPWORLD"]),
    ("MER-000009", "Employer Payroll", "CAT-INCOME", ["Payroll", "Salary Credit"]),
    ("MER-000010", "Own Account Transfer", "CAT-TRANSFER", ["Self Transfer", "Account Transfer"]),
]

# All categories that represent household expenses. Used for expense summaries.
EXPENSE_CATEGORIES = [
    "CAT-GROCERIES",
    "CAT-RENT",
    "CAT-UTILITIES",
    "CAT-TRANSPORT",
    "CAT-SUBSCRIPTIONS",
    "CAT-HEALTH",
    "CAT-DINING",
    "CAT-SHOPPING",
]

# Variable day-to-day expenses only. Rent and subscriptions are generated
# separately so they are not accidentally assigned a second time as generic expenses.
RANDOM_EXPENSE_CATEGORIES = [
    "CAT-GROCERIES",
    "CAT-UTILITIES",
    "CAT-TRANSPORT",
    "CAT-HEALTH",
    "CAT-DINING",
    "CAT-SHOPPING",
]


def write_csv(path, fieldnames, rows):
    """Write rows in a stable column order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def month_range(months):
    """Return YYYY-MM values for the period ending October 2026."""
    end_year, end_month = 2026, 10
    result = []
    for offset in reversed(range(months)):
        month_index = end_year * 12 + end_month - 1 - offset
        year, zero_month = divmod(month_index, 12)
        result.append(f"{year:04d}-{zero_month + 1:02d}")
    return result


def generate_dataset(users=1000, transactions=500000, months=12,
                     seed=DEFAULT_SEED, out="data/generated"):
    if users < 1 or transactions < 5 or months < 1:
        raise ValueError("Use at least 1 user, 5 transactions and 1 month.")

    rng = random.Random(seed)
    out = Path(out)
    truth_dir = out.parent / "ground_truth"
    out.mkdir(parents=True, exist_ok=True)
    truth_dir.mkdir(parents=True, exist_ok=True)

    months_list = month_range(months)
    start_date = date.fromisoformat(months_list[0] + "-01")
    last_month_start = date.fromisoformat(months_list[-1] + "-01")
    if last_month_start.month == 12:
        end_date = date(last_month_start.year + 1, 1, 1)
    else:
        end_date = date(last_month_start.year, last_month_start.month + 1, 1)
    total_days = (end_date - start_date).days

    # 1. Parent/master entities.
    profiles, accounts = [], []
    for i in range(1, users + 1):
        user_id = f"USR-{i:06d}"
        profiles.append({
            "user_id": user_id,
            "display_name": f"Synthetic User {i:06d}",
            "household_id": f"HHD-{i:06d}",
            "currency": "INR",
            "status": "active",
        })
        for account_no in (1, 2):
            accounts.append({
                "account_id": f"ACC-{user_id}-{account_no:02d}",
                "user_id": user_id,
                "account_type": "checking" if account_no == 1 else "savings",
                "currency": "INR",
                "status": "active",
            })

    categories = [{
        "category_id": cid,
        "category_name": name,
        "category_code": code,
        "category_type": "income" if cid == "CAT-INCOME" else "transfer" if cid == "CAT-TRANSFER" else "expense",
        "active": True,
    } for cid, name, code in CATEGORIES]

    merchant_rows = [{
        "merchant_id": mid,
        "merchant_name": name,
        "default_category_id": category_id,
        "aliases": "|".join(aliases),
        "active": True,
    } for mid, name, category_id, aliases in MERCHANTS]

    category_rules = []
    for i, (mid, name, category_id, aliases) in enumerate(MERCHANTS, 1):
        category_rules.append({
            "rule_id": f"RULE-{i:06d}", "merchant_id": mid,
            "category_id": category_id, "match_type": "alias_or_exact_name",
            "priority": 100 - i, "effective_from": months_list[0] + "-01",
            "effective_to": "", "active": True,
        })

    write_csv(out / "users.csv", ["user_id", "display_name", "household_id", "currency", "status"], profiles)
    write_csv(out / "accounts.csv", ["account_id", "user_id", "account_type", "currency", "status"], accounts)
    write_csv(out / "categories.csv", ["category_id", "category_name", "category_code", "category_type", "active"], categories)
    write_csv(out / "merchants.csv", ["merchant_id", "merchant_name", "default_category_id", "aliases", "active"], merchant_rows)
    write_csv(out / "category_rules.csv", ["rule_id", "merchant_id", "category_id", "match_type", "priority", "effective_from", "effective_to", "active"], category_rules)

    # 2. Budgets and recurring schedules.
    budgets, recurring = [], []
    recurring_id = 1
    budget_limits = {
        "CAT-GROCERIES": 12000, "CAT-UTILITIES": 4000,
        "CAT-TRANSPORT": 3500, "CAT-SUBSCRIPTIONS": 1500,
        "CAT-HEALTH": 4000, "CAT-DINING": 5000,
        "CAT-SHOPPING": 6000, "CAT-RENT": 15000,
    }
    for profile in profiles:
        user_id = profile["user_id"]
        for month in months_list:
            for category_id, limit in budget_limits.items():
                category_code = category_id.replace("CAT-", "").lower()
                budgets.append({
                    "budget_id": f"BUD-{user_id}-{month}-{category_code}",
                    "user_id": user_id, "month": month, "category_id": category_id,
                    "budget_amount": round(limit * rng.uniform(0.8, 1.2), 2),
                    "currency": "INR", "status": "active",
                })
        recurring_specs = [
            ("salary", "MER-000009", "CAT-INCOME", 45000, 5),
            ("rent", "MER-000002", "CAT-RENT", 12000, 1),
            ("subscription", "MER-000005", "CAT-SUBSCRIPTIONS", 649, 10),
        ]
        for kind, merchant_id, category_id, amount, day in recurring_specs:
            recurring.append({
                "recurring_id": f"REC-{recurring_id:06d}", "user_id": user_id,
                "account_id": f"ACC-{user_id}-01", "merchant_id": merchant_id,
                "category_id": category_id, "frequency": "monthly",
                "expected_amount": amount, "expected_day": day,
                "effective_from": months_list[0] + "-01", "effective_to": "",
                "status": "active",
            })
            recurring_id += 1

    write_csv(out / "budgets.csv", ["budget_id", "user_id", "month", "category_id", "budget_amount", "currency", "status"], budgets)
    write_csv(out / "recurring_series.csv", ["recurring_id", "user_id", "account_id", "merchant_id", "category_id", "frequency", "expected_amount", "expected_day", "effective_from", "effective_to", "status"], recurring)

    # 3. Transactions and separate ground-truth labels.
    transaction_fields = [
        "transaction_id", "user_id", "account_id", "counterpart_account_id",
        "merchant_id", "transaction_timestamp", "transaction_date", "description",
        "amount", "currency", "transaction_type", "category_id", "status",
    ]
    truth_fields = ["transaction_id", "expected_category_id", "expected_category_name", "issue_type", "expected_decision"]
    category_name = {cid: name for cid, name, _ in CATEGORIES}
    merchant_by_id = {m[0]: m for m in MERCHANTS}
    spend_by_user_category, spend_by_user = defaultdict(float), defaultdict(float)
    anomaly_rows = []

    edge_cases = {
        0: ("transfer_out", "CAT-TRANSFER", "MER-000010", -250.00, "transfer between own accounts"),
        1: ("transfer_in", "CAT-TRANSFER", "MER-000010", 250.00, "matching transfer between own accounts"),
        2: ("refund", "CAT-GROCERIES", "MER-000001", 200.00, "refund for a previous grocery purchase"),
        3: ("timezone_boundary", "CAT-GROCERIES", "MER-000001", -125.00, "transaction near timezone date boundary"),
        4: ("subscription", "CAT-SUBSCRIPTIONS", "MER-000005", -649.00, "monthly subscription"),
    }

    # Build scheduled transactions from recurring_series.csv's source records.
    # Selected cycles are intentionally omitted to test missed-payment alerts.
    scheduled_transactions = []
    for series in recurring:
        series_number = int(series["recurring_id"].split("-")[-1])
        category_id = series["category_id"]
        if category_id == "CAT-INCOME":
            kind, amount, description = "salary", float(series["expected_amount"]), "scheduled salary credit"
        elif category_id == "CAT-RENT":
            kind, amount, description = "rent", -abs(float(series["expected_amount"])), "scheduled monthly rent"
        else:
            kind, amount, description = "subscription", -abs(float(series["expected_amount"])), "scheduled subscription payment"

        for month_index, month in enumerate(months_list):
            if series_number == 2 and month_index == 5:
                continue
            if month_index > 0 and (series_number + month_index) % 97 == 0:
                continue
            month_start = date.fromisoformat(month + "-01")
            next_month = month_start.replace(day=28) + timedelta(days=4)
            month_end = next_month.replace(day=1) - timedelta(days=1)
            expected_day = min(int(series["expected_day"]), month_end.day)
            scheduled_transactions.append({
                "kind": kind, "user_id": series["user_id"],
                "category_id": category_id, "merchant_id": series["merchant_id"],
                "amount": amount, "description": description,
                "date": month_start.replace(day=expected_day),
            })

    # Keep five deterministic edge-case records, then scheduled payments, then random activity.
    scheduled_capacity = min(len(scheduled_transactions), max(0, transactions - len(edge_cases)))
    scheduled_transactions = scheduled_transactions[:scheduled_capacity]

    with (out / "transactions.csv").open("w", newline="", encoding="utf-8") as tx_file:
        tx_writer = csv.DictWriter(tx_file, fieldnames=transaction_fields)
        tx_writer.writeheader()
        with (truth_dir / "ground_truth.csv").open("w", newline="", encoding="utf-8") as truth_file:
            truth_writer = csv.DictWriter(truth_file, fieldnames=truth_fields)
            truth_writer.writeheader()

            for i in range(transactions):
                txn_id = f"TXN-2026-{i + 1:08d}"
                scheduled_date = None
                if i in edge_cases:
                    kind, category_id, merchant_id, amount, description = edge_cases[i]
                    user_index = 0
                elif i < len(edge_cases) + len(scheduled_transactions):
                    scheduled = scheduled_transactions[i - len(edge_cases)]
                    kind = scheduled["kind"]
                    category_id = scheduled["category_id"]
                    merchant_id = scheduled["merchant_id"]
                    amount = scheduled["amount"]
                    description = scheduled["description"]
                    scheduled_date = scheduled["date"]
                    user_index = int(scheduled["user_id"].split("-")[-1]) - 1
                else:
                    user_index = rng.randrange(users)
                    # Keep rent/subscriptions mostly tied to their scheduled series.
                    # Generic expenses use a lower range to align better with monthly budgets.
                    kind = rng.choices(
                        ["expense", "salary", "rent", "subscription", "refund", "transfer"],
                        weights=[55, 4, 0, 1, 6, 34],
                        k=1,
                    )[0]
                    if kind == "salary":
                        category_id, merchant_id = "CAT-INCOME", "MER-000009"
                        amount = round(rng.uniform(30000, 80000), 2)
                        description = "salary credit"
                    elif kind == "rent":
                        category_id, merchant_id = "CAT-RENT", "MER-000002"
                        amount = -round(rng.uniform(8000, 22000), 2)
                        description = "monthly rent"
                    elif kind == "subscription":
                        category_id, merchant_id = "CAT-SUBSCRIPTIONS", "MER-000005"
                        amount = -round(rng.uniform(199, 1499), 2)
                        description = "subscription payment"
                    elif kind == "refund":
                        category_id = rng.choice(RANDOM_EXPENSE_CATEGORIES)
                        merchant_id = next(m[0] for m in MERCHANTS if m[2] == category_id)
                        amount = round(rng.uniform(50, 2000), 2)
                        description = "merchant refund"
                    elif kind == "transfer":
                        category_id, merchant_id = "CAT-TRANSFER", "MER-000010"
                        amount = -round(rng.uniform(100, 5000), 2)
                        description = "internal account transfer"
                    else:
                        category_id = rng.choice(RANDOM_EXPENSE_CATEGORIES)
                        merchant_id = next(m[0] for m in MERCHANTS if m[2] == category_id)
                        amount = -round(rng.uniform(50, 2000), 2)
                        description = merchant_by_id[merchant_id][1]

                user_id = f"USR-{user_index + 1:06d}"
                account_id = f"ACC-{user_id}-01"
                counterpart = ""
                txn_type = "debit" if amount < 0 else "credit"
                if kind == "transfer_out":
                    counterpart = f"ACC-{user_id}-02"
                    txn_type = "transfer"
                elif kind == "transfer_in":
                    account_id = f"ACC-{user_id}-02"
                    counterpart = f"ACC-{user_id}-01"
                    txn_type = "transfer"
                elif kind == "transfer":
                    counterpart = f"ACC-{user_id}-02"
                    txn_type = "transfer"
                elif kind == "refund":
                    txn_type = "refund"
                elif kind == "salary":
                    txn_type = "income"

                if kind == "timezone_boundary":
                    timestamp, txn_date = "2026-10-01T00:15:00+05:30", "2026-10-01"
                else:
                    if scheduled_date is not None:
                        txn_day, hour, minute = scheduled_date, 12, 0
                    else:
                        txn_day = start_date + timedelta(days=rng.randrange(total_days))
                        hour, minute = rng.randrange(24), rng.randrange(60)
                    timestamp = f"{txn_day.isoformat()}T{hour:02d}:{minute:02d}:00+05:30"
                    txn_date = txn_day.isoformat()

                tx_writer.writerow({
                    "transaction_id": txn_id, "user_id": user_id, "account_id": account_id,
                    "counterpart_account_id": counterpart, "merchant_id": merchant_id,
                    "transaction_timestamp": timestamp, "transaction_date": txn_date,
                    "description": description, "amount": f"{amount:.2f}", "currency": "INR",
                    "transaction_type": txn_type, "category_id": category_id, "status": "posted",
                })

                if category_id in EXPENSE_CATEGORIES:
                    spend_by_user_category[(user_id, category_id)] += -amount
                    spend_by_user[user_id] += -amount

                issue_type = ""
                expected_decision = "Use assigned ground-truth category."
                if kind in ("transfer_out", "transfer_in", "transfer"):
                    issue_type = "internal_transfer"
                    expected_decision = "Exclude internal transfers from household spending."
                elif kind == "refund":
                    issue_type = "refund"
                    expected_decision = "Treat as a refund; reduce matched-category net spending."
                elif kind == "timezone_boundary":
                    issue_type = "timezone_boundary"
                    expected_decision = "Preserve offset and apply documented timezone policy."

                truth_writer.writerow({
                    "transaction_id": txn_id, "expected_category_id": category_id,
                    "expected_category_name": category_name[category_id],
                    "issue_type": issue_type, "expected_decision": expected_decision,
                })
                if issue_type:
                    anomaly_rows.append({
                        "case_id": f"CASE-{len(anomaly_rows) + 1:04d}",
                        "record_id": txn_id, "issue_type": issue_type,
                        "expected_decision": expected_decision,
                    })

    # 4. Insights are derived from generated transactions.
    insights = []
    for index, profile in enumerate(profiles, 1):
        user_id = profile["user_id"]
        insights.append({
            "insight_id": f"INS-{index:06d}", "user_id": user_id,
            "insight_type": "total_expense", "period": f"{months_list[0]} to {months_list[-1]}",
            "value": round(spend_by_user[user_id], 2), "currency": "INR",
            "description": "Aggregate of categorized expense transactions; validate refunds and transfers before final net-spend reporting.",
        })
    write_csv(out / "insights.csv", ["insight_id", "user_id", "insight_type", "period", "value", "currency", "description"], insights)

    anomaly_rows.extend([
        {"case_id": "CASE-RECURRING-0001", "record_id": "REC-000002", "issue_type": "recurring_series_skip", "expected_decision": "Flag the missing expected occurrence; do not assume cancellation."},
        {"case_id": "CASE-BUDGET-0001", "record_id": "INVALID-BUDGET-CASE", "issue_type": "invalid_budget_category", "expected_decision": "Reject or flag the budget because its category is not in the taxonomy."},
        {"case_id": "CASE-TRANSFER-0001", "record_id": "TXN-2026-00000001", "issue_type": "transfer_double_count", "expected_decision": "Do not count the internal transfer pair as household expense."},
        {"case_id": "CASE-REFUND-0001", "record_id": "TXN-2026-00000003", "issue_type": "refund_as_expense", "expected_decision": "Treat the refund as a credit against the relevant expense category."},
    ])
    write_csv(truth_dir / "anomaly_cases.csv", ["case_id", "record_id", "issue_type", "expected_decision"], anomaly_rows)

    # 5. Manifest with checksums for repeatability.
    files = sorted(path for path in out.iterdir() if path.is_file() and path.name != "manifest.json")
    manifest = {
        "generator": "yottaflex-finance-management", "seed": seed,
        "users_requested": users, "users_generated": len(profiles),
        "transactions_requested": transactions, "months_requested": months,
        "months": months_list, "currency": "INR",
        "amount_convention": "expenses negative; income/refunds positive",
        "ground_truth_directory": str(truth_dir),
        "files": {path.name: {"sha256": sha256_file(path), "bytes": path.stat().st_size} for path in files},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("Dataset generation complete.")
    print(f"Output directory: {out.resolve()}")
    print(f"Ground truth: {truth_dir.resolve()}")
    print(f"Users: {len(profiles):,}")
    print(f"Transactions: {transactions:,}")
    print(f"Recurring series: {len(recurring):,}")
    print(f"Scheduled recurring transactions generated: {len(scheduled_transactions):,}")
    print(f"Budgets: {len(budgets):,}")
    print(f"Seed: {seed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate reproducible synthetic finance data.")
    parser.add_argument("--users", type=int, default=1000)
    parser.add_argument("--transactions", type=int, default=500000)
    parser.add_argument("--months", type=int, default=12)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--out", default="data/generated")
    args = parser.parse_args()
    generate_dataset(users=args.users, transactions=args.transactions, months=args.months, seed=args.seed, out=args.out)
