"""
tests/test_reconcile.py
-----------------------
A small validation suite for the reconciliation engine.
Each test checks one real-world issue and makes sure normal
transactions still match cleanly.
"""

import sys
import uuid
from datetime import datetime, date

sys.path.insert(0, "..")

from reconcile import reconcile, find_duplicate_settlements

# ---------------------------------------------------------------------------
# helper functions for tests
# ---------------------------------------------------------------------------

def make_txn(amount=100.00, month=1, year=2024, txn_id=None):
    return {
        "transaction_id": txn_id or str(uuid.uuid4()),
        "timestamp":      datetime(year, month, 15, 12, 0, 0),
        "amount":         round(amount, 2),
        "customer_id":    "CUST0001",
    }

def make_settlement(txn_id, amount=100.00, month=1, year=2024, s_id=None):
    return {
        "settlement_id":   s_id or str(uuid.uuid4()),
        "transaction_id":  txn_id,
        "settlement_date": date(year, month, 17),
        "settled_amount":  round(amount, 2),
    }

def run_recon(txns_list, settlements):
    txns_dict = {t["transaction_id"]: t for t in txns_list}
    return reconcile(txns_dict, settlements)

TEST_DESCRIPTIONS = {
    "test_clean_match": "A normal transaction matches a settlement exactly.",
    "test_missing_settlement": "A transaction has no settlement record at all.",
    "test_late_settlement": "A settlement occurs in the following month.",
    "test_amount_mismatch": "The settled amount is off by a penny.",
    "test_duplicate_settlement": "The same settlement row appears twice.",
    "test_split_settlement": "One transaction is settled in two rows that total the original amount.",
    "test_linked_refund_exact": "A linked refund nets out exactly to the original amount.",
    "test_linked_refund_mismatch": "A linked refund causes the transaction to be out of balance.",
    "test_orphan_refund": "A refund appears without any original transaction ID.",
    "test_mixed_batch": "A batch containing clean, missing, late, and mismatched cases.",
}


# ---------------------------------------------------------------------------
# clean match scenario
# ---------------------------------------------------------------------------

def test_clean_match():
    txn = make_txn(amount=250.00)
    s   = make_settlement(txn["transaction_id"], amount=250.00)
    r   = run_recon([txn], [s])

    assert len(r["matched"])         == 1, "Should have 1 clean match"
    assert len(r["missing"])         == 0
    assert len(r["late"])            == 0
    assert len(r["amount_mismatch"]) == 0
    assert len(r["duplicates"])      == 0
    assert len(r["orphan_refunds"])  == 0
    print("PASS  test_clean_match")


# ---------------------------------------------------------------------------
# missing settlement scenario
# ---------------------------------------------------------------------------

def test_missing_settlement():
    txn = make_txn(amount=150.00)
    r   = run_recon([txn], [])   # run with no settlement rows

    assert len(r["missing"]) == 1, "Should flag 1 missing settlement"
    assert r["missing"][0]["transaction"]["transaction_id"] == txn["transaction_id"]
    print("PASS  test_missing_settlement")


# ---------------------------------------------------------------------------
# late settlement scenario
# ---------------------------------------------------------------------------

def test_late_settlement():
    txn = make_txn(amount=300.00, month=1)
    s   = make_settlement(txn["transaction_id"], amount=300.00, month=2)  # February
    r   = run_recon([txn], [s])

    assert len(r["late"])    == 1, "Should flag 1 late settlement"
    assert len(r["matched"]) == 0
    print("PASS  test_late_settlement")


# ---------------------------------------------------------------------------
# amount mismatch scenario
# ---------------------------------------------------------------------------

def test_amount_mismatch():
    txn = make_txn(amount=99.99)
    s   = make_settlement(txn["transaction_id"], amount=99.98)  # 1 cent short
    r   = run_recon([txn], [s])

    assert len(r["amount_mismatch"]) == 1, "Should flag 1 amount mismatch"
    assert r["amount_mismatch"][0]["difference"] == 0.01
    print("PASS  test_amount_mismatch")


# ---------------------------------------------------------------------------
# duplicate settlement scenario
# ---------------------------------------------------------------------------

def test_duplicate_settlement():
    txn = make_txn(amount=500.00)
    s   = make_settlement(txn["transaction_id"], amount=500.00)
    dup = dict(s)  # duplicate settlement row

    dupes = find_duplicate_settlements([s, dup])
    assert len(dupes) == 2, "Both rows in the duplicate pair should be returned"
    print("PASS  test_duplicate_settlement")


# ---------------------------------------------------------------------------
# split settlement scenario
# ---------------------------------------------------------------------------

