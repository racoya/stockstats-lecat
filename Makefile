.PHONY: install format test run clean help

# Default target
help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install all dependencies
	pip install -r requirements.txt

install-dev:  ## Install with development tools (black, isort, pytest)
	pip install -e ".[all,dev]"

format:  ## Format code with black and isort
	isort lecat/ tests/
	black lecat/ tests/

lint:  ## Check formatting without modifying files
	black --check lecat/ tests/
	isort --check lecat/ tests/

test:  ## Run all tests
	python -m pytest tests/ -v

test-fast:  ## Run tests without verbose output
	python -m pytest tests/ -q

test-unit:  ## Run unittest discovery (alternative)
	python -m unittest discover -s tests -v

run:  ## Launch the Streamlit dashboard
	streamlit run lecat/dashboard/app.py

run-cli:  ## Run CLI with default settings
	python -m lecat.main

clean:  ## Remove caches, logs, and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ logs/
	@echo "✅ Cleaned"
