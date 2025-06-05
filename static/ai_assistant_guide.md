# AI Assistant Guide for Basic Memory

This guide helps AIs use Basic Memory tools effectively when working with users. It covers reading, writing, and
navigating knowledge through the Model Context Protocol (MCP).

## Overview

Basic Memory allows you and users to record context in local Markdown files, building a rich knowledge base through
natural conversations. The system automatically creates a semantic knowledge graph from simple text patterns.

- **Local-First**: All data is stored in plain text files on the user's computer
- **Real-Time**: Users see content updates immediately
- **Bi-Directional**: Both you and users can read and edit notes
- **Semantic**: Simple patterns create a structured knowledge graph
- **Persistent**: Knowledge persists across sessions and conversations

## The Importance of the Knowledge Graph

**Basic Memory's value comes from connections between notes, not just the notes themselves.**

When writing notes, your primary goal should be creating a rich, interconnected knowledge graph:

1. **Increase Semantic Density**: Add multiple observations and relations to each note
2. **Use Accurate References**: Aim to reference existing entities by their exact titles
3. **Create Forward References**: Feel free to reference entities that don't exist yet - Basic Memory will resolve these
   when they're created later
4. **Create Bidirectional Links**: When appropriate, connect entities from both directions
5. **Use Meaningful Categories**: Add semantic context with appropriate observation categories
6. **Choose Precise Relations**: Use specific relation types that convey meaning

Remember: A knowledge graph with 10 heavily connected notes is more valuable than 20 isolated notes. Your job is to help
build these connections!

## Core Tools Reference

**Writing knowledge - THE MOST IMPORTANT TOOL!**
```
write_note(
    title="Search Design",
    content="# Search Design\n\n## Overview\nSearch functionality design and implementation.\n\n## Observations\n- [requirement] Must support full-text search #search\n- [decision] Using vector embeddings for semantic search #technology\n\n## Relations\n- implements [[Search Requirements]]\n- part_of [[API Specification]]",
    folder="specs",
    tags=["search", "design"]
)
```

**Reading knowledge:**
```
read_note("Search Design")               # By exact title
read_note("specs/search-design")         # By permalink  
read_note("memory://specs/search")       # By memory URL
```

**Incremental editing (v0.13.0) - REQUIRES EXACT IDENTIFIERS:**
```
edit_note(
    identifier="Search Design",             # Must be EXACT title/permalink
    operation="append",
    content="\n## Implementation Notes\n- Added caching layer for performance"
)

edit_note(
    identifier="API Documentation", 
    operation="replace_section",
    section="## Authentication",
    content="Updated authentication using JWT tokens with refresh capability."
)
```

**File organization (v0.13.0) - REQUIRES EXACT IDENTIFIERS:**
```
move_note(
    identifier="Old Meeting Notes",          # Must be EXACT title/permalink
    destination_path="archive/2024/meeting-notes.md"
)
```

**Searching for knowledge:**
```
search_notes(
    query="authentication system",
    page=1,
    page_size=10
)
```

**Building context from the knowledge graph:**
```
build_context(
    url="memory://specs/search",
    depth=2,
    timeframe="1 month"
)
```

**Checking recent changes:**
```
recent_activity(
    timeframe="1 week",
    depth=1
)
```

**Creating knowledge visualizations:**
```
canvas(
    nodes=[
        {"id": "search", "x": 100, "y": 100, "width": 200, "height": 100, "type": "text", "text": "Search Design"},
        {"id": "api", "x": 400, "y": 100, "width": 200, "height": 100, "type": "text", "text": "API Specification"}
    ],
    edges=[
        {"id": "link1", "fromNode": "search", "toNode": "api"}
    ],
    title="System Architecture",
    folder="diagrams"
)
```

**Monitoring sync status:**
```
sync_status()                           # Check overall system status
sync_status(project="work-notes")       # Check specific project status
```

## memory:// URLs Explained

Basic Memory uses a special URL format to reference entities in the knowledge graph:

- `memory://title` - Reference by title
- `memory://folder/title` - Reference by folder and title
- `memory://permalink` - Reference by permalink
- `memory://path/relation_type/*` - Follow all relations of a specific type
- `memory://path/*/target` - Find all entities with relations to target

## Semantic Markdown Format

Knowledge is encoded in standard markdown using simple patterns:

**Observations** - Facts about an entity:

```markdown
- [category] This is an observation #tag1 #tag2 (optional context)
```

**Relations** - Links between entities:

```markdown
- relation_type [[Target Entity]] (optional context)
```

**Common Categories & Relation Types:**

- Categories: `[idea]`, `[decision]`, `[question]`, `[fact]`, `[requirement]`, `[technique]`, `[recipe]`, `[preference]`
- Relations: `relates_to`, `implements`, `requires`, `extends`, `part_of`, `pairs_with`, `inspired_by`,
  `originated_from`

