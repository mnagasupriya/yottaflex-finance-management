
from pathlib import Path
import json

import pandas as pd
import streamlit as st


# --------------------------------------------------
# Project paths
# --------------------------------------------------
from src.gemini_helper import generate_budget_insight
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "generated"
GROUND_TRUTH_DIR = BASE_DIR / "data" / "ground_truth"
DOCS_DIR = BASE_DIR / "docs"

st.set_page_config(
    page_title="YottaFlex Finance Manager",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# Styling
# --------------------------------------------------

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    [data-testid="stMetric"] {
        background-color: rgba(128, 128, 128, 0.08);
        padding: 16px;
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.2);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# Data loading helpers
# --------------------------------------------------

@st.cache_data
def load_csv(path_string, modified_time):
    """Load a CSV and cache it until the file changes."""
    path = Path(path_string)
    return pd.read_csv(path, low_memory=False)


def read_csv_file(filename, folder=DATA_DIR):
    path = folder / filename
    if not path.exists():
        return None

    try:
        return load_csv(str(path), path.stat().st_mtime)
    except Exception as exc:
        st.warning(f"Could not read {filename}: {exc}")
        return None


def find_csv_files(folder=DATA_DIR):
    if not folder.exists():
        return []
    return sorted(folder.glob("*.csv"))


def find_file_by_keywords(keywords, folder=DATA_DIR):
    """Find a CSV whose filename contains one of the supplied keywords."""
    files = find_csv_files(folder)
    for keyword in keywords:
        for path in files:
            if keyword.lower() in path.name.lower():
                return path
    return None


def load_first_available(filenames, folder=DATA_DIR):
    for filename in filenames:
        df = read_csv_file(filename, folder)
        if df is not None:
            return df, filename
    return None, None


def show_dataframe(df, key, max_rows=1000):
    if df is None:
        st.info("No data available for this section yet.")
        return

    if df.empty:
        st.info("This report exists, but it contains no rows.")
        return

    st.caption(f"{len(df):,} rows · {len(df.columns):,} columns")

    if len(df) > max_rows:
        st.caption(f"Showing the first {max_rows:,} rows. Download to view all rows.")
        display_df = df.head(max_rows)
    else:
        display_df = df

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "Download CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"{key}.csv",
        mime="text/csv",
        key=f"download_{key}",
    )


def show_metric(label, value, help_text=None):
    st.metric(label, value, help=help_text)


def find_column(df, candidates):
    """Return the first column matching a candidate name, ignoring case."""
    if df is None:
        return None

    lookup = {str(col).strip().lower(): col for col in df.columns}

    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    for col in df.columns:
        normalized = str(col).strip().lower()
        if any(candidate.lower() in normalized for candidate in candidates):
            return col

    return None


def numeric_series(df, candidates):
    column = find_column(df, candidates)
    if column is None:
        return None, None

    values = pd.to_numeric(df[column], errors="coerce")
    return values, column


def show_file_status():
    st.sidebar.caption("Project data")

    for label, path in [
        ("Generated data", DATA_DIR),
        ("Documentation", DOCS_DIR),
    ]:
        st.sidebar.write(
            f"{'✅' if path.exists() else '⚠️'} {label}"
        )


# --------------------------------------------------
# Sidebar navigation
# --------------------------------------------------

st.sidebar.title("💰 YottaFlex")
st.sidebar.caption("Household Finance Management")

page = st.sidebar.radio(
    "Navigate",
    [
        "Overview",
        "Transactions",
        "Budget Analysis",
        "Recurring Payments",
        "Exceptions & Audit",
        "Reports & Data",
    ],
)

show_file_status()

if st.sidebar.button("Refresh dashboard"):
    st.cache_data.clear()
    st.rerun()


# --------------------------------------------------
# Common datasets
# --------------------------------------------------

transactions = read_csv_file("categorized_transactions.csv")

if transactions is None:
    transactions = read_csv_file("transactions.csv")

budget_summary, budget_summary_name = load_first_available(
    [
        "budget_comparison.csv",
        "budget_analysis.csv",
        "budget_status.csv",
        "budget_summary.csv",
        "budget_comparison_results.csv",
    ]
)

