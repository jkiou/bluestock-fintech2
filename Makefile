# ==============================================================================
# Nifty 100 Financial Intelligence Platform - Makefile
# ==============================================================================

.PHONY: load ratios test report dashboard api clean help

help:
	@echo "Available commands:"
	@echo "  make load      - Run ETL: load all Excel datasets into SQLite database"
	@echo "  make ratios    - Run Ratio Engine: compute and populate KPIs"
	@echo "  make test      - Run full test suite and output HTML test report"
	@echo "  make report    - Generate all PDF reports (Tearsheets, Sectors, Portfolio)"
	@echo "  make dashboard - Start the Streamlit multi-page dashboard"
	@echo "  make api       - Start the FastAPI / Uvicorn server"
	@echo "  make clean     - Remove Python cache files, __pycache__ and test logs"

load:
	python src/etl/loader.py

ratios:
	python src/analytics/ratios.py

test:
	pytest tests/ --html=reports/pytest_report.html

report:
	python src/reports/portfolio_report.py

dashboard:
	streamlit run src/dashboard/app.py

api:
	uvicorn src.api.main:app --port 8000 --reload

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__') if p.is_dir()]; [p.unlink() for p in pathlib.Path('.').rglob('*.py[co]') if p.is_file()]; [p.unlink() for p in pathlib.Path('reports').glob('*.html') if p.exists()]"
