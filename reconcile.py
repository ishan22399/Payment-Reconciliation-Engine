"""
reconcile.py
------------
Core reconciliation logic for matching transactions with settlements.

Assumptions are documented in README and cover currency, timezone,
calendar month reconciliation, late settlement detection, rounding tolerance,
and how refunds and duplicates are handled.
"""

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# load CSV files
# ---------------------------------------------------------------------------

def load_csv(path: str) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def parse_transactions(rows: list[dict]) -> dict[str, dict]:
    """Convert transaction rows into typed transaction objects."""
    out = {}
    for r in rows:
        out[r["transaction_id"]] = {
            "transaction_id": r["transaction_id"],
            "timestamp":      datetime.fromisoformat(r["timestamp"]),
            "amount":         round(float(r["amount"]), 2),
            "customer_id":    r["customer_id"],
        }
    return out


def parse_settlements(rows: list[dict]) -> list[dict]:
    """Convert settlement rows into typed settlement objects."""
    out = []
    for r in rows:
        raw_date = r["settlement_date"]
        try:
            settlement_dt = datetime.fromisoformat(raw_date)
            settlement_date = settlement_dt.date()
        except ValueError:
            settlement_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
        out.append({
            "settlement_id":   r["settlement_id"],
            "transaction_id":  r["transaction_id"] if r["transaction_id"] else None,
            "settlement_date": settlement_date,
            "settled_amount":  round(float(r["settled_amount"]), 2),
        })
    return out


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------

def find_duplicate_settlements(settlements: list[dict]) -> list[dict]:
    """
    Find settlement rows that repeat the same transaction, amount, and date.
    Returns all rows that are part of any duplicate group.

    Banks can send the same batch twice, so we flag repeated rows here.
    """
    seen = defaultdict(list)
    for s in settlements:
        key = (s["transaction_id"], s["settled_amount"], str(s["settlement_date"]))
        seen[key].append(s)

    duplicates = []
    for key, group in seen.items():
        if len(group) > 1:
            duplicates.extend(group)
    return duplicates


# ---------------------------------------------------------------------------
# compare transactions with settlements
# ---------------------------------------------------------------------------

def reconcile(
    transactions: dict[str, dict],
    settlements: list[dict],
    recon_month: int = 1,
    recon_year:  int = 2024,
    amount_tolerance: float = 0.00,
) -> dict:
    """
    Match every transaction to its settlement(s) and classify discrepancies.

    Returns a dict with keys:
      matched          – clean, correct pairs
      missing          – transactions with no settlement at all
      late             – settlement exists but settlement_date is outside month
      amount_mismatch  – amounts differ beyond tolerance
      duplicates       – duplicate settlement rows
      orphan_refunds   – settlements with no transaction_id
    """

    results = {
        "matched":         [],
        "missing":         [],
        "late":            [],
        "amount_mismatch": [],
        "split_settlements": [],
        "duplicates":      [],
        "orphan_refunds":  [],
    }

    # Only examine transactions for the requested reconciliation period.
    period_transactions = {
        tid: txn
        for tid, txn in transactions.items()
        if (txn["timestamp"].year, txn["timestamp"].month) == (recon_year, recon_month)
    }

    # --- Step 1: Separate orphan refunds (no transaction_id) ---
    orphans   = [
        s for s in settlements
        if s["transaction_id"] is None
           and (s["settlement_date"].year, s["settlement_date"].month) == (recon_year, recon_month)
    ]
    linked    = [s for s in settlements if s["transaction_id"] is not None]

    results["orphan_refunds"] = orphans

    # --- Step 2: Flag duplicates (before deduplication) ---
    results["duplicates"] = find_duplicate_settlements(linked)

    # Keep the first matching row and ignore repeated duplicates for the rest of reconciliation.
    seen_keys = set()
    deduped = []
    for s in linked:
        key = (s["transaction_id"], s["settled_amount"], str(s["settlement_date"]))
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(s)

    # --- Step 3: Build settlement index by transaction_id ---
    settle_by_txn: dict[str, list[dict]] = defaultdict(list)
    for s in deduped:
        settle_by_txn[s["transaction_id"]].append(s)

    # --- Step 4: Walk every transaction for the requested reconciliation period ---
    for txn_id, txn in period_transactions.items():
        txn_month = txn["timestamp"].month
        txn_year  = txn["timestamp"].year
        matches   = settle_by_txn.get(txn_id, [])

        if not matches:
            # No settlement found at all
            results["missing"].append({"transaction": txn, "settlement": None})
            continue

        total_settled = round(sum(s["settled_amount"] for s in matches), 2)
        any_late = any(
            (s["settlement_date"].year, s["settlement_date"].month) != (txn_year, txn_month)
            for s in matches
        )

        if any_late:
            # If any settlement row lands outside the transaction month, treat as late.
            results["late"].append({"transaction": txn, "settlements": matches})
            continue

        if len(matches) > 1:
            diff = round(abs(txn["amount"] - total_settled), 2)
            if diff <= amount_tolerance:
                results["split_settlements"].append({
                    "transaction": txn,
                    "settlements": matches,
                    "total_settled": total_settled,
                })
                continue

            results["amount_mismatch"].append({
                "transaction":     txn,
                "settlements":     matches,
                "expected_amount": txn["amount"],
                "settled_amount":  total_settled,
                "difference":      round(txn["amount"] - total_settled, 2),
            })
            continue

        s = matches[0]
        diff = abs(txn["amount"] - s["settled_amount"])
        if diff > amount_tolerance:
            results["amount_mismatch"].append({
                "transaction":     txn,
                "settlement":      s,
                "expected_amount": txn["amount"],
                "settled_amount":  s["settled_amount"],
                "difference":      round(txn["amount"] - s["settled_amount"], 2),
            })
            continue

        # All checks passed – clean match
        results["matched"].append({"transaction": txn, "settlement": s})

    return results


# ---------------------------------------------------------------------------
# Summary builder
# ---------------------------------------------------------------------------

def build_summary(results: dict) -> dict:
    """Compute counts and total financial impact per category."""

    def total_txn_amount(items):
        return round(sum(i["transaction"]["amount"] for i in items if i.get("transaction")), 2)

    def total_diff(items):
        return round(sum(i["difference"] for i in items), 2)

    def total_orphan(items):
        return round(sum(abs(i["settled_amount"]) for i in items), 2)

    def total_dup(items):
        # Total amount in duplicated settlement rows
        return round(sum(i["settled_amount"] for i in items), 2)

    summary = {
        "matched":         {"count": len(results["matched"]),
                            "financial_impact_usd": 0.00},
        "missing":         {"count": len(results["missing"]),
                            "financial_impact_usd": total_txn_amount(results["missing"])},
        "late":            {"count": len(results["late"]),
                            "financial_impact_usd": total_txn_amount(results["late"])},
        "amount_mismatch": {"count": len(results["amount_mismatch"]),
                            "financial_impact_usd": total_diff(results["amount_mismatch"])},
        "split_settlements": {"count": len(results["split_settlements"]),
                            "financial_impact_usd": 0.00},
        "duplicates":      {"count": len(results["duplicates"]),
                            "financial_impact_usd": total_dup(results["duplicates"])},
        "orphan_refunds":  {"count": len(results["orphan_refunds"]),
                            "financial_impact_usd": total_orphan(results["orphan_refunds"])},
    }
    return summary