exceptions, exceptions_name = load_first_available(
    [
        "budget_exceptions.csv",
        "exceptions.csv",
        "finance_exceptions.csv",
    ]
)

# Discover the recurring reports produced by the current pipeline.
detected_recurring = read_csv_file("detected_recurring_payments.csv")
recurring_series = read_csv_file("recurring_series.csv")
recurring_exceptions = read_csv_file("recurring_cycle_exceptions.csv")


# --------------------------------------------------
# Overview
# --------------------------------------------------

if page == "Overview":
    st.title("Finance Management Dashboard")
    st.write(
        "Categorize transactions, monitor recurring payments, "
        "compare household spending with budgets, and review exceptions."
    )

    total_transactions = (
        len(transactions) if transactions is not None else 0
    )

    st.subheader("Financial snapshot")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        show_metric("Transactions", f"{total_transactions:,}")

    with col2:
        show_metric(
            "Budget comparisons",
            f"{len(budget_summary):,}"
            if budget_summary is not None else "Not loaded",
        )

    with col3:
        show_metric(
            "Recurring candidates",
            f"{len(detected_recurring):,}"
            if detected_recurring is not None else "Not loaded",
        )

    with col4:
        show_metric(
            "Recurring exceptions",
            f"{len(recurring_exceptions):,}"
            if recurring_exceptions is not None else "Not loaded",
        )

    st.divider()
    st.subheader("Budget status")

    if budget_summary is not None and not budget_summary.empty:
        status_col = find_column(
            budget_summary,
            ["budget_status", "status", "budget_state"],
        )

        if status_col:
            counts = (
                budget_summary[status_col]
                .fillna("Unknown")
                .astype(str)
                .value_counts()
            )

            left, right = st.columns([1, 2])

            with left:
                st.dataframe(
                    counts.rename_axis("Status")
                    .reset_index(name="Count"),
                    use_container_width=True,
                    hide_index=True,
                )

            with right:
                st.bar_chart(counts)
        else:
            st.info(
                "A budget report was found, but no recognizable status "
                "column was detected."
            )
            show_dataframe(budget_summary, "budget_overview", 20)
    else:
        st.info(
            "Budget report not found. Run "
            "`python -m src.run_budget_analysis` first."
        )

    st.divider()
    st.subheader("Transaction category breakdown")

    if transactions is not None and not transactions.empty:
        category_col = find_column(
            transactions,
            ["predicted_category", "category_name", "category", "category_id"],
        )

        if category_col:
            category_counts = (
                transactions[category_col]
                .fillna("Uncategorized")
                .astype(str)
                .value_counts()
                .head(15)
            )
            st.bar_chart(category_counts)
        else:
            st.info("No recognizable transaction category column was found.")
    else:
        st.info(
            "Transaction data not found. Run "
            "`python -m src.categorization` first."
        )

    st.caption(
        "Evaluation metrics from synthetic ground truth measure agreement "
        "with generated labels, not guaranteed real-world performance."
    )


# --------------------------------------------------
# Transactions
# --------------------------------------------------

elif page == "Transactions":
    st.title("Transactions")
    st.write("Search, filter, inspect, and export categorized transactions.")

    if transactions is None or transactions.empty:
        st.warning(
            "Transaction data was not found. Run "
            "`python -m src.categorization`."
        )
    else:
        filtered = transactions.copy()

        search = st.text_input(
            "Search transactions",
            placeholder="Search merchant, description, transaction ID...",
        )

        if search.strip():
            text_columns = filtered.select_dtypes(
                include=["object", "string"]
            ).columns

            mask = pd.Series(False, index=filtered.index)

            for col in text_columns:
                mask = mask | filtered[col].astype(str).str.contains(
                    search.strip(),
                    case=False,
                    na=False,
                    regex=False,
                )

            filtered = filtered[mask]

        category_col = find_column(
            filtered,
            ["predicted_category", "category_name", "category", "category_id"],
        )

        if category_col:
            categories = sorted(
                filtered[category_col]
                .fillna("Uncategorized")
                .astype(str)
                .unique()
            )

            selected_categories = st.multiselect(
                "Filter by category",
                categories,
                default=[],
            )

            if selected_categories:
                filtered = filtered[
                    filtered[category_col]
                    .fillna("Uncategorized")
                    .astype(str)
                    .isin(selected_categories)
                ]

        type_col = find_column(
            filtered,
            ["transaction_type", "type", "flow_type"],
        )

        if type_col:
            types = sorted(
                filtered[type_col].dropna().astype(str).unique()
            )

            selected_types = st.multiselect(
                "Filter by transaction type",
                types,
                default=[],
            )

            if selected_types:
                filtered = filtered[
                    filtered[type_col].astype(str).isin(selected_types)
                ]

        st.metric("Matching transactions", f"{len(filtered):,}")
        show_dataframe(filtered, "filtered_transactions")


