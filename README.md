# Payment Reconciliation Prototype

This repository contains a working reconciliation prototype for matching a payments platform dataset against a bank settlement dataset at month-end.

## What is included

- `generate_data.py` — synthetic data generator for `data/transactions.csv` and `data/settlements.csv`
- `reconcile.py` — core reconciliation engine and summary builder
- `report.py` — CSV report writer and readable console summary printer
- `main.py` — end-to-end runner for data generation, reconciliation, report writing, and summary output
- `dashboard.py` — simple web dashboard using Streamlit

## Assumptions

- Currency is USD, with 2-decimal precision.
- All timestamps and settlement dates are treated as UTC.
- Reconciliation is performed per calendar month, based on the transaction timestamp.
- A bank settlement delay of 1–2 days is simulated.
- A settlement outside the transaction month is classified as `late`.
- `transaction_id` is the primary join key and is unique in the transactions dataset.
- A settlement may have `transaction_id` blank/null for refunds.
- Duplicate settlements are rows with the same `(transaction_id, settled_amount, settlement_date)` values.
- Orphan refunds are settlement rows with no matching transaction ID.
- Amount tolerance is zero cents; even a $0.01 discrepancy is flagged.

## Usage

1. Generate synthetic data:

```bash
python generate_data.py
```

2. Run reconciliation end-to-end:

```bash
python main.py
```

3. Use report files in `reports/` and the generated `reports/summary.csv` for discrepancy counts and impacts.

4. Run tests:

```bash
python test_reconcile.py
```

5. Launch the web dashboard:

```bash
streamlit run dashboard.py
```

## Dashboard

The dashboard provides a simple web interface to:
- Run reconciliation on the fly
- Run the edge-case test suite with a button
- View summary statistics
- Browse detailed CSV reports in tabs
- See a bar chart of financial impacts

Open your browser to the URL shown after running `streamlit run dashboard.py`.

## Deployment

### Local Development
- Install dependencies: `pip install streamlit`
- Run the dashboard: `streamlit run dashboard.py`

### Server Deployment
- For production, deploy Streamlit apps on platforms like Heroku, AWS, or use Streamlit Cloud.
- Example for Heroku:
  1. Create a `requirements.txt` with `streamlit`, `pandas`, etc.
  2. Add a `Procfile` with `web: streamlit run dashboard.py --server.port $PORT --server.headless true`
  3. Deploy via Heroku CLI.

### CLI-Only Deployment
- Run `python main.py` on a server via cron jobs or scheduled tasks.
- Output CSVs can be emailed or uploaded to cloud storage.

The pipeline writes the following CSVs to `reports/`:

- `matched.csv`
- `missing_settlements.csv`
- `late_settlements.csv`
- `amount_mismatches.csv`
- `split_settlements.csv`
- `duplicate_settlements.csv`
- `orphan_refunds.csv`
- `summary.csv`

## Edge cases included in synthetic data

- A transaction settled in the following month
- A rounding mismatch of $0.01
- A duplicate settlement row
- A split settlement for the same transaction (two settlement rows)
- Refunds linked to an original transaction
- An orphan refund with no original transaction
- Missing settlement entries
