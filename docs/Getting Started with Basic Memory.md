---
title: Getting Started with Basic Memory
type: note
permalink: docs/getting-started
---

# Getting Started with Basic Memory

This guide will help you install Basic Memory, configure it with Claude Desktop, and create your first knowledge notes
through conversations.

Basic Memory uses the [Model Context Protocol](https://modelcontextprotocol.io/introduction) (MCP) to connect with LLMs.
It can be used with any service that supports the MCP, but Claude Desktop works especially well.

## Installation

### 1. Install Basic Memory

```bash
# Install with uv (recommended).  
uv tool install basic-memory

# Or with pip
pip install basic-memory
```

> **Important**: You need to install Basic Memory using one of the commands above to use the command line tools.

Using `uv tool install` will install the basic-memory package in a standalone virtual environment.
See the [UV docs](https://docs.astral.sh/uv/concepts/tools/) for more info.

### 2. Configure Claude Desktop

Claude Desktop often has trouble finding executables in your user path. Follow these steps for a reliable setup:

#### Step 1: Find the absolute path to uvx

Open Terminal and run:

```bash
which uvx
```

This will show you the full path (e.g., `/Users/yourusername/.cargo/bin/uvx`).

#### Step 2: Edit Claude Desktop Configuration

Edit the configuration file located at `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "basic-memory": {
      "command": "/absolute/path/to/uvx",
      "args": [
        "basic-memory",
        "mcp"
      ]
    }
  }
}
```

Replace `/absolute/path/to/uvx` with the actual path you found in Step 1.

> **Note**: Using absolute paths is necessary because Claude Desktop cannot access binaries in your user PATH.

#### Step 3: Restart Claude Desktop

Close and reopen Claude Desktop for the changes to take effect.

### 3. Start the Sync Service

Start the sync service to monitor your files for changes:

```bash
# One-time sync
basic-memory sync

# For continuous monitoring (recommended)
basic-memory sync --watch
```

The `--watch` flag enables automatic detection of file changes, keeping your knowledge base current.

### 4. Staying Updated

To update Basic Memory when new versions are released:

```bash
# Update with uv (recommended)
uv tool upgrade basic-memory 

# Or with pip 
pip install --upgrade basic-memory
```

> **Note**: After updating, you'll need to restart Claude Desktop and your sync process for changes to take effect.

## Troubleshooting Installation

### Common Issues

#### Claude Says "No Basic Memory Tools Available"

If Claude cannot find Basic Memory tools:

1. **Check absolute paths**: Ensure you're using complete absolute paths to uvx in the Claude Desktop configuration
2. **Verify installation**: Run `basic-memory --version` in Terminal to confirm Basic Memory is installed
3. **Restart applications**: Restart both Terminal and Claude Desktop after making configuration changes
4. **Check sync status**: Ensure `basic-memory sync --watch` is running

#### Permission Issues

If you encounter permission errors:

1. Check that Basic Memory has access to create files in your home directory
2. Ensure Claude Desktop has permission to execute the uvx command

## Creating Your First Knowledge Note

1. **Start the sync process** in a Terminal window:
   ```bash
   basic-memory sync --watch
   ```
   Keep this running in the background.

2. **Open Claude Desktop** and start a new conversation.

3. **Have a natural conversation** about any topic:
   ```
   You: "Let's talk about coffee brewing methods I've been experimenting with."
   Claude: "I'd be happy to discuss coffee brewing methods..."
   You: "I've found that pour over gives more flavor clarity than French press..."
   ```

4. **Ask Claude to create a note**:
   ```
   You: "Could you create a note summarizing what we've discussed about coffee brewing?"
   ```

5. **Confirm note creation**:
   Claude will confirm when the note has been created and where it's stored.

6. **View the created file** in your `~/basic-memory` directory using any text editor or Obsidian.
   The file structure will look similar to:
   ```markdown
   ---
   title: Coffee Brewing Methods
   permalink: coffee-brewing-methods
   ---
   
   # Coffee Brewing Methods
   
   ## Observations
   - [method] Pour over provides more clarity...
   - [technique] Water temperature at 205°F...
   
   ## Relations
   - relates_to [[Other Coffee Topics]]
   ```

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

See [[User Guide#Using Special Prompts]] for further information.

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