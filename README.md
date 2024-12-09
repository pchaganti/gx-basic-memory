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


project info memory store
~/.npm/_npx/15b07286cbcc3329/node_modules/@modelcontextprotocol/server-memory/dist/memory.json


## Running locally

See: https://modelcontextprotocol.io/docs/first-server/python#connect-to-claude-desktop

```json
{
  "mcpServers": {
    "basic-memory": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/phernandez/dev/basicmachines/basic-memory",
        "run",
        "src/basic_memory/mcp/server.py"
      ]
    }
  }
}
```

### logs

/Users/phernandez/Library/Logs/Claude/mcp-server-basic-memory.log 




# MCP quickstart
https://modelcontextprotocol.io/quickstart

Claude Desktop config json
/Users/phernandez/Library/Application Support/Claude/claude_desktop_config.json

## stdout logging

logs-dir:
/Users/phernandez/Library/Logs/Claude

- mcp-server-sqlite.log 
- mcp.log

To test changes efficiently:

- Configuration changes: Restart Claude Desktop
- Server code changes: Use Command-R to reload
- Quick iteration: Use Inspector during development
  - https://modelcontextprotocol.io/docs/tools/inspector

eg. 
```bash
npx @modelcontextprotocol/inspector uvx mcp-server-sqlite --db-path /Users/phernandez/dev/basicmachines/mcp-quickstart/test.db
```

## tools 
Inspector: https://modelcontextprotocol.io/docs/tools/inspector
Debugger: https://modelcontextprotocol.io/docs/tools/debugging

## dev tools

```bash
jq '.allowDevTools = true' ~/Library/Application\ Support/Claude/developer_settings.json > tmp.json \
  && mv tmp.json ~/Library/Application\ Support/Claude/developer_settings.json

```

Open DevTools: Command-Option-Shift-i


## TODO

logs 

/Users/phernandez/Library/Logs/Claude/mcp-server-basic-memory.log 

```text
2024-12-08 20:32:38.802 | INFO     | __main__:run_server:264 - Starting MCP server basic-memory
The garbage collector is trying to clean up non-checked-in connection <AdaptedConnection <Connection(Thread-2, started daemon 6227046400)>>, which will be dropped, as it cannot be safely terminated.  Please ensure that SQLAlchemy pooled connections are returned to the pool explicitly, either by calling ``close()`` or by using appropriate context managers to manage their lifecycle.
The garbage collector is trying to clean up non-checked-in connection <AdaptedConnection <Connection(Thread-3, started daemon 6243872768)>>, which will be dropped, as it cannot be safely terminated.  Please ensure that SQLAlchemy pooled connections are returned to the pool explicitly, either by calling ``close()`` or by using appropriate context managers to manage their lifecycle.
~
```

more info about setting log level: https://modelcontextprotocol.io/docs/first-server/python
- scroll down to logging
