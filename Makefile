# ==============================================================================
# Nifty 100 Financial Intelligence Platform - Makefile
# ==============================================================================

.PHONY: load validate ratios screen report tearsheet sector-report portfolio-report \
        dashboard api nlp-demo test test-kpi test-api lint format clean help

# ------------------------------------------------------------------------------
# Help
# ------------------------------------------------------------------------------
help:
	@echo ""
	@echo "======================================================================"
	@echo "  Nifty 100 Financial Intelligence Platform — Make Targets"
	@echo "======================================================================"
	@echo ""
	@echo "  DATA & ETL"
	@echo "    make load             Load all 12 Excel files into SQLite (nifty100.db)"
	@echo "    make validate         Run 16 DQ rules and generate validation_failures.csv"
	@echo ""
	@echo "  ANALYTICS / KPI"
	@echo "    make ratios           Compute 50+ KPIs and write to financial_ratios table"
	@echo "    make screen           Run all 6 screener presets and export CSV files"
	@echo ""
	@echo "  REPORTS"
	@echo "    make report           Generate ALL report types (tearsheets, sector, portfolio)"
	@echo "    make tearsheet        Generate tearsheet for one company (TICKER=RELIANCE)"
	@echo "    make sector-report    Generate sector intelligence PDF"
	@echo "    make portfolio-report Generate sample portfolio PDF"
	@echo ""
	@echo "  USER INTERFACES"
	@echo "    make dashboard        Start Streamlit dashboard (http://localhost:8501)"
	@echo "    make api              Start FastAPI server (http://localhost:8000)"
	@echo ""
	@echo "  NLP"
	@echo "    make nlp-demo         Run sentiment analysis demo on sample headlines"
	@echo ""
	@echo "  TESTING"
	@echo "    make test             Run full test suite (all modules)"
	@echo "    make test-kpi         Run KPI / screener unit tests only"
	@echo "    make test-api         Run API integration tests only"
	@echo "    make test-etl         Run ETL / DQ unit tests only"
	@echo ""
	@echo "  CODE QUALITY"
	@echo "    make lint             Lint code with ruff"
	@echo "    make format           Format code with black"
	@echo ""
	@echo "    make clean            Remove Python cache, pyc files, HTML reports"
	@echo "======================================================================"
	@echo ""

# ------------------------------------------------------------------------------
# ETL
# ------------------------------------------------------------------------------
load:
	python src/etl/loader.py

validate:
	python src/etl/validator.py

# ------------------------------------------------------------------------------
# Analytics / KPI
# ------------------------------------------------------------------------------
ratios:
	python src/analytics/ratios.py

screen:
	python src/analytics/screener.py

# ------------------------------------------------------------------------------
# Reports
# ------------------------------------------------------------------------------
report:
	python src/reports/sector_report.py
	python src/reports/portfolio_report.py
	@echo ""
	@echo "To generate company tearsheets run: make tearsheet TICKER=<TICKER>"

TICKER ?= RELIANCE
tearsheet:
	python -c "from src.reports.tearsheet import generate_tearsheet; print(generate_tearsheet('$(TICKER)'))"

sector-report:
	python src/reports/sector_report.py

portfolio-report:
	python src/reports/portfolio_report.py

# ------------------------------------------------------------------------------
# User Interfaces
# ------------------------------------------------------------------------------
dashboard:
	streamlit run src/dashboard/app.py

api:
	uvicorn src.api.main:app --port 8000 --reload

# ------------------------------------------------------------------------------
# NLP
# ------------------------------------------------------------------------------
nlp-demo:
	python src/nlp/sentiment.py

# ------------------------------------------------------------------------------
# Testing
# ------------------------------------------------------------------------------
test:
	pytest tests/ -v --html=output/pytest_report.html --self-contained-html

test-kpi:
	pytest tests/kpi/ -v

test-api:
	pytest tests/api/ -v

test-etl:
	pytest tests/etl/ tests/dq/ -v

# ------------------------------------------------------------------------------
# Code Quality
# ------------------------------------------------------------------------------
lint:
	ruff check src/ tests/

format:
	black src/ tests/

# ------------------------------------------------------------------------------
# Clean
# ------------------------------------------------------------------------------
clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__') if p.is_dir()]; [p.unlink() for p in pathlib.Path('.').rglob('*.py[co]') if p.is_file()]"
	@echo "Cache cleared."