# --------------------------------------------------
# Budget Analysis
# --------------------------------------------------

elif page == "Budget Analysis":
    st.title("Budget Analysis")
    st.write("Compare actual spending against household budget limits.")

    if budget_summary is None:
        st.warning(
            "No recognized budget comparison report was found. "
            "Run `python -m src.run_budget_analysis` and check "
            "`data/generated/` for the output filenames."
        )
    elif budget_summary.empty:
        st.info("The budget comparison report contains no rows.")
    else:
        df = budget_summary.copy()

        status_col = find_column(
            df,
            ["budget_status", "status", "budget_state"],
        )
        actual_col = find_column(
            df,
            ["actual_spending", "actual_amount", "spent", "actual", "total_spending"],
        )
        budget_col = find_column(
            df,
            ["budget_amount", "budget_limit", "budgeted_amount", "budget"],
        )
        category_col = find_column(
            df,
            ["category_name", "category", "category_id"],
        )

        if status_col:
            status_counts = (
                df[status_col].fillna("Unknown").astype(str).value_counts()
            )

            cols = st.columns(min(4, max(1, len(status_counts))))

            for index, (status, count) in enumerate(status_counts.items()):
                with cols[index % len(cols)]:
                    show_metric(str(status), f"{count:,}")

            st.subheader("Budget status distribution")
            st.bar_chart(status_counts)

        if actual_col:
            df[actual_col] = pd.to_numeric(df[actual_col], errors="coerce")

            if budget_col:
                df[budget_col] = pd.to_numeric(
                    df[budget_col], errors="coerce"
                )

                df["Calculated variance"] = df[actual_col] - df[budget_col]

                st.subheader("Spending versus budget")

                chart_columns = [actual_col, budget_col]
                chart_df = df[chart_columns].copy()
                chart_df = chart_df.dropna().head(30)

                if not chart_df.empty:
                    st.bar_chart(chart_df)

                st.subheader("Largest spending variances")
                variance_df = df.sort_values(
                    "Calculated variance",
                    ascending=False,
                    na_position="last",
                )
                show_dataframe(variance_df, "budget_variances", 100)
            else:
                st.info(
                    "Actual spending was found, but a budget amount column "
                    "could not be identified."
                )
                show_dataframe(df, "budget_analysis")
        else:
            st.info(
                "The budget report was found, but the spending columns "
                "could not be identified automatically."
            )
            show_dataframe(df, "budget_analysis")

        if category_col:
            st.subheader("Budget records by category")
            st.dataframe(
                df.groupby(category_col, dropna=False)
                .size()
                .reset_index(name="Records")
                .sort_values("Records", ascending=False),
                use_container_width=True,
                hide_index=True,
            )

        # Gemini explains the already-calculated Python results.
        # It does not calculate or modify budgets/transactions.
        st.divider()
        st.subheader("Gemini AI Budget Insights")
        st.caption(
            "AI explanations are based on aggregate results from this report. "
            "Budget calculations remain in Python; no transactions are changed."
        )

        if st.button("Generate budget insights", key="generate_budget_insights"):
            insight_summary = {
                "source_report": budget_summary_name or "budget report",
                "record_count": int(len(df)),
            }

            if status_col:
                status_counts = (
                    df[status_col].fillna("Unknown").astype(str)
                    .value_counts().to_dict()
                )
                insight_summary["budget_status_counts"] = {
                    str(k): int(v) for k, v in status_counts.items()
                }

            if actual_col:
                actual_values = pd.to_numeric(df[actual_col], errors="coerce")
                insight_summary["total_actual_spending"] = (
                    round(float(actual_values.sum()), 2)
                    if actual_values.notna().any() else None
                )

                if budget_col:
                    budget_values = pd.to_numeric(df[budget_col], errors="coerce")
                    valid = actual_values.notna() & budget_values.notna()
                    insight_summary["total_budget"] = (
                        round(float(budget_values[valid].sum()), 2)
                        if valid.any() else None
                    )
                    insight_summary["total_calculated_variance"] = (
                        round(float((actual_values[valid] - budget_values[valid]).sum()), 2)
                        if valid.any() else None
                    )
                    insight_summary["variance_definition"] = (
                        "actual spending minus budget; positive means over budget"
                    )

                    if category_col:
                        category_data = pd.DataFrame({
                            "category": df[category_col].fillna("Uncategorized").astype(str),
                            "actual": actual_values,
                            "budget": budget_values,
                        }).dropna(subset=["actual", "budget"])
                        if not category_data.empty:
                            category_data["variance"] = (
                                category_data["actual"] - category_data["budget"]
                            )
                            by_category = (
                                category_data.groupby("category", dropna=False)
                                .agg(
                                    actual_spending=("actual", "sum"),
                                    budget=("budget", "sum"),
                                    variance=("variance", "sum"),
                                )
                                .sort_values("variance", ascending=False)
                                .head(15)
                                .round(2)
                                .reset_index()
                            )
                            insight_summary["category_breakdown_top_15"] = (
                                by_category.to_dict(orient="records")
                            )

            with st.spinner("Generating insights from the budget report..."):
                try:
                    insight_text = generate_budget_insight(insight_summary)
                    st.session_state["gemini_budget_insight"] = insight_text
                except Exception as exc:
                    st.session_state["gemini_budget_insight"] = (
                        "Unable to generate insights. Check the Gemini setup. "
                        f"Details: {exc}"
                    )

        if st.session_state.get("gemini_budget_insight"):
            st.markdown(st.session_state["gemini_budget_insight"])


