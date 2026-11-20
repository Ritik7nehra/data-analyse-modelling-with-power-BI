.PHONY: help install lint test pipeline validate bq-dry-run bi-snippets excel pivots dcf deck-data deck deliverables all clean

PYTHON ?= python3

help:  ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

install:  ## install the package with dev and deliverable extras
	$(PYTHON) -m pip install -e ".[dev,deliverables]"

lint:  ## ruff
	ruff check . --exclude notebooks

test:  ## pytest (includes SQL, masking, pipeline, Excel, DCF and deck regression tests)
	$(PYTHON) -m pytest

pipeline:  ## run the ETL pipeline (dev masking key unless MASKING_KEY is set)
	$(PYTHON) -m superstore_pipeline run

validate:  ## data-quality checks only
	$(PYTHON) -m superstore_pipeline validate

bq-dry-run:  ## validate the BigQuery load without credentials
	$(PYTHON) warehouse/bigquery/load_to_bigquery.py --project demo --dataset demo --dry-run

bi-snippets:  ## regenerate the metric reference (SQL / DAX / Tableau / Looker Studio)
	$(PYTHON) bi/generate_bi_snippets.py

excel:  ## rebuild the Excel workbook (then recalculate in Excel or LibreOffice to store values)
	$(PYTHON) excel/build_workbook.py

pivots:  ## native PivotTables (needs LibreOffice's python-uno)
	$(PYTHON) excel/build_pivottables.py

dcf:  ## rebuild the DCF workbook
	$(PYTHON) excel/finance/build_dcf.py

deck-data:  ## numbers for the deck, straight from the marts
	$(PYTHON) reports/deck/build_deck_data.py

deck: deck-data  ## executive deck (needs Node and `npm install pptxgenjs`)
	node reports/deck/build_deck.js
	$(PYTHON) reports/deck/apply_theme.py reports/Superstore_Executive_Deck.pptx

deliverables: excel dcf pivots deck  ## everything that is not code

all: lint test pipeline  ## the checks CI runs

clean:  ## remove build outputs
	rm -rf build .pytest_cache .ruff_cache
