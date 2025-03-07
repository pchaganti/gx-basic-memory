---
title: Getting Started with Basic Memory
type: note
permalink: docs/getting-started
---

# Getting Started with Basic Memory

This guide will help you install Basic Memory, configure it with Claude Desktop, and create your first knowledge notes through conversations.

## Installation

### 1. Install Basic Memory

```bash
# Install with uv (recommended)
uv install basic-memory

# Or with pip
pip install basic-memory
```

> **Important**: You need to install Basic Memory using one of the commands above to use the command line tools. The `uvx` command mentioned in the Claude Desktop configuration is only for enabling Claude to access Basic Memory.

### 2. Configure Claude Desktop

To enable Claude to read and write to your knowledge base, edit the Claude Desktop configuration file (usually at `~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "basic-memory": {
      "command": "uvx",
      "args": [
        "basic-memory",
        "mcp"
      ]
    }
  }
}
```

This configuration uses `uvx` to execute Basic Memory without requiring a full installation in Claude's environment.

### 3. Start the Sync Service

Start the sync service to monitor your files for changes:

```bash
# One-time sync
basic-memory sync

# For continuous monitoring (recommended)
basic-memory sync --watch
```

The `--watch` flag enables automatic detection of file changes, keeping your knowledge base current.

## Creating Your First Knowledge Note

1. **Start a conversation in Claude Desktop** about any topic:
   ```
   You: "Let's talk about coffee brewing methods I've been experimenting with."
   ```

2. **Have a natural conversation** about the topic

3. **Ask Claude to create a note**:
   ```
   You: "Could you create a note summarizing what we've discussed about coffee brewing?"
   ```

4. **Claude creates a Markdown file** in your `~/basic-memory` directory

5. **View and edit the file** with any text editor or Obsidian

## Using Special Prompts

Basic Memory includes special prompts that help you start conversations with context from your knowledge base:

### Continue Conversation

To resume a previous topic:

```
You: "Let's continue our conversation about coffee brewing."
```

This prompt triggers Claude to:
1. Search your knowledge base for relevant content about coffee brewing
2. Build context from these documents
3. Resume the conversation with full awareness of previous discussions

### Recent Activity

To see what you've been working on:

```
You: "What have we been discussing recently?"
```

This prompt causes Claude to:
1. Retrieve documents modified in the recent past
2. Summarize the topics and main points
3. Offer to continue any of those discussions

### Search

To find specific information:

```
You: "Find information about pour over coffee methods."
```

Claude will:
1. Search your knowledge base for relevant documents
2. Summarize the key findings
3. Offer to explore specific documents in more detail

## Using Your Knowledge Base

### Referencing Knowledge

In future conversations, reference your existing knowledge:

```
You: "What water temperature did we decide was optimal for coffee brewing?"
```

Or directly reference notes using memory:// URLs:

```
You: "Take a look at memory://coffee-brewing-methods and let's discuss how to improve my technique."
```

### Building On Previous Knowledge

Basic Memory enables continuous knowledge building:

1. **Reference previous discussions** in new conversations
2. **Add to existing notes** through conversations
3. **Create connections** between related topics
4. **Follow relationships** to build comprehensive context

## Importing Existing Conversations

Import your existing AI conversations:

```bash
# From Claude
basic-memory import claude conversations

# From ChatGPT
basic-memory import chatgpt
```

After importing, run `basic-memory sync` to index everything.

## Quick Tips

- Keep `basic-memory sync --watch` running in a terminal window
- Use special prompts (Continue Conversation, Recent Activity, Search) to start contextual discussions
- Build connections between notes for a richer knowledge graph
- Use direct memory:// URLs when you need precise context
- Use git to version control your knowledge base
- Review and edit AI-generated notes for accuracy

## Next Steps

After getting started, explore these areas:

1. **Read the [[User Guide]]** for comprehensive usage instructions
2. **Understand the [[Knowledge Format]]** to learn how knowledge is structured
3. **Set up [[Obsidian Integration]]** for visual knowledge navigation
4. **Learn about [[Canvas]]** visualizations for mapping concepts
5. **Review the [[CLI Reference]]** for command line tools
