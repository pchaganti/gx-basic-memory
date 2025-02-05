# Basic Memory

Basic Memory lets you build persistent knowledge through natural conversations with Large Language Models (LLMs) like
Claude, while keeping everything in simple markdown files on your computer.

## What Problem Does This Solve?

Most people use LLMs like calculators - paste in some text, expect to get an answer back, repeat. Each conversation
starts fresh,
and any knowledge or context is lost. Some try to work around this by:

- Saving chat histories (but they're hard to reference)
- Copying and pasting previous conversations (messy and repetitive)
- Using RAG systems to query documents (complex and often cloud-based)

Basic Memory takes a different approach by letting both humans and LLMs read and write knowledge naturally using
standard markdown files. This means:

- Your knowledge stays in files you control
- Both you and the LLM can read and write notes
- Context persists across conversations
- Context stays local and user controlled

## How It Works in Practice

Let's say you're working on a new project and want to capture design decisions. Here's how it works:

1. Start by chatting normally:

```markdown
We need to design a new auth system, some key features:

- local first, don't delegate users to third party system
- support multiple platforms via jwt
- want to keep it simple but secure
```

... continue conversation.

2. Ask Claude to help structure this knowledge:

```
"Lets write a note about the auth system design."
```

Claude creates a new markdown file on your system (which you can see instantly in Obsidian or your editor):

```markdown
---
title: Auth System Design
permalink: auth-system-design
tags
- design
- auth
---

# Auth System Design

## Observations

- [requirement] Local-first authentication without third party delegation
- [tech] JWT-based auth for cross-platform support
- [principle] Balance simplicity with security

## Relations

- implements [[Security Requirements]]
- relates_to [[Platform Support]]
- referenced_by [[JWT Implementation]]
```

The note embeds semantic content (Observations) and links to other topics (Relations) via simple markdown formatting.

3. You can edit this file directly in your editor in real time:

```markdown
# Auth System Design

## Observations

- [requirement] Local-first authentication without third party delegation
- [tech] JWT-based auth for cross-platform support
- [principle] Balance simplicity with security
- [decision] Will use bcrypt for password hashing # Added by you

## Relations

- implements [[Security Requirements]]
- relates_to [[Platform Support]]
- referenced_by [[JWT Implementation]]
- blocks [[User Service]]  # Added by you
```

4. In a new chat with Claude, you can reference this knowledge:

```
"Claude, look at memory://auth-system-design for context about our auth system"
```

Claude can now:

- Read your original requirements
- See your added decisions
- Follow links to related documents
- Build rich context from the knowledge graph

Everything stays in local markdown files that you can:

- Edit in any text editor
- Put in git
- Back up normally
- Share when you want to

## Technical Implementation

Under the hood, Basic Memory:

1. Stores everything in markdown files
2. Uses a SQLite database just for searching and indexing
3. Extracts semantic meaning from simple markdown patterns
4. Maintains a local knowledge graph from file content

The file format is just markdown with some simple markup:

Frontmatter

- title
- type
- permalink
- optional metadata

Observations

- facts about a topic

```markdown
- [category] content #tag (optional context)
```

Relations

- links to other topics

```markdown
- relation_type [[WikiLink]] (optional context)
```

Example:

```markdown
---
title: Note tile
type: note
permalink: unique/stable/id  # Added automatically
tags
- tag1
- tag2
---

# Note Title

Regular markdown content...

## Observations

- [category] Structured knowledge #tag (optional context)
- [idea] Another observation

## Relations

- links_to [[Other Note]]
- implements [[Some Spec]]
```

Basic Memory will parse the markdown and derive the semantic relationships in the content.

## Using with Claude

Basic Memory works with the Claude desktop app (https://claude.ai/):

1. Install Basic Memory locally:

```bash
{
  "mcpServers": {
    "basic-memory": {
      "command": "uvx",
      "args": [
        "basic-memory"
      ]
    }
}
```

2. Add to Claude Desktop:

```
Basic Memory is available with these tools:
- write_note() for creating/updating notes
- read_note() for loading notes
- build_context() to load notes via memory:// URLs
- recent_activity() to find recently updated information
- search() to search infomation in the knowledge base
```

3. Install via uv

```bash
uv add  basic-memory

# sync local knowledge updates
basic-memory sync

# run realtime sync process
basic-memory sync --watch
```

## Design Philosophy

Basic Memory is built on some key ideas:

- Your knowledge should stay in files you control
- Both humans and AI should use natural formats
- Simple text patterns can capture rich meaning
- Local-first doesn't mean feature-poor

## License

AGPL-3.0