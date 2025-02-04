.PHONY: install test lint db-new db-up db-down db-reset

install:
	brew install dbmate
	pip install -e ".[dev]"

test:
	pytest -p pytest_mock -v

lint:
	black .
	ruff check .

db-new:
	dbmate new $(name)

db-up:
	dbmate up

db-down:
	dbmate down

db-reset:
	dbmate drop
	dbmate up

clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -exec rm -r {} +

format:
	uv run ruff format .

format: format-python
#format: format-python format-prettier

# run inspector tool
run-dev:
	uv run mcp dev src/basic_memory/mcp/main.py