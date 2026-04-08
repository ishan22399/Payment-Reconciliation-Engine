# Payment Reconciliation Engine

A production-ready reconciliation prototype for matching transaction data from a payments platform against bank settlement records.

## Summary

This project is designed to demonstrate end-to-end payment reconciliation workflows with realistic synthetic datasets, edge-case detection, CSV reporting, and a Streamlit dashboard interface.

## Repository Contents

- `generate_data.py` — Generate synthetic transaction and settlement datasets with built-in edge cases.
- `reconcile.py` — Core reconciliation engine, including classification for matches, missing settlements, late settlements, amount mismatches, duplicates, split settlements, and orphan refunds.
- `report.py` — Export reconciliation results to detailed CSV reports.
- `main.py` — CLI entrypoint for generating data, running reconciliation, and writing reports.
- `dashboard.py` — Streamlit web dashboard to drive reconciliation, view summary metrics, and inspect detailed report data.
- `test_reconcile.py` — Edge-case test suite for validating reconciliation behavior.
- `requirements.txt` — Python dependencies required to run the app.

## Key Assumptions

- Currency is assumed to be USD.
- Amounts are rounded to two decimal places.
- Reconciliation is performed per calendar month based on transaction timestamps.
- Settlements that fall outside the transaction month are treated as late.
- `transaction_id` is the primary join key.
- Refunds may appear as settlement rows with no matching transaction ID.
- Duplicate settlements are defined as repeated rows with the same `(transaction_id, settled_amount, settlement_date)`.
- The reconciliation pipeline is strict on amount equality: even a $0.01 difference is reported.

## Usage

### Generate test data

```bash
python generate_data.py
```

### Run reconciliation

```bash
python main.py
```

### Launch the dashboard

```bash
streamlit run dashboard.py
```

### Run tests

```bash
python test_reconcile.py
```

## Output

The reconciliation process produces scoped CSV reports in `reports/`:

- `matched.csv`
- `missing_settlements.csv`
- `late_settlements.csv`
- `amount_mismatches.csv`
- `split_settlements.csv`
- `duplicate_settlements.csv`
- `orphan_refunds.csv`
- `summary.csv`

## Deployment

### Recommended deployment

This app is best deployed as a Streamlit application.

1. Push the repository to GitHub.
2. Use Streamlit Community Cloud to deploy `dashboard.py` directly.
3. Configure the app to use `requirements.txt` for dependencies.

### Alternative deployment

- Deploy on any Python-friendly host that supports Streamlit.
- For CLI-only automation, schedule `python main.py` on a server and consume the generated `reports/*.csv` outputs.

## Included Reconciliation Edge Cases

- Late settlement in the next month.
- Amount rounding discrepancy of $0.01.
- Duplicate settlement entry.
- Split settlement across two rows.
- Linked refund associated with an original transaction.
- Orphan refund with no transaction match.
- Missing settlement rows.
