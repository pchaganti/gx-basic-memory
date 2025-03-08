---
title: User Guide
type: note
permalink: docs/user-guide
---

# User Guide

This guide explains how to effectively use Basic Memory in your daily workflow, from creating knowledge through conversations to building a rich semantic network.

## Basic Memory Workflow

Using Basic Memory follows a natural cycle:

1. **Have conversations** with AI assistants like Claude
2. **Capture knowledge** in Markdown files
3. **Build connections** between pieces of knowledge
4. **Reference your knowledge** in future conversations
5. **Edit files directly** when needed
6. **Sync changes** automatically

## Creating Knowledge

### Through Conversations

To create knowledge during conversations with Claude:

```
You: We've covered several authentication approaches. Could you create a note summarizing what we've discussed?

Claude: I'll create a note summarizing our authentication discussion.
```

This creates a Markdown file in your `~/basic-memory` directory with semantic markup.

### Direct File Creation

You can create files directly:

1. Create a new Markdown file in your `~/basic-memory` directory
2. Add frontmatter with title, type, and optional tags
3. Structure content with observations and relations
4. Save the file
5. Run `basic-memory sync` if not in watch mode

## Using Special Prompts

Basic Memory includes several special prompts that help you leverage your knowledge base more effectively. In apps like Claude Desktop, these prompts trigger specific tools to search and analyze your knowledge base.

### Continue Conversation

When you want to pick up where you left off on a topic:

```
You: Let's continue our conversation about authentication systems.
```

Behind the scenes:
- Claude searches your knowledge base for content about "authentication systems"
- It retrieves relevant documents and their relations
- It analyzes the context to understand where you left off
- It builds a comprehensive picture of what you've previously discussed
- It can then resume the conversation with all that context

This is particularly useful when:
- Starting a new session days or weeks after your last discussion
- Switching between multiple ongoing projects
- Building on previous work without repeating yourself

### Recent Activity

To get an overview of what you've been working on:

```
You: What have we been discussing recently?
```

Behind the scenes:
- Claude retrieves documents modified recently
- It analyzes patterns and themes
- It summarizes the key topics and changes
- It offers to continue working on any of those topics

This is useful for:
- Coming back after a break
- Getting a quick reminder of ongoing projects
- Deciding what to work on next

### Search

To find specific information in your knowledge base:

```
You: Find information about JWT authentication in my notes.
```

Behind the scenes:
- Claude performs a semantic search for "JWT authentication"
- It retrieves and ranks the most relevant documents
- It summarizes the key findings
- It offers to explore specific areas in more detail

This is useful for:
- Finding specific information quickly
- Exploring what you know about a topic
- Starting work on an existing topic

### Example

Claude Desktop lets you send a prompt to provide context. You can use this at the beginning of a chat to preload context without needing to copy paste all the time. By using one of the supplied prompts, Basic Memory will search the knowledge base and give the AI instructions for how to build context. 

Choose "Continue Conversation":

![[prompt 1.png|500]]

Enter a topic:

![[prompt2.png|500]]

Give optional additional instructions:

![[prompt3.png|500]]

Claude can build context from the supplied topic. This works independently of Claude Project information. All the context comes from your local knowledge base. 

![[prompt4.png|500]]


## Searching Your Knowledge Base

Basic Memory provides multiple ways to search and explore your knowledge base:

### Natural Language Search

The simplest way to search is to ask Claude directly:

```
You: What do I know about authentication methods?
```

Claude will search your knowledge base semantically and return relevant information.

### Search Prompt

Use the dedicated search prompt for more focused searches:

```
You: Search for "JWT authentication"
```

This triggers a specialized search that returns precise results with document titles, relevant excerpts, and offers to explore specific documents.

### Boolean Search

For more precise searches, use boolean operators to refine your queries:

```
You: Search for "authentication AND OAuth NOT basic"
```

Basic Memory supports standard boolean operators:

- **AND**: Find documents containing both terms
  ```
  You: Search for "python AND flask"
  ```
  This finds documents containing both "python" and "flask"