## When to Record Context

**Always consider recording context when**:

1. Users make decisions or reach conclusions
2. Important information emerges during conversation
3. Multiple related topics are discussed
4. The conversation contains information that might be useful later
5. Plans, tasks, or action items are mentioned

**Protocol for recording context**:

1. Identify valuable information in the conversation
2. Ask the user: "Would you like me to record our discussion about [topic] in Basic Memory?"
3. If they agree, use `write_note` to capture the information
4. If they decline, continue without recording
5. Let the user know when information has been recorded: "I've saved our discussion about [topic] to Basic Memory."

## Understanding User Interactions

Users will interact with Basic Memory in patterns like:

1. **Creating knowledge**:
   ```
   Human: "Let's write up what we discussed about search."
   
   You: I'll create a note capturing our discussion about the search functionality.
   [Use write_note() to record the conversation details]
   ```

2. **Referencing existing knowledge**:
   ```
   Human: "Take a look at memory://specs/search"
   
   You: I'll examine that information.
   [Use build_context() to gather related information]
   [Then read_note() to access specific content]
   ```

3. **Finding information**:
   ```
   Human: "What were our decisions about auth?"
   
   You: Let me find that information for you.
   [Use search_notes() to find relevant notes]
   [Then build_context() to understand connections]
   ```

## Key Things to Remember

1. **Files are Truth**
    - All knowledge lives in local files on the user's computer
    - Users can edit files outside your interaction
    - Changes need to be synced by the user (usually automatic)
    - Always verify information is current with `recent_activity()`

2. **Building Context Effectively**
    - Start with specific entities
    - Follow meaningful relations
    - Check recent changes
    - Build context incrementally
    - Combine related information

3. **Writing Knowledge Wisely**
    - Using the same title+folder will overwrite existing notes
    - Structure content with clear headings and sections
    - Use semantic markup for observations and relations
    - Keep files organized in logical folders

## Common Knowledge Patterns

### Capturing Decisions

```markdown
# Coffee Brewing Methods

## Context

I've experimented with various brewing methods including French press, pour over, and espresso.

## Decision

Pour over is my preferred method for light to medium roasts because it highlights subtle flavors and offers more control
over the extraction.

## Observations

- [technique] Blooming the coffee grounds for 30 seconds improves extraction #brewing
- [preference] Water temperature between 195-205°F works best #temperature
- [equipment] Gooseneck kettle provides better control of water flow #tools

## Relations

- pairs_with [[Light Roast Beans]]
- contrasts_with [[French Press Method]]
- requires [[Proper Grinding Technique]]
```

### Recording Project Structure

```markdown
# Garden Planning

## Overview

This document outlines the garden layout and planting strategy for this season.

## Observations

- [structure] Raised beds in south corner for sun exposure #layout
- [structure] Drip irrigation system installed for efficiency #watering
- [pattern] Companion planting used to deter pests naturally #technique

## Relations

- contains [[Vegetable Section]]
- contains [[Herb Garden]]
- implements [[Organic Gardening Principles]]
```

### Technical Discussions

```markdown
# Recipe Improvement Discussion

## Key Points

Discussed strategies for improving the chocolate chip cookie recipe.

## Observations

- [issue] Cookies spread too thin when baked at 350°F #texture
- [solution] Chilling dough for 24 hours improves flavor and reduces spreading #technique
- [decision] Will use brown butter instead of regular butter #flavor

## Relations

- improves [[Basic Cookie Recipe]]
- inspired_by [[Bakery-Style Cookies]]
- pairs_with [[Homemade Ice Cream]]
```

### Creating Effective Relations

When creating relations, you can:

1. Reference existing entities by their exact title
2. Create forward references to entities that don't exist yet

**Example workflow for creating notes with effective relations:**

1. **First, search for existing entities to reference:**
```
search_notes(query="travel")
```

2. **Check recent activity for current topics:**
```
recent_activity(timeframe="1 week")
```

3. **Create the note with both existing and forward references:**
```
write_note(
    title="Tokyo Neighborhood Guide",
    content="# Tokyo Neighborhood Guide

## Overview
Details about different Tokyo neighborhoods and their unique characteristics.

## Observations
- [area] Shibuya is a busy shopping district #shopping
- [transportation] Yamanote Line connects major neighborhoods #transit
- [recommendation] Visit Shimokitazawa for vintage shopping #unique
- [tip] Get a Suica card for easy train travel #convenience

## Relations
- references [[Packing Tips]]           # Forward reference (will be linked when created)
- part_of [[Japan Travel Guide]]        # Existing reference (if found in search)
- relates_to [[Transportation Options]] # Recent reference (if found in activity)
- located_in [[Tokyo]]                  # Forward reference
- visited_during [[Spring 2023 Trip]]   # Forward reference",
    folder="travel",
    tags=["tokyo", "neighborhoods", "travel"]
)
```

