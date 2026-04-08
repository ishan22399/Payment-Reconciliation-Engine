"""
dashboard.py
------------
A simple web dashboard for the reconciliation results using Streamlit.
Run with: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
from pathlib import Path

# Import our reconciliation modules
from generate_data import generate_synthetic_data
from reconcile import load_csv, parse_transactions, parse_settlements, reconcile, build_summary
from report import write_reports

st.title("Payment Reconciliation Dashboard")

st.sidebar.header("Options")
run_reconciliation = st.sidebar.button("Run Reconciliation")
run_tests = st.sidebar.button("Run Test Suite")
month = st.sidebar.selectbox("Month", list(range(1, 13)), index=0)
year = st.sidebar.selectbox("Year", [2024, 2025, 2026], index=0)


def execute_reconciliation(month: int, year: int):
    txn_path = "data/transactions.csv"
    set_path = "data/settlements.csv"
    generate_synthetic_data(txn_path, set_path, month=month, year=year)

    raw_txns = load_csv(txn_path)
    raw_sets = load_csv(set_path)
    transactions = parse_transactions(raw_txns)
    settlements = parse_settlements(raw_sets)
    results = reconcile(transactions, settlements, recon_month=month, recon_year=year)
    summary = build_summary(results)
    write_reports(results, out_dir="reports")
    return summary, results

if run_tests:
    import sys
    sys.path.insert(0, ".")
    import test_reconcile

    st.header("Test Suite Results")
    st.markdown("Each test case includes a short description so you can understand the business scenario being validated.")
    results = test_reconcile.run_all_tests()
    results_df = pd.DataFrame(results)
    st.dataframe(results_df)

    failed = [r for r in results if not r["passed"]]
    if failed:
        st.error(f"{len(failed)} test(s) failed")
    else:
        st.success("All tests passed ✅")

if run_reconciliation:
    with st.spinner("Generating data and running reconciliation..."):
        summary, results = execute_reconciliation(month, year)
    st.success("Reconciliation complete!")

    # Display summary
    st.header("Summary")
    summary_df = pd.DataFrame(summary).T
    st.dataframe(summary_df)

    # Display charts
    st.header("Financial Impact")
    impact_data = summary_df[summary_df.index != "matched"]["financial_impact_usd"]
    st.bar_chart(impact_data)

    # Display detailed reports
    st.header("Detailed Reports")
    tabs = st.tabs(["Matched", "Missing", "Late", "Mismatches", "Split Settlements", "Duplicates", "Orphan Refunds"])

    with tabs[0]:
        if Path("reports/matched.csv").exists():
            df = pd.read_csv("reports/matched.csv")
            st.dataframe(df)
        else:
            st.write("No matched transactions.")

    with tabs[1]:
        if Path("reports/missing_settlements.csv").exists():
            df = pd.read_csv("reports/missing_settlements.csv")
            st.dataframe(df)
        else:
            st.write("No missing settlements.")

    with tabs[2]:
        if Path("reports/late_settlements.csv").exists():
            df = pd.read_csv("reports/late_settlements.csv")
            st.dataframe(df)
        else:
            st.write("No late settlements.")

    with tabs[3]:
        if Path("reports/amount_mismatches.csv").exists():
            df = pd.read_csv("reports/amount_mismatches.csv")
            st.dataframe(df)
        else:
            st.write("No amount mismatches.")

    with tabs[4]:
        if Path("reports/split_settlements.csv").exists():
            df = pd.read_csv("reports/split_settlements.csv")
            st.dataframe(df)
        else:
            st.write("No split settlements.")

    with tabs[5]:
        if Path("reports/duplicate_settlements.csv").exists():
            df = pd.read_csv("reports/duplicate_settlements.csv")
            st.dataframe(df)
        else:
            st.write("No duplicate settlements.")

    with tabs[6]:
        if Path("reports/orphan_refunds.csv").exists():
            df = pd.read_csv("reports/orphan_refunds.csv")
            st.dataframe(df)
        else:
            st.write("No orphan refunds.")

else:
    st.write("Click 'Run Reconciliation' to generate and analyze data.")