- **OR**: Find documents containing either term
  ```
  You: Search for "python OR javascript"
  ```
  This finds documents containing either "python" or "javascript"

- **NOT**: Exclude documents containing specific terms
  ```
  You: Search for "python NOT django"
  ```
  This finds documents containing "python" but excludes those containing "django"

- **Grouping with parentheses**: Control operator precedence
  ```
  You: Search for "(python OR javascript) AND web"
  ```
  This finds documents about web development that mention either Python or JavaScript

Boolean search is particularly useful for:
- Narrowing down results in large knowledge bases
- Finding specific combinations of concepts
- Excluding irrelevant content from search results
- Creating complex queries for precise information retrieval

### Memory URL Pattern Matching

For advanced searches, use memory:// URL patterns with wildcards:

```
You: Look at memory://auth* and summarize all authentication approaches.
```

Pattern matching supports:
- **Wildcards**: `memory://auth*` matches all permalinks starting with "auth"
- **Path patterns**: `memory://project/*/auth` matches auth documents in any project subfolder
- **Relation traversal**: `memory://auth-system/implements/*` finds all documents that implement the auth system

### Combining Search with Context Building

The most powerful searches build comprehensive context by following relationships:

```
You: Search for JWT authentication and then follow all implementation relations.
```

This builds a complete picture by:
1. Finding documents about JWT authentication
2. Following implementation relationships from those documents
3. Building a complete picture of how JWT is implemented across your system

### Search Best Practices

For effective searching:
1. **Be specific** with search terms and phrases
2. **Use boolean operators** to refine searches and find precise information
3. **Use technical terms** when searching for technical content
4. **Follow up** on search results by asking for more details about specific documents
5. **Combine approaches** by starting with search and then using memory:// URLs for precision
6. **Use relation traversal** to explore connected concepts after finding initial documents

## Referencing Knowledge

### Using memory:// URLs

Reference specific knowledge directly:

```
You: Please look at memory://authentication-approaches and suggest which approach would be best for our mobile app.
```

### Natural Language References

Reference knowledge conversationally:

```
You: What did we decide about authentication for the project?
```

### Advanced References

Follow connections across your knowledge graph:

```
You: Look at memory://project-architecture and check related documents to give me a complete picture.
```

## Working with Files

### File Location and Organization

By default, Basic Memory stores files in `~/basic-memory`:

- Browse this directory in your file explorer
- Organize files into subfolders
- Use git for version control

### File Format

Each knowledge file follows this structure:

```markdown
---
title: Authentication Approaches
type: note
tags: [security, architecture]
permalink: authentication-approaches
---

# Authentication Approaches

A comparison of authentication methods.

## Observations
- [approach] JWT provides stateless authentication #security
- [limitation] Session tokens require server-side storage #infrastructure

## Relations
- implements [[Security Requirements]]
- affects [[User Login Flow]]
```

### Editing Files

Modify files in any text editor:

1. Open the file in your preferred editor
2. Make changes to content, observations, or relations
3. Save the file
4. Basic Memory detects changes automatically when running in watch mode

## Building a Knowledge Graph

The value of Basic Memory comes from connections between pieces of knowledge.

### Creating Relations

When creating or editing notes, build connections:

```markdown
## Relations
- implements [[Security Requirements]]
- depends_on [[User Authentication]]
```

Relations can be:
- Hierarchical (part_of, contains)
- Directional (implements, depends_on)
- Associative (relates_to, similar_to)
- Temporal (precedes, follows)

Relations are also created via regular wiki-link style links within the body text.

### Forward References

Reference documents that don't exist yet:

```markdown
- will_impact [[Future Feature]]
```

These references resolve automatically when you create the referenced document.

## Conversation Continuity

Basic Memory maintains context across different conversations.

### Starting New Sessions with Context

When starting a new conversation with Claude, you can:

1. **Use special prompts** like "Continue conversation about..." or "What were we working on?"
2. **Reference specific documents** with memory:// URLs
3. **Ask about recent work** with "What have we been discussing recently?"
4. **Search for specific topics** with "Find information about..."

