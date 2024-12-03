.PHONY: install test lint db-new db-up db-down db-reset

install:
	brew install dbmate
	pip install -e ".[dev]"

test:
	pytest

lint:
	black .
	ruff check .

db-new:
	dbmate new

db-up:
	dbmate up

db-down:
	dbmate down

db-reset:
	dbmate drop
	dbmate up