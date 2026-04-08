"""
generate_data.py
----------------
Generates synthetic transactions.csv and settlements.csv with realistic
volume (~700 rows each) and intentional edge cases for reconciliation testing.

Edge Cases Injected:
  1. Late settlement  – settled in the following month (Jan → Feb)
  2. Rounding mismatch – individual amounts differ by $0.01 due to float truncation
  3. Duplicate entry  – one settlement row duplicated
  4. Orphan refund    – negative-amount settlement with no matching transaction_id
"""

import csv
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

# ---------------------------------------------------------------------------
# helper functions
# ---------------------------------------------------------------------------

def rand_amount(lo=5.0, hi=2000.0) -> float:
    """Return a dollar amount rounded to 2 decimal places."""
    return round(random.uniform(lo, hi), 2)

def rand_timestamp(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))

def settlement_date(ts: datetime, min_days=1, max_days=2) -> datetime:
    """Simulate T+1 / T+2 bank settlement."""
    return ts + timedelta(days=random.randint(min_days, max_days))


def format_settlement_date(value):
    """Return a YYYY-MM-DD string for datetime or date inputs."""
    if isinstance(value, datetime):
        value = value.date()
    return value.isoformat()

# ---------------------------------------------------------------------------
# Synthetic data builder
# ---------------------------------------------------------------------------

def month_bounds(year: int, month: int):
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    else:
        end = datetime(year, month + 1, 1) - timedelta(seconds=1)
    return start, end


def build_transactions(year: int = 2024, month: int = 1, count: int = 680):
    start, end = month_bounds(year, month)
    out = []
    for _ in range(count):
        out.append({
            "transaction_id": str(uuid.uuid4()),
            "timestamp":      rand_timestamp(start, end).isoformat(),
            "amount":         rand_amount(),
            "customer_id":    f"CUST{random.randint(1000, 9999)}",
        })
    return out


def next_month_date(year: int, month: int):
    if month == 12:
        return datetime(year + 1, 1, 2)
    return datetime(year, month + 1, 2)


def build_settlements(transactions: list[dict], year: int = 2024, month: int = 1):
    settlements = []
    late_idx = random.randint(50, min(150, len(transactions) - 1))
    rounding_idx = random.randint(200, min(300, len(transactions) - 1))
    duplicate_idx = random.randint(400, min(500, len(transactions) - 1))
    split_indices = random.sample(range(20, max(21, len(transactions) - 20)), k=5)
    refund_indices = random.sample(range(20, max(21, len(transactions) - 20)), k=3)

    batch_dates = [datetime(year, month, day).date() for day in random.sample(range(2, 28), 4)]

    for i, txn in enumerate(transactions):
        ts = datetime.fromisoformat(txn["timestamp"])
        amt = txn["amount"]
        if i % 20 == 0:
            s_date = random.choice(batch_dates)
        else:
            s_date = settlement_date(ts)

        if i == late_idx:
            s_date = next_month_date(year, month)

        if i == rounding_idx:
            amt = round(amt - 0.01, 2)

        if i in split_indices:
            first_amt = round(amt * random.uniform(0.3, 0.7), 2)
            second_amt = round(amt - first_amt, 2)
            if second_amt <= 0:
                first_amt = round(amt / 2, 2)
                second_amt = round(amt - first_amt, 2)

            settlements.append({
                "settlement_id":   str(uuid.uuid4()),
                "transaction_id":  txn["transaction_id"],
                "settlement_date": format_settlement_date(s_date),
                "settled_amount":  first_amt,
            })
            settlements.append({
                "settlement_id":   str(uuid.uuid4()),
                "transaction_id":  txn["transaction_id"],
                "settlement_date": format_settlement_date(s_date),
                "settled_amount":  second_amt,
            })
            continue

        row = {
            "settlement_id":   str(uuid.uuid4()),
            "transaction_id":  txn["transaction_id"],
            "settlement_date": format_settlement_date(s_date),
            "settled_amount":  amt,
        }
        settlements.append(row)

        if i == duplicate_idx:
            settlements.append(dict(row))

        if i in refund_indices:
            refund_amount = -round(min(amt * random.uniform(0.1, 0.5), amt - 1.00), 2)
            settlements.append({
                "settlement_id":   str(uuid.uuid4()),
                "transaction_id":  txn["transaction_id"],
                "settlement_date": format_settlement_date(s_date),
                "settled_amount":  refund_amount,
            })

    for _ in range(3):
        settlements.append({
            "settlement_id":   str(uuid.uuid4()),
            "transaction_id":  None,
            "settlement_date": datetime(year, month, 15).date().isoformat(),
            "settled_amount":  -round(random.uniform(20, 300), 2),
        })

    no_settle_txns = transactions[-15:]
    for txn in no_settle_txns:
        settlements = [s for s in settlements if s["transaction_id"] != txn["transaction_id"]]

    return settlements


# ---------------------------------------------------------------------------
# Write the generated CSV files
# ---------------------------------------------------------------------------

TXN_FIELDS = ["transaction_id", "timestamp", "amount", "customer_id"]
SET_FIELDS = ["settlement_id", "transaction_id", "settlement_date", "settled_amount"]


def generate_synthetic_data(
    txn_path: str = "data/transactions.csv",
    set_path: str = "data/settlements.csv",
    month: int = 1,
    year: int = 2024,
    num_normal: int = 680,
) -> None:
    transactions = build_transactions(year=year, month=month, count=num_normal)
    settlements = build_settlements(transactions, year=year, month=month)

    Path(txn_path).parent.mkdir(parents=True, exist_ok=True)
    Path(set_path).parent.mkdir(parents=True, exist_ok=True)

    with open(txn_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TXN_FIELDS)
        w.writeheader()
        w.writerows(transactions)

    with open(set_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SET_FIELDS)
        w.writeheader()
        w.writerows(settlements)

    print(f"Generated {len(transactions)} transactions for {year}-{month:02d}.")
    print(f"Generated {len(settlements)} settlement rows.")
    print(f"Files written to {txn_path} and {set_path}")


if __name__ == "__main__":
    generate_synthetic_data()
