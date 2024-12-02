# basic-memory

Local-first knowledge management system that combines Zettelkasten methodology with knowledge graphs. Built using SQLite and markdown files, it enables seamless capture and connection of ideas while maintaining user control over data.

## Features

- Local-first design using SQLite and markdown files
- Combines Zettelkasten principles with knowledge graph capabilities
- Everything readable/writable as markdown
- Project isolation for focused context
- Rich querying and traversal through SQLite index
- Built with Python 3.12, SQLAlchemy, and modern tooling

## Development

Setup your development environment:

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv/Scripts/activate` on Windows

# Install dependencies including dev tools
pip install -e ".[dev]"
```

Run tests:
```bash
pytest
```

## License

AGPL-3.0-or-later