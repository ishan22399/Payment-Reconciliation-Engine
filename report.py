"""
report.py
---------
Save reconciliation results to CSV files and print a short summary.
"""

import csv
from pathlib import Path
from datetime import date


# ---------------------------------------------------------------------------
# write CSV files
# ---------------------------------------------------------------------------

def _write_csv(path: str, fieldnames: list[str], rows: list[dict]):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def flatten_matched(items):
    out = []
    for i in items:
        t, s = i["transaction"], i["settlement"]
        out.append({
            "transaction_id":  t["transaction_id"],
            "customer_id":     t["customer_id"],
            "txn_amount":      t["amount"],
            "settlement_id":   s["settlement_id"],
            "settled_amount":  s["settled_amount"],
            "settlement_date": s["settlement_date"],
        })
    return out


def flatten_missing(items):
    out = []
    for i in items:
        t = i["transaction"]
        out.append({
            "transaction_id": t["transaction_id"],
            "customer_id":    t["customer_id"],
            "txn_amount":     t["amount"],
            "timestamp":      t["timestamp"].isoformat(),
        })
    return out


def flatten_late(items):
    out = []
    for i in items:
        t = i["transaction"]
        settlements = i.get("settlements") or []
        if not isinstance(settlements, list):
            settlements = [settlements]

        settlement_ids = ";".join(s["settlement_id"] for s in settlements)
        settlement_dates = ";".join(str(s["settlement_date"]) for s in settlements)
        settled_months = ";".join(s["settlement_date"].strftime("%Y-%m") for s in settlements)

        out.append({
            "transaction_id":  t["transaction_id"],
            "customer_id":     t["customer_id"],
            "txn_amount":      t["amount"],
            "txn_month":       t["timestamp"].strftime("%Y-%m"),
            "settlement_id":   settlement_ids,
            "settlement_date": settlement_dates,
            "settled_month":   settled_months,
        })
    return out


def flatten_mismatches(items):
    out = []
    for i in items:
        t = i["transaction"]
        settlements = i.get("settlements") or i.get("settlement")

        if settlements is None:
            settlement_ids = ""
            settlement_dates = ""
        elif isinstance(settlements, list):
            settlement_ids = ";".join(s["settlement_id"] for s in settlements)
            settlement_dates = ";".join(str(s["settlement_date"]) for s in settlements)
        else:
            settlement_ids = settlements["settlement_id"]
            settlement_dates = str(settlements["settlement_date"])

        out.append({
            "transaction_id":  t["transaction_id"],
            "customer_id":     t["customer_id"],
            "expected_amount": i["expected_amount"],
            "settled_amount":  i["settled_amount"],
            "difference":      i["difference"],
            "settlement_id":   settlement_ids,
            "settlement_date": settlement_dates,
        })
    return out


def flatten_split_settlements(items):
    out = []
    for i in items:
        t = i["transaction"]
        settlements = i["settlements"]
        settlement_ids = ";".join(s["settlement_id"] for s in settlements)
        settlement_dates = ";".join(str(s["settlement_date"]) for s in settlements)
        settlement_amounts = ";".join(str(s["settled_amount"]) for s in settlements)
        out.append({
            "transaction_id":  t["transaction_id"],
            "customer_id":     t["customer_id"],
            "txn_amount":      t["amount"],
            "settlement_ids":  settlement_ids,
            "settlement_dates": settlement_dates,
            "settled_amounts": settlement_amounts,
            "total_settled":   i["total_settled"],
        })
    return out


def flatten_duplicates(items):
    out = []
    for i in items:
        out.append({
            "settlement_id":   i["settlement_id"],
            "transaction_id":  i["transaction_id"],
            "settlement_date": i["settlement_date"],
            "settled_amount":  i["settled_amount"],
        })
    return out


def flatten_orphans(items):
    out = []
    for i in items:
        out.append({
            "settlement_id":   i["settlement_id"],
            "transaction_id":  i["transaction_id"],   # None
            "settlement_date": i["settlement_date"],
            "settled_amount":  i["settled_amount"],
        })
    return out


# ---------------------------------------------------------------------------
# write all reports
# ---------------------------------------------------------------------------

def write_reports(results: dict, out_dir: str = "reports"):
    p = Path(out_dir)

    _write_csv(
        p / "matched.csv",
        ["transaction_id","customer_id","txn_amount","settlement_id","settled_amount","settlement_date"],
        flatten_matched(results["matched"]),
    )
    _write_csv(
        p / "missing_settlements.csv",
        ["transaction_id","customer_id","txn_amount","timestamp"],
        flatten_missing(results["missing"]),
    )
    _write_csv(
        p / "late_settlements.csv",
        ["transaction_id","customer_id","txn_amount","txn_month","settlement_id","settlement_date","settled_month"],
        flatten_late(results["late"]),
    )
    _write_csv(
        p / "amount_mismatches.csv",
        ["transaction_id","customer_id","expected_amount","settled_amount","difference","settlement_id","settlement_date"],
        flatten_mismatches(results["amount_mismatch"]),
    )
    _write_csv(
        p / "split_settlements.csv",
        ["transaction_id","customer_id","txn_amount","settlement_ids","settlement_dates","settled_amounts","total_settled"],
        flatten_split_settlements(results["split_settlements"]),
    )
    _write_csv(
        p / "duplicate_settlements.csv",
        ["settlement_id","transaction_id","settlement_date","settled_amount"],
        flatten_duplicates(results["duplicates"]),
    )
    _write_csv(
        p / "orphan_refunds.csv",
        ["settlement_id","transaction_id","settlement_date","settled_amount"],
        flatten_orphans(results["orphan_refunds"]),
    )

    print(f"\n✅  CSV reports written to {out_dir}/")


# ---------------------------------------------------------------------------
# print a simple summary
# ---------------------------------------------------------------------------

def print_summary(summary: dict, recon_month: str = "January 2024"):
    divider = "=" * 60
    print(f"\n{divider}")
    print(f"  RECONCILIATION REPORT  –  {recon_month}")
    print(divider)

    labels = {
        "matched":         "✅  Clean matches",
        "missing":         "❌  Missing settlements",
        "late":            "⏰  Late settlements",
        "amount_mismatch": "⚠️   Amount mismatches",
        "split_settlements": "🔀  Split settlements",
        "duplicates":      "🔁  Duplicate entries",
        "orphan_refunds":  "👻  Orphan refunds",
    }

    for key, info in summary.items():
        label  = labels.get(key, key)
        count  = info["count"]
        impact = info["financial_impact_usd"]
        if key == "matched":
            print(f"  {label:<35}  {count:>5} rows")
        else:
            sign = "+" if impact > 0 else ""
            print(f"  {label:<35}  {count:>5} rows   ${sign}{impact:,.2f} exposure")

    total_exposure = sum(
        v["financial_impact_usd"]
        for k, v in summary.items()
        if k != "matched"
    )
    print(divider)
    print(f"  {'TOTAL FINANCIAL EXPOSURE':<35}         ${total_exposure:,.2f}")
    print(divider)
