# Payment Reconciliation Engine

A professional payment reconciliation prototype that matches transaction records to bank settlement data and highlights exceptions.

## Live Deployment

- Streamlit app: https://payment-reconciliation-engine-4u6jfti2mnatandfewglxx.streamlit.app/

## Features

- Synthetic transaction and settlement data generation
- Reconciliation of payments against bank settlement records
- Detailed classification of exceptions
- Export of exception reports to CSV
- Interactive Streamlit dashboard for review and analysis

## Supported Rules

- Missing settlement detection
- Late settlement identification
- Amount mismatches
- Split settlement handling
- Duplicate settlement detection
- Orphan refund classification

## Tech Stack

- Python 3.11+ compatible
- Streamlit for dashboard UI
- pandas for data handling
- CSV-based input/output for portability

## Repository Structure

- `dashboard.py` — Streamlit application for interactive reconciliation
- `main.py` — CLI workflow for generating data and running reconciliation
- `generate_data.py` — synthetic data generation with real-world edge cases
- `reconcile.py` — reconciliation engine and result classification
- `report.py` — CSV report generation
- `test_reconcile.py` — regression tests for reconciliation scenarios
- `requirements.txt` — dependency list
- `LICENSE` — project license

## Getting Started

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the dashboard:

```bash
streamlit run dashboard.py
```

Alternatively, run the CLI flow:

```bash
python main.py
```

Run the test suite:

```bash
python test_reconcile.py
```

## Deployment

This app is optimized for Streamlit deployment.

Recommended deployment options:
- Streamlit Community Cloud
- Render
- Railway

## License

This project is licensed under the MIT License. See [LICENSE] for details.
