.PHONY: install test lint db-new db-up db-down db-reset installer installer-deps installer-build installer-dmg

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
	rm -rf installer/build/
	rm -rf installer/dist/
	rm -f rw.*.dmg 

format:
	uv run ruff format .

format: format-python
#format: format-python format-prettier

# run inspector tool
run-dev:
	uv run mcp dev src/basic_memory/mcp/main.py

# Installer targets
installer-deps:
	uv pip install -e ".[dev]"
	brew install create-dmg || true  # Don't fail if already installed

installer-build:
	cd installer && python setup.py bdist_mac

installer-dmg:
	mkdir -p installer/dist
	create-dmg \
		--volname "Basic Memory Installer" \
		--window-pos 200 120 \
		--window-size 800 400 \
		--icon-size 100 \
		--icon "Basic Memory Installer.app" 200 190 \
		--hide-extension "Basic Memory Installer.app" \
		--app-drop-link 600 185 \
		"installer/dist/Basic Memory-Installer.dmg" \
		"installer/build/Basic Memory Installer.app"


# Main installer target that runs everything
installer: installer-deps installer-build installer-dmg