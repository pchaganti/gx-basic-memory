---
title: Introduction to Basic Memory
type: docs
permalink: docs/introduction
tags:
  - documentation
  - index
  - overview
---

# BASIC MEMORY

Basic Memory is a knowledge management system that allows you to build a persistent semantic graph from conversations
with AI assistants. All knowledge is stored in standard Markdown files on your computer, giving you full control and
ownership of your data.

Basic Memory connects you and AI assistants through shared knowledge:

1. **Captures knowledge** from natural conversations with AI assistants
2. **Structures information** using simple semantic patterns in Markdown
3. **Enables knowledge reuse** across different conversations and sessions
4. **Maintains persistence** through local files you control completely

Both you and AI assistants like Claude can read from and write to the same knowledge base, creating a continuous
learning environment where each conversation builds upon previous ones.

## Pick up your conversation right where you left off

- AI assistants can load context from local files in a new conversation
- Notes are saved locally as Markdown files in real time
- No project knowledge or special prompting required

![[Claude-Obsidian-Demo.mp4]]

Basic Memory uses:

- **Files as the source of truth** - Everything is stored in plain Markdown files
- **Git-compatible storage** - All knowledge can be versioned, branched, and merged
- **Local SQLite database** - For fast indexing and searching only (not primary storage)
- **Model Context Protocol (MCP)** - For seamless AI assistant integration

Basic Memory gives you complete control over your knowledge:

- **Local-first storage** - All knowledge lives on your computer
- **Standard file formats** - Plain Markdown compatible with any editor
- **Directory organization** - Knowledge stored in `~/basic-memory` by default
- **Version control ready** - Use git for history, branching, and collaboration
- **Edit anywhere** - Modify files with any text editor or Obsidian

Changes to files automatically sync with the knowledge graph, and AI assistants can see your edits in conversations.

## Documentation Map

Continue exploring Basic Memory with these guides:

- Installation and setup [[Getting Started with Basic Memory]]
- Comprehensive usage instructions [[User Guide]]
- Detailed explanation of knowledge structure [[Knowledge Format]]
- Obsidian integration guide [[Obsidian Integration]]
- Canvas visualization guide [[Canvas]]
- Command line tool reference [[CLI Reference]]
- Reference for AI assistants using Basic Memory [[AI Assistant Guide]]
- Technical implementation details [[Technical Information]]

## Next Steps

Start with the [[Getting Started with Basic Memory]] guide to install Basic Memory and configure it with your AI
assistant.