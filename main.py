"""
main.py
-------
End-to-end CLI runner.

Usage:
  python main.py                          # uses default paths
  python main.py --transactions data/transactions.csv \\
                 --settlements  data/settlements.csv  \\
                 --output       reports/
"""

import argparse
import subprocess
import sys
from pathlib import Path

from generate_data import generate_synthetic_data
from reconcile import load_csv, parse_transactions, parse_settlements, reconcile, build_summary
from report import write_reports, print_summary


# ---------------------------------------------------------------------------
# make sure data files match the selected month/year
# ---------------------------------------------------------------------------

def csv_period_matches(path: str, month: int, year: int) -> bool:
    import csv
    from datetime import datetime

    if not Path(path).exists():
        return False

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        first = next(reader, None)
        if not first or "timestamp" not in first:
            return False

        try:
            ts = datetime.fromisoformat(first["timestamp"])
            return ts.year == year and ts.month == month
        except Exception:
            return False


def ensure_data(txn_path: str, set_path: str, month: int, year: int):
    if (
        not Path(txn_path).exists()
        or not Path(set_path).exists()
        or not csv_period_matches(txn_path, month, year)
    ):
        print("Data files missing or wrong period – regenerating for selected month/year...")
        generate_synthetic_data(txn_path, set_path, month=month, year=year)


# ---------------------------------------------------------------------------
# command line pipeline
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Payment Reconciliation Engine")
    parser.add_argument("--transactions", default="data/transactions.csv")
    parser.add_argument("--settlements",  default="data/settlements.csv")
    parser.add_argument("--output",       default="reports")
    parser.add_argument("--month",        default=1,    type=int, help="Reconciliation month (1-12)")
    parser.add_argument("--year",         default=2024, type=int, help="Reconciliation year")
    parser.add_argument("--skip-tests",   action="store_true",    help="Skip test suite")
    args = parser.parse_args()

    # --- Step 0: Ensure data exists ---
    ensure_data(args.transactions, args.settlements, args.month, args.year)

    # --- Step 1: Run tests unless skipped ---
    if not args.skip_tests:
        print("\n🧪  Running test suite...\n")
        result = subprocess.run(
            [sys.executable, "test_reconcile.py"],
            capture_output=False
        )
        if result.returncode != 0:
            print("\n⚠️  Tests failed. Proceeding anyway – check output above.\n")

    # --- Step 2: Load data ---
    print("\n📂  Loading data files...")
    raw_txns   = load_csv(args.transactions)
    raw_sets   = load_csv(args.settlements)
    print(f"    Transactions: {len(raw_txns)} rows")
    print(f"    Settlements:  {len(raw_sets)} rows")

    transactions = parse_transactions(raw_txns)
    settlements  = parse_settlements(raw_sets)

    # --- Step 3: Reconcile ---
    print("\n🔎  Running reconciliation...")
    results = reconcile(
        transactions,
        settlements,
        recon_month=args.month,
        recon_year=args.year,
    )

    # --- Step 4: Write reports ---
    write_reports(results, out_dir=args.output)

    # --- Step 5: Print summary ---
    month_label = f"{['','January','February','March','April','May','June','July','August','September','October','November','December'][args.month]} {args.year}"
    summary = build_summary(results)
    print_summary(summary, recon_month=month_label)

    # --- Step 6: Write master summary CSV ---
    import csv
    summary_path = Path(args.output) / "summary.csv"
    with open(summary_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["category","count","financial_impact_usd"])
        w.writeheader()
        for cat, info in summary.items():
            w.writerow({"category": cat, **info})
    print(f"  Summary CSV → {summary_path}\n")


if __name__ == "__main__":
    main()
