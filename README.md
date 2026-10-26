# YottaFlex Finance Management

## Overview

YottaFlex Finance Management is a Python-based household finance management solution designed to categorize financial transactions, identify recurring payments, and compare household spending against predefined budgets.

The system aims to make financial data easier to understand by identifying spending patterns, highlighting budget exceptions, and maintaining traceability of processing decisions.

## Problem Statement

Households often struggle to organize financial transactions, identify recurring expenses, and monitor spending against budgets. This project addresses these challenges through an end-to-end workflow that processes transactions, assigns categories, detects recurring payment patterns, and evaluates budget performance.

## Objectives

- Automatically categorize financial transactions.
- Identify recurring payments and payment patterns.
- Compare actual household spending with allocated budgets.
- Detect exceptions and unusual spending conditions.
- Maintain traceability of processing decisions.
- Generate measurable outputs to evaluate system performance.

## Key Features

### 1. Transaction Categorization

Organizes financial transactions into appropriate spending categories using categorization rules or other implemented classification methods.

### 2. Recurring Payment Detection

Analyzes transaction history to identify potential recurring payments, such as subscriptions and regular household expenses.

### 3. Budget Comparison

Compares actual spending with predefined budgets to identify spending limits, budget overruns, and remaining budget amounts.

### 4. Exception Handling

Highlights exceptions such as budget overruns, transactions requiring review, or recurring payment patterns that do not meet the expected rules, where supported by the implementation.

### 5. Traceability

Uses generated outputs and supporting records to help track processed transactions, categorization results, recurring payment detections, and budget comparison decisions.

### 6. Evaluation Metrics

Provides a foundation for measuring categorization quality, recurring payment detection, budget compliance, and exception handling.

## Technology Stack

- **Programming Language:** Python
- **Data Processing:** Pandas, NumPy
- **Application Interface:** Streamlit
- **Visualization:** Plotly
- **Classification and Evaluation:** Scikit-learn
- **Testing:** Pytest
- **Environment Configuration:** Python Dotenv
- **AI Integration:** Google GenAI, if used by the implemented workflow

## Project Structure

```text
yottaflex-finance-management/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── data/
│   └── generated/
│       ├── accounts.csv
│       ├── budget_comparison.csv
│       ├── budget_exceptions.csv
│       ├── budgets.csv
│       ├── categories.csv
│       ├── category_confusion_matrix.csv
│       ├── category_rules.csv
│       ├── detected_recurring_payments.csv
│       ├── household_spending.csv
│       ├── insights.csv
│       ├── merchants.csv
│       ├── recurring_cycle_exceptions.csv
│       ├── recurring_series.csv
│       └── users.csv
└── tests/
```

*Note: The structure above reflects the project files and generated outputs identified during development. Adjust it if your actual folders differ.*

## Installation and Setup

### Prerequisites

- Python 3.10 or a compatible version
- Git
- Visual Studio Code or another Python editor

### 1. Clone the repository

```bash
git clone https://github.com/mnagasupriya/yottaflex-finance-management.git
cd yottaflex-finance-management
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

If the application uses a Google Gemini API key, create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_api_key_here
```

Replace the placeholder with your own API key. Never commit `.env` or expose API credentials publicly.

### 5. Run the application

```bash
python -m streamlit run app.py
```

Open the local URL displayed in your terminal.

## Generated Outputs

The project includes generated data files intended to support analysis and evaluation.

| Output | Purpose |
|---|---|
| `categories.csv` | Category reference data |
| `category_rules.csv` | Categorization rules |
| `category_confusion_matrix.csv` | Categorization evaluation |
| `detected_recurring_payments.csv` | Detected recurring payments |
| `recurring_series.csv` | Recurring payment series |
| `recurring_cycle_exceptions.csv` | Recurring cycle exceptions |
| `budget_comparison.csv` | Actual spending compared with budgets |
| `budget_exceptions.csv` | Budget-related exceptions |
| `household_spending.csv` | Household spending analysis |
| `insights.csv` | Generated financial insights |
| `manifest.json` | Generated output metadata, if maintained by the application |

The actual contents and generation logic of each file depend on the implementation.

## Evaluation Metrics

The following metrics can be used to evaluate the solution:

### Transaction Categorization

- Accuracy
- Precision
- Recall
- F1-score
- Confusion matrix

### Recurring Payment Detection

- Number of recurring payment series detected
- Detection precision and recall, when verified labels are available
- Number of recurring cycle exceptions

### Budget Monitoring

- Number of budgets evaluated
- Number of budget overruns
- Total amount exceeding budgets
- Percentage of budgets within limits

### Operational Evaluation

- Number of transactions processed
- Number of transactions requiring manual review
- Number of exceptions detected
- Processing time, where measured

Metrics should be calculated from actual application results rather than assumed or hard-coded.

## Testing

Run the test suite, if tests are available:

```bash
python -m pytest
```

Testing should cover transaction categorization, recurring payment detection, budget calculations, exception conditions, and edge cases such as missing values or invalid transaction data.

## Security and Data Handling

- Keep API keys and other credentials in environment variables.
- Exclude `.env`, virtual environments, and unnecessary generated files from Git.
- Avoid committing large datasets containing sensitive financial information.
- Use synthetic or anonymized transaction data for demonstrations.

## Future Improvements

- Improve categorization accuracy with additional rules or trained models.
- Add configurable household budgets.
- Improve recurring payment detection for irregular payment dates and amounts.
- Add explanations for categorization and exception decisions.
- Expand automated testing and evaluation reports.
- Improve dashboards for household spending trends.

## Author

**Naga Supriya Moravaneni**

GitHub: https://github.com/mnagasupriya

## Project Goal

To provide an end-to-end household finance management solution that organizes transactions, identifies recurring payments, monitors budgets, highlights exceptions, and supports measurable evaluation of financial processing decisions.