### Long-Term Projects

Maintain context for complex projects over time:

1. **Document key decisions** as you make them
2. **Create relationships** between project components
3. **Reference past decisions** when implementing features
4. **Update documentation** as the project evolves

### Tips for Effective Continuity

1. **Be specific about topics** when continuing a conversation
2. **Reference documents directly** with memory:// URLs for precision
3. **Create summary notes** after important discussions
4. **Update existing notes** rather than creating duplicates
5. **Build robust connections** between related topics

## Advanced Features

### Importing External Knowledge

Import existing conversations:

```bash
# From Claude
basic-memory import claude conversations

# From ChatGPT
basic-memory import chatgpt
```

After importing, run `basic-memory sync` to index everything.

### Obsidian Integration

Use with [Obsidian](https://obsidian.md):

1. Point Obsidian to your `~/basic-memory` directory
2. Use Obsidian's graph view to visualize your knowledge network
3. All changes sync back to Basic Memory

### Canvas Visualizations

Create visual knowledge maps:

```
You: Could you create a canvas visualization of our project components?
```

This generates an Obsidian canvas file showing the relationships between concepts.

### Advanced Memory URI Patterns

Use wildcards and patterns:

```
You: Review memory://project/*/requirements to summarize all project requirements.
```

## Command Line Interface

### Sync Commands

```bash
# One-time sync
basic-memory sync

# Watch for changes
basic-memory sync --watch
```

### Status and Information

```bash
# Check system status
basic-memory status

# View CLI help
basic-memory --help
```

### Import Commands

```bash
# Import from Claude
basic-memory import claude conversations

# Import from ChatGPT
basic-memory import chatgpt
```


## Multiple Projects  
  
Basic Memory supports managing multiple separate knowledge bases through projects. This feature allows you to maintain  
separate knowledge graphs for different purposes (e.g., personal notes, work projects, research topics).  

Basic Memory keeps a list of projects in a config file: ` ~/.basic-memory/config.json`
  
### Managing Projects  
  
```bash  
# List all configured projects  
basic-memory project list  
  
# Add a new project  
basic-memory project add work ~/work-basic-memory  
  
# Set the default project  
basic-memory project default work  
  
# Remove a project (doesn't delete files)  
basic-memory project remove personal  
  
# Show current project  
basic-memory project current  
```  
  
### Using Projects in Commands  
  
All commands support the `--project` flag to specify which project to use:  
  
```bash  
# Sync a specific project  
basic-memory --project=work sync  
  
# Run MCP server for a specific project  
basic-memory --project=personal mcp  
```  
  
You can also set the `BASIC_MEMORY_PROJECT` environment variable:  
  
```bash  
BASIC_MEMORY_PROJECT=work basic-memory sync  
```  
  
### Project Isolation  
  
Each project maintains:  
  
- Its own collection of markdown files in the specified directory  
- A separate SQLite database for that project  
- Complete knowledge graph isolation from other projects
## Workflow Tips

1. Run sync in watch mode for automatic updates
2. Use git for version control of your knowledge base
3. Review and edit AI-created content for accuracy
4. Periodically organize and refine your knowledge structure
5. Build rich connections between related ideas
6. Use forward references to plan future documentation
7. Start conversations with special prompts to leverage existing knowledge

## Troubleshooting

### Sync Issues

If changes aren't showing up:
1. Verify `basic-memory sync --watch` is running
2. Run `basic-memory status` to check system state
3. Try a manual sync with `basic-memory sync`

### Missing Content

If content isn't found:
1. Check the exact path and permalink
2. Try searching with more general terms
3. Verify the file exists in your knowledge base

### Relation Problems

If relations aren't working:
1. Ensure exact title matching in [[WikiLinks]]
2. Check for typos in relation types
3. Verify both documents exist

## Relations
- implements [[Knowledge Format]] (How knowledge is structured)
- relates_to [[Getting Started with Basic Memory]] (Setup and first steps)
- relates_to [[Canvas]] (Creating visual knowledge maps)
- relates_to [[CLI Reference]] (Command line tools)