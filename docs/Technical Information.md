---
title: Technical Information
type: note
permalink: docs/technical-information
---

# Technical Information

This document provides technical details about Basic Memory's implementation, licensing, and integration with the Model Context Protocol (MCP).

## Architecture

Basic Memory consists of:

1. **Core Knowledge Engine**: Parses and indexes Markdown files
2. **SQLite Database**: Provides fast querying and search
3. **MCP Server**: Implements the Model Context Protocol
4. **CLI Tools**: Command-line utilities for management
5. **Sync Service**: Monitors file changes and updates the database

The system follows a file-first architecture where all knowledge is represented in standard Markdown files and the database serves as a secondary index.

## Model Context Protocol (MCP)

Basic Memory implements the [Model Context Protocol](https://github.com/modelcontextprotocol/spec), an open standard for enabling AI models to access external tools:

- **Standardized Interface**: Common protocol for tool integration
- **Tool Registration**: Basic Memory registers as a tool provider
- **Asynchronous Communication**: Enables efficient interaction with AI models
- **Standardized Schema**: Structured data exchange format

Integration with Claude Desktop uses the MCP to grant Claude access to your knowledge base through a set of specialized tools that search, read, and write knowledge.

## Licensing

Basic Memory is licensed under the [GNU Affero General Public License v3.0 (AGPL-3.0)](https://www.gnu.org/licenses/agpl-3.0.en.html):

- **Free Software**: You can use, study, share, and modify the software
- **Copyleft**: Derivative works must be distributed under the same license
- **Network Use**: Network users must be able to receive the source code
- **Commercial Use**: Allowed, subject to license requirements

The AGPL license ensures Basic Memory remains open source while protecting against proprietary forks.

## Source Code

Basic Memory is developed as an open-source project:

- **GitHub Repository**: [https://github.com/basicmachines-co/basic-memory](https://github.com/basicmachines-co/basic-memory)
- **Issue Tracker**: Report bugs and request features on GitHub
- **Contributions**: Pull requests are welcome following the contributing guidelines
- **Documentation**: Source for this documentation is also available in the repository

## Data Storage and Privacy

Basic Memory is designed with privacy as a core principle:

- **Local-First**: All data remains on your local machine
- **No Cloud Dependency**: No remote servers or accounts required
- **Telemetry**: Optional and disabled by default
- **Standard Formats**: All data is stored in standard file formats you control

## Implementation Details

### Entity Model

Basic Memory's core data model consists of:

- **Entities**: Documents in your knowledge base
- **Observations**: Facts or statements about entities
- **Relations**: Connections between entities
- **Tags**: Additional categorization for entities and observations

The system parses Markdown files to extract this structured information while preserving the human-readable format.

### Sync Process

The sync process:

1. Detects changes to files in the knowledge directory
2. Parses modified files to extract structured data
3. Updates the SQLite database with changes
4. Resolves forward references when new entities are created
5. Updates the search index for fast querying

### Search Engine

The search functionality:

1. Uses a combination of full-text search and semantic matching
2. Indexes observations, relations, and content
3. Supports wildcards and pattern matching in memory:// URLs
4. Traverses the knowledge graph to follow relationships
5. Ranks results by relevance to the query

## Relations
- relates_to [[Introduction to Basic Memory]] (System overview)
- relates_to [[CLI Reference]] (Command line tools)
- implements [[Knowledge Format]] (File structure and format)