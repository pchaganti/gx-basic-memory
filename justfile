# Basic Memory - Modern Command Runner

# Install dependencies
install:
    pip install -e ".[dev]"

# Run unit tests in parallel
test-unit:
    uv run pytest -p pytest_mock -v -n auto

# Run integration tests in parallel
test-int:
    uv run pytest -p pytest_mock -v --no-cov -n auto test-int

# Run all tests
test: test-unit test-int

# Lint and fix code
lint:
    ruff check . --fix

# Type check code
type-check:
    uv run pyright

# Clean build artifacts and cache files
clean:
    find . -type f -name '*.pyc' -delete
    find . -type d -name '__pycache__' -exec rm -r {} +
    rm -rf installer/build/ installer/dist/ dist/
    rm -f rw.*.dmg .coverage.*

# Format code with ruff
format:
    uv run ruff format .

# Run MCP inspector tool
run-inspector:
    npx @modelcontextprotocol/inspector

# Build macOS installer
installer-mac:
    cd installer && chmod +x make_icons.sh && ./make_icons.sh
    cd installer && uv run python setup.py bdist_mac

# Build Windows installer
installer-win:
    cd installer && uv run python setup.py bdist_win32

# Update all dependencies to latest versions
update-deps:
    uv sync --upgrade

# Run all code quality checks and tests
check: lint format type-check test

# Generate Alembic migration with descriptive message
migration message:
    cd src/basic_memory/alembic && alembic revision --autogenerate -m "{{message}}"

# List all available recipes
default:
    @just --list