# --------------------------------------------------
# Recurring Payments
# --------------------------------------------------

elif page == "Recurring Payments":
    st.title("Recurring Payments")
    st.write(
        "Review detected recurring payments, recurring series, "
        "and possible missed payment cycles."
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "Detected Payments",
            "Recurring Series",
            "Cycle Exceptions",
        ]
    )

    recurring_sections = [
        (
            tab1,
            "Detected recurring payments",
            detected_recurring,
            "detected_recurring_payments",
        ),
        (
            tab2,
            "Recurring series",
            recurring_series,
            "recurring_series",
        ),
        (
            tab3,
            "Recurring cycle exceptions",
            recurring_exceptions,
            "recurring_cycle_exceptions",
        ),
    ]

    for tab, title, df, download_name in recurring_sections:
        with tab:
            st.subheader(title)

            if df is None:
                st.warning(
                    f"File for this section was not found in "
                    f"`data/generated/`."
                )
            else:
                st.metric("Rows", f"{len(df):,}")

                if df.empty:
                    st.info(
                        "The file exists, but there are no records to display."
                    )
                else:
                    show_dataframe(df, download_name, 1000)

                    # Show useful columns as a compact summary where possible.
                    status_col = find_column(
                        df,
                        ["status", "match_status", "exception_type", "reason"],
                    )

                    if status_col:
                        st.subheader("Status breakdown")
                        st.bar_chart(
                            df[status_col]
                            .fillna("Unknown")
                            .astype(str)
                            .value_counts()
                        )

    st.divider()
    st.caption(
        "The dashboard reads the files produced by your existing pipeline: "
        "detected_recurring_payments.csv, recurring_series.csv, and "
        "recurring_cycle_exceptions.csv."
    )


# --------------------------------------------------
# Exceptions & Audit
# --------------------------------------------------

elif page == "Exceptions & Audit":
    st.title("Exceptions & Audit")
    st.write(
        "Inspect exceptions and trace records that may require review."
    )

    tab1, tab2, tab3 = st.tabs(
        ["Budget Exceptions", "Recurring Exceptions", "Validation Report"]
    )

    with tab1:
        st.subheader("Budget exceptions")

        if exceptions is None:
            # Look for other exception CSVs without confusing recurring reports.
            candidates = [
                path for path in find_csv_files()
                if "exception" in path.name.lower()
                and "recurring" not in path.name.lower()
                and "cycle" not in path.name.lower()
            ]

            if candidates:
                chosen = st.selectbox(
                    "Select an exception report",
                    candidates,
                    format_func=lambda p: p.name,
                    key="budget_exception_select",
                )
                df = read_csv_file(chosen.name)
                show_dataframe(df, chosen.stem)
            else:
                st.info(
                    "No separate budget-exceptions CSV was found. "
                    "Check the budget comparison report for OVER_BUDGET records."
                )

                if budget_summary is not None:
                    status_col = find_column(
                        budget_summary,
                        ["budget_status", "status", "budget_state"],
                    )

                    if status_col:
                        over = budget_summary[
                            budget_summary[status_col]
                            .astype(str)
                            .str.upper()
                            .str.contains("OVER", na=False)
                        ]
                        st.metric("Over-budget records", f"{len(over):,}")
                        show_dataframe(over, "over_budget_exceptions")

        else:
            show_dataframe(exceptions, "budget_exceptions")

    with tab2:
        st.subheader("Recurring cycle exceptions")

        if recurring_exceptions is None:
            st.info("Recurring cycle exception report not found.")
        else:
            st.metric("Exception records", f"{len(recurring_exceptions):,}")
            show_dataframe(
                recurring_exceptions,
                "recurring_cycle_exceptions",
            )

    
    with tab3:
        st.subheader("Data Validation Report")

        report_path = DOCS_DIR / "validation_report.json"

        if report_path.exists():
            try:
                with report_path.open("r", encoding="utf-8") as file:
                    report = json.load(file)

                status = str(report.get("status", "UNKNOWN")).upper()
                row_counts = report.get("row_counts", {})

                # Overall validation status
                st.markdown("### Overall Status")

                if status == "PASS":
                    st.success("PASS — All configured validation checks passed.")
                else:
                    st.error(f"Validation status: {status}")

                st.divider()

                # Dataset metric cards
                st.markdown("### Dataset Summary")

                if row_counts:
                    preferred = [
                        "users",
                        "accounts",
                        "transactions",
                        "budgets",
                        "recurring",
                        "merchants",
                        "categories",
                        "rules",
                        "ground_truth_labels",
                        "anomaly_cases",
                    ]

                    available = [
                        name for name in preferred if name in row_counts
                    ]

                    for start in range(0, len(available), 4):
                        cols = st.columns(4)

                        for col, name in zip(
                            cols, available[start:start + 4]
                        ):
                            with col:
                                st.metric(
                                    label=name.replace("_", " ").title(),
                                    value=f"{row_counts[name]:,}",
                                )

                    # Detailed table
                    st.markdown("### Record Counts")

                    details = pd.DataFrame([
                        {
                            "Dataset": name.replace("_", " ").title(),
                            "Record Count": count,
                        }
                        for name, count in row_counts.items()
                    ])

                    st.dataframe(
                        details,
                        use_container_width=True,
                        hide_index=True,
                    )

                    # Chart
                    st.markdown("### Dataset Size Comparison")

                    chart_data = details.set_index("Dataset")
                    st.bar_chart(chart_data["Record Count"])

                else:
                    st.warning("No dataset row counts were found in the report.")

                # Display additional checks without raw JSON
                extra_details = {
                    key: value
                    for key, value in report.items()
                    if key not in ("status", "row_counts")
                }

                if extra_details:
                    st.markdown("### Additional Validation Details")

                    for key, value in extra_details.items():
                        with st.expander(key.replace("_", " ").title()):
                            if isinstance(value, dict):
                                detail_df = pd.DataFrame(
                                    list(value.items()),
                                    columns=["Check", "Result"],
                                )
                                st.dataframe(
                                    detail_df,
                                    use_container_width=True,
                                    hide_index=True,
                                )
                            elif isinstance(value, list):
                                st.write(value)
                            else:
                                st.write(value)

                # Download original report
                st.divider()

                st.download_button(
                    label="Download Validation Report",
                    data=json.dumps(report, indent=2).encode("utf-8"),
                    file_name="validation_report.json",
                    mime="application/json",
                    key="download_validation_report",
                )

            except Exception as exc:
                st.error(f"Unable to load validation report: {exc}")

        else:
            st.warning(
                "Validation report not found. Run "
                "`python -m src.validation`."
            )



# --------------------------------------------------
# Reports & Data
# --------------------------------------------------

elif page == "Reports & Data":
    st.title("Reports & Data")
    st.write("Browse the generated outputs and evaluation reports.")

    tab1, tab2, tab3 = st.tabs(
        ["Generated CSVs", "Evaluation", "Project Files"]
    )

    with tab1:
        st.subheader("CSV files in data/generated")

        csv_files = find_csv_files()

        if not csv_files:
            st.warning(
                "No generated CSV files were found in `data/generated/`."
            )
        else:
            file_names = [path.name for path in csv_files]

            selected_name = st.selectbox(
                "Choose a report",
                file_names,
            )

            selected_path = DATA_DIR / selected_name
            selected_df = read_csv_file(selected_name)

            if selected_df is not None:
                show_dataframe(selected_df, selected_path.stem, 1000)

    with tab2:
        st.subheader("Evaluation report")

        evaluation_path = DOCS_DIR / "evaluation_report.json"

        if evaluation_path.exists():
            try:
                with evaluation_path.open("r", encoding="utf-8") as file:
                    evaluation = json.load(file)

                st.json(evaluation)

                st.download_button(
                    "Download evaluation JSON",
                    data=json.dumps(evaluation, indent=2).encode("utf-8"),
                    file_name="evaluation_report.json",
                    mime="application/json",
                    key="download_evaluation_report",
                )

                st.warning(
                    "Interpret evaluation results in context: if predictions "
                    "are compared with labels generated from the same synthetic "
                    "transaction data, the score is not an independent estimate "
                    "of real-world classification accuracy."
                )
            except Exception as exc:
                st.error(f"Could not read evaluation report: {exc}")
        else:
            st.info(
                "Evaluation report not found. Run "
                "`python -m src.evaluation`."
            )

    with tab3:
        st.subheader("Project folders")

        folder_info = pd.DataFrame(
            [
                {
                    "Folder": "data/generated",
                    "Path": str(DATA_DIR),
                    "Exists": DATA_DIR.exists(),
                    "CSV files": len(find_csv_files(DATA_DIR)),
                },
                {
                    "Folder": "data/ground_truth",
                    "Path": str(GROUND_TRUTH_DIR),
                    "Exists": GROUND_TRUTH_DIR.exists(),
                    "CSV files": len(find_csv_files(GROUND_TRUTH_DIR)),
                },
                {
                    "Folder": "docs",
                    "Path": str(DOCS_DIR),
                    "Exists": DOCS_DIR.exists(),
                    "CSV files": len(find_csv_files(DOCS_DIR)),
                },
            ]
        )

        st.dataframe(
            folder_info,
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("Generated CSV inventory")

        inventory = []

        for path in find_csv_files():
            try:
                row_count = sum(1 for _ in path.open(
                    "r", encoding="utf-8", errors="replace"
                )) - 1
            except Exception:
                row_count = None

            inventory.append(
                {
                    "File": path.name,
                    "Size (KB)": round(path.stat().st_size / 1024, 2),
                    "Approximate data rows": max(row_count, 0)
                    if row_count is not None else "Unknown",
                }
            )

        if inventory:
            st.dataframe(
                pd.DataFrame(inventory),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No generated CSV files are available yet.")


# --------------------------------------------------
# Footer
# --------------------------------------------------

st.sidebar.divider()
st.sidebar.caption("YottaFlex Finance Management")
st.sidebar.caption("Local Streamlit dashboard")
