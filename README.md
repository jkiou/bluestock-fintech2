# Nifty 100 Financial Intelligence Platform

A self-contained, production-grade financial intelligence system enabling analysts to query, screen, score, and compare all 92 Nifty 100 companies with 10–13 years of annual financial history, 50+ computed KPIs, and 12 analytics modules.

## Project Structure

```text
├── data/
│   ├── raw/               # 7 core Excel files (read-only)
│   └── supporting/        # 5 supplementary Excel files
├── src/
│   ├── etl/               # Database loader, validator, and normalizer
│   ├── analytics/         # Ratio engine, CAGR, and financial formulas
│   ├── nlp/               # Qualitative text parsers & sentiment analysis
│   ├── dashboard/         # Streamlit multi-page dashboard
│   ├── api/               # FastAPI routing and endpoints
│   └── reports/           # Tearsheet and portfolio PDF generators
├── tests/                 # Pytest test suites (etl, kpi, api, dq)
├── config/                # YAML and env configurations
├── reports/               # Output PDF/PNG reports
├── output/                # Excel/CSV data exports
├── docs/                  # Project specifications and manuals
├── requirements.txt       # Project python dependencies
├── Makefile               # CLI target automation scripts
└── README.md              # Project documentation
```

## Setup & Quick Start

1. **Configure Environment**:
   Copy the environment template file:
   ```bash
   cp config/.env.template .env
   ```

2. **Install Dependencies**:
   Install the required libraries:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify Environment**:
   Verify that all dependencies (including compiled components) load correctly:
   ```bash
   python -c "import pandas, numpy, scipy, sklearn, matplotlib, plotly, streamlit, fastapi, uvicorn, reportlab, nltk, regex, pytest, requests, yaml; print('All libraries imported successfully!')"
   ```

## Development Commands (Makefile)

Use the following `make` commands to automate workflows:

- `make load` - Run the ETL pipeline to load and normalize all 12 Excel source files.
- `make ratios` - Run the Ratio Engine to compute and populate financial KPIs.
- `make test` - Run the unit test suite and generate an HTML test report.
- `make report` - Generate all PDF reports (Tearsheets, Sectors, Portfolio).
- `make dashboard` - Launch the Streamlit multi-page dashboard.
- `make api` - Launch the FastAPI REST server.
- `make clean` - Remove Python cache and temporary test artifacts.