def test_split_settlement():
    txn = make_txn(amount=500.00)
    s1  = make_settlement(txn["transaction_id"], amount=200.00)
    s2  = make_settlement(txn["transaction_id"], amount=300.00)
    r   = run_recon([txn], [s1, s2])

    assert len(r["split_settlements"]) == 1, "Should flag 1 split settlement"
    assert r["split_settlements"][0]["total_settled"] == 500.00
    print("PASS  test_split_settlement")


def test_linked_refund_exact():
    txn = make_txn(amount=500.00)
    s1  = make_settlement(txn["transaction_id"], amount=520.00)
    refund = {
        "settlement_id":   str(uuid.uuid4()),
        "transaction_id":  txn["transaction_id"],
        "settlement_date": date(2024, 1, 18),
        "settled_amount":  -20.00,
    }
    r   = run_recon([txn], [s1, refund])

    assert len(r["split_settlements"]) == 1, "Exact linked refund should appear as split settlement"
    assert r["split_settlements"][0]["total_settled"] == 500.00
    print("PASS  test_linked_refund_exact")


def test_linked_refund_mismatch():
    txn = make_txn(amount=500.00)
    s1  = make_settlement(txn["transaction_id"], amount=500.00)
    refund = {
        "settlement_id":   str(uuid.uuid4()),
        "transaction_id":  txn["transaction_id"],
        "settlement_date": date(2024, 1, 18),
        "settled_amount":  -20.00,
    }
    r   = run_recon([txn], [s1, refund])

    assert len(r["amount_mismatch"]) == 1, "Linked refund should create an amount mismatch when totals differ"
    assert r["amount_mismatch"][0]["difference"] == 20.00
    print("PASS  test_linked_refund_mismatch")


# ---------------------------------------------------------------------------
# orphan refund scenario
# ---------------------------------------------------------------------------

def test_orphan_refund():
    orphan = {
        "settlement_id":   str(uuid.uuid4()),
        "transaction_id":  None,
        "settlement_date": date(2024, 1, 20),
        "settled_amount":  -75.00,
    }
    r = run_recon([], [orphan])

    assert len(r["orphan_refunds"]) == 1, "Should flag 1 orphan refund"
    assert r["orphan_refunds"][0]["settled_amount"] == -75.00
    print("PASS  test_orphan_refund")


# ---------------------------------------------------------------------------
# mixed batch scenario
# ---------------------------------------------------------------------------

def test_mixed_batch():
    t1 = make_txn(amount=100.00)  # expected to match
    t2 = make_txn(amount=200.00)  # expected to be missing
    t3 = make_txn(amount=300.00)  # expected to be late
    t4 = make_txn(amount=400.00)  # expected to mismatch

    s1 = make_settlement(t1["transaction_id"], 100.00, month=1)
    s3 = make_settlement(t3["transaction_id"], 300.00, month=2)   # late
    s4 = make_settlement(t4["transaction_id"], 399.50, month=1)   # -$0.50

    r = run_recon([t1, t2, t3, t4], [s1, s3, s4])

    assert len(r["matched"])         == 1, f"Expected 1 matched, got {len(r['matched'])}"
    assert len(r["missing"])         == 1, f"Expected 1 missing, got {len(r['missing'])}"
    assert len(r["late"])            == 1, f"Expected 1 late, got {len(r['late'])}"
    assert len(r["amount_mismatch"]) == 1, f"Expected 1 mismatch, got {len(r['amount_mismatch'])}"
    print("PASS  test_mixed_batch")


# ---------------------------------------------------------------------------
# run the test suite
# ---------------------------------------------------------------------------

def run_all_tests():
    tests = [
        test_clean_match,
        test_missing_settlement,
        test_late_settlement,
        test_amount_mismatch,
        test_duplicate_settlement,
        test_split_settlement,
        test_linked_refund_exact,
        test_linked_refund_mismatch,
        test_orphan_refund,
        test_mixed_batch,
    ]

    results = []
    failures = 0
    for t in tests:
        try:
            t()
            results.append({
                "name": t.__name__,
                "passed": True,
                "message": "Passed",
                "description": TEST_DESCRIPTIONS.get(t.__name__, ""),
            })
        except AssertionError as e:
            results.append({
                "name": t.__name__,
                "passed": False,
                "message": str(e),
                "description": TEST_DESCRIPTIONS.get(t.__name__, ""),
            })
            failures += 1
        except Exception as e:
            results.append({
                "name": t.__name__,
                "passed": False,
                "message": str(e),
                "description": TEST_DESCRIPTIONS.get(t.__name__, ""),
            })
            failures += 1
    return results


if __name__ == "__main__":
    print("\n--- Running reconciliation tests ---\n")
    results = run_all_tests()
    failures = sum(1 for r in results if not r["passed"])
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"{status}  {r['name']}{': ' + r['message'] if r['message'] else ''}")
    print(f"\n{'All tests passed ✅' if failures == 0 else f'{failures} test(s) failed ❌'}\n")