**Key points:**
- Use exact titles from search results for existing entities: `[[Exact Title Found]]`
- Forward references are fine - they'll be linked automatically when target notes are created
- Check recent activity to reference currently active topics
- Use meaningful relation types: `part_of`, `located_in`, `visited_during` vs generic `relates_to`

## Error Handling

Common issues to watch for:

**1. Missing Content - Use Search as Fallback**
```
# If read_note fails, try search instead
search_notes(query="Document")
# Then use exact result from search:
read_note("Exact Document Title Found")
```

**2. Strict Mode for Edit/Move Operations (v0.13.0)**

❌ **This might fail if identifier isn't exact:**
```
edit_note(identifier="Meeting Note", operation="append", content="new content")
```

✅ **Safe approach - search first, then use exact result:**
```
# 1. Search first to find exact identifier
search_notes(query="meeting")

# 2. Use exact title from search results  
edit_note(identifier="Meeting Notes 2024", operation="append", content="new content")

# Same pattern for move_note:
search_notes(query="old note")
move_note(identifier="Old Meeting Notes", destination_path="archive/old-notes.md")
```

**3. Forward References (Unresolved Relations)**

Forward references are a **feature, not an error!** Basic Memory automatically links them when target notes are created.

When you see unresolved relations in the response:
- Inform users: "I've created forward references that will be linked when you create those notes"
- Optionally suggest: "Would you like me to create any of these notes now to complete the connections?"

**4. Sync Issues**

If information seems outdated:
```
recent_activity(timeframe="1 hour")
```
If no recent activity shows, check sync status first:
```
sync_status()
```
If sync is pending or failed, suggest: "You might need to run `basic-memory sync`"

**5. Understanding Sync Status**

The `sync_status()` tool provides essential information about Basic Memory's operational state:

```
sync_status()                           # Check overall system readiness
sync_status(project="work-notes")       # Check specific project context
```

**When to use sync_status:**
- At the start of conversations to verify system readiness
- When operations seem slow or fail unexpectedly  
- Before working with large knowledge bases
- When switching between projects
- To provide users context about background processing

**What sync_status tells you:**
- **System Ready**: Whether all files are indexed and tools are operational
- **Active Processing**: Which projects are currently syncing with progress indicators
- **Project Status**: Individual project sync states (👁️ watching, ✅ completed, 🔄 syncing, ❌ failed, ⏳ pending)
- **Error Details**: Specific error messages for failed sync operations
- **Guidance**: Next steps when issues are detected

**Using sync_status effectively:**
- Check status if tools return unexpected results
- Use project parameter when working in multi-project setups
- Share status with users when explaining delays
- Monitor progress during initial setup or large imports

## Best Practices

1. **Proactively Record Context**
    - Offer to capture important discussions
    - Record decisions, rationales, and conclusions
    - Link to related topics
    - Ask for permission first: "Would you like me to save our discussion about [topic]?"
    - Confirm when complete: "I've saved our discussion to Basic Memory"

2. **Create a Rich Semantic Graph**
    - **Add meaningful observations**: Include at least 3-5 categorized observations in each note
    - **Create deliberate relations**: Connect each note to at least 2-3 related entities
    - **Use existing entities**: Before creating a new relation, search for existing entities
    - **Verify wikilinks**: When referencing `[[Entity]]`, use exact titles of existing notes
    - **Check accuracy**: Use `search_notes()` or `recent_activity()` to confirm entity titles
    - **Use precise relation types**: Choose specific relation types that convey meaning (e.g., "implements" instead
      of "relates_to")
    - **Consider bidirectional relations**: When appropriate, create inverse relations in both entities

3. **Structure Content Thoughtfully**
    - Use clear, descriptive titles
    - Organize with logical sections (Context, Decision, Implementation, etc.)
    - Include relevant context and background
    - Add semantic observations with appropriate categories
    - Use a consistent format for similar types of notes
    - Balance detail with conciseness

4. **Navigate Knowledge Effectively**
    - Start with specific searches
    - Follow relation paths
    - Combine information from multiple sources
    - Verify information is current
    - Build a complete picture before responding

5. **Help Users Maintain Their Knowledge**
    - Suggest organizing related topics
    - Identify potential duplicates
    - Recommend adding relations between topics
    - Offer to create summaries of scattered information
    - Suggest potential missing relations: "I notice this might relate to [topic], would you like me to add that
      connection?"

Built with ♥️ b
y Basic Machines