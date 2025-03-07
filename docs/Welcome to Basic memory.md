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

## Core Functions

Basic Memory connects you and AI assistants through shared knowledge:

1. **Captures knowledge** from natural conversations with AI assistants
2. **Structures information** using simple semantic patterns in Markdown
3. **Enables knowledge reuse** across different conversations and sessions
4. **Maintains persistence** through local files you control completely

Both you and AI assistants like Claude can read from and write to the same knowledge base, creating a continuous
learning environment where each conversation builds upon previous ones.

![[Obsidian-CoffeeKnowledgeBase-examples-overlays.gif]]

## Technical Architecture

Basic Memory uses:

- **Files as the source of truth** - Everything is stored in plain Markdown files
- **Git-compatible storage** - All knowledge can be versioned, branched, and merged
- **Local SQLite database** - For fast indexing and searching only (not primary storage)
- **Memory:// URI scheme** - For precise knowledge referencing and navigation
- **Model Context Protocol (MCP)** - For seamless AI assistant integration

## Knowledge Structure

Knowledge in Basic Memory is organized as a semantic graph:

1. **Entities** - Distinct concepts represented by Markdown documents
2. **Observations** - Categorized facts and information about entities
3. **Relations** - Connections between entities that form the knowledge graph

This structure emerges from simple text patterns in standard Markdown:

```markdown
---
title: Coffee Brewing Methods
type: note
permalink: coffee/coffee-brewing-methods
tags:
- '#coffee'
- '#brewing'
- '#methods'
- '#demo'
---

# Coffee Brewing Methods

An exploration of different coffee brewing techniques, their characteristics, and how they affect flavor extraction.

## Overview

Coffee brewing is both an art and a science. Different brewing methods extract different compounds from coffee beans,
resulting in unique flavor profiles, body, and mouthfeel. The key variables in any brewing method are:

- Grind size
- Water temperature
- Brew time
- Coffee-to-water ratio
- Agitation/turbulence

## Observations

- [principle] Coffee extraction follows a predictable pattern: acids extract first, then sugars, then bitter compounds
  #extraction
- [method] Pour over methods generally produce cleaner, brighter cups with more distinct flavor notes #clarity

## Relations

- requires [[Proper Grinding Technique]]
- affects [[Flavor Extraction]]
```

Becomes

```json
{
  "entities": [
    {
      "permalink": "coffee/coffee-brewing-methods",
      "title": "Coffee Brewing Methods",
      "file_path": "Coffee Notes/Coffee Brewing Methods.md",
      "entity_type": "note",
      "entity_metadata": {
        "title": "Coffee Brewing Methods",
        "type": "note",
        "permalink": "coffee/coffee-brewing-methods",
        "tags": "['#coffee', '#brewing', '#methods', '#demo']"
      },
      "checksum": "bfa32a0f23fa124b53f0694c344d2788b0ce50bd090b55b6d738401d2a349e4c",
      "content_type": "text/markdown",
      "observations": [
        {
          "category": "principle",
          "content": "Coffee extraction follows a predictable pattern: acids extract first, then sugars, then bitter compounds #extraction",
          "tags": [
            "extraction"
          ],
          "permalink": "coffee/coffee-brewing-methods/observations/principle/coffee-extraction-follows-a-predictable-pattern-acids-extract-first-then-sugars-then-bitter-compounds-extraction"
        },
        {
          "category": "method",
          "content": "Pour over methods generally produce cleaner, brighter cups with more distinct flavor notes #clarity",
          "tags": [
            "clarity"
          ],
          "permalink": "coffee/coffee-brewing-methods/observations/method/pour-over-methods-generally-produce-cleaner-brighter-cups-with-more-distinct-flavor-notes-clarity"
        }
      ],
      "relations": [
        {
          "from_id": "coffee/coffee-bean-origins",
          "to_id": "coffee/coffee-brewing-methods",
          "relation_type": "pairs_with",
          "context": null,
          "permalink": "coffee/coffee-bean-origins/pairs-with/coffee/coffee-brewing-methods",
          "to_name": "Coffee Brewing Methods"
        },
        {
          "from_id": "coffee/flavor-extraction",
          "to_id": "coffee/coffee-brewing-methods",
          "relation_type": "affected_by",
          "context": null,
          "permalink": "coffee/flavor-extraction/affected-by/coffee/coffee-brewing-methods",
          "to_name": "Coffee Brewing Methods"
        }
      ],
      "created_at": "2025-03-06T14:01:23.445071",
      "updated_at": "2025-03-06T13:34:48.563606"
    }
  ]
}
```

Basic Memory understands how to build context via its semantic graph.

## User Control and File Management

Basic Memory gives you complete control over your knowledge:

- **Local-first storage** - All knowledge lives on your computer
- **Standard file formats** - Plain Markdown compatible with any editor
- **Directory organization** - Knowledge stored in `~/basic-memory` by default
- **Version control ready** - Use git for history, branching, and collaboration
- **Edit anywhere** - Modify files with any text editor or Obsidian

Changes to files automatically update the knowledge graph, and AI assistants can see your edits in future conversations.

## Documentation Map

Continue exploring Basic Memory with these guides:

- Installation and setup [[Getting Started with Basic Memory]]
- Comprehensive usage instructions [[User Guide]]
- Detailed explanation of knowledge structure [[Knowledge Format]]
- Reference for AI assistants using Basic Memory [[AI Assistant Guide]]
- Technical implementation details [[Technical Information]]
- Command line tool reference [[CLI Reference]]
- Obsidian integration guide [[Obsidian Integration]]
- Canvas visualization guide [[Canvas]]

## Next Steps

Start with the [[Getting Started with Basic Memory]] guide to install Basic Memory and configure it with your AI
assistant.