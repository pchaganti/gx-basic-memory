# Basic Memory Tasks

## Current Focus

### Observation Management

Implement update/remove functionality for observations with a focus on maintainability and consistency with our "
filesystem is source of truth" principle.

Options under consideration:

1. Bulk Update Approach
    - Update all observations at once
    - Pros:
        - Simpler file operations
        - No need to match on observation content
        - Easier database synchronization
        - Very consistent with "filesystem is source of truth"
    - Cons:
        - Less efficient - rewrites everything for small changes
        - Potential concurrency implications

2. Tracked Observations Approach
    - Use markdown comments for observation IDs
   ```markdown
   # Entity Name
   type: entity_type
   
   ## Observations
   - <!-- obs-id: abc123 -->
     This is an observation
   ```
    - Pros:
        - Can track individual observations
        - Enables precise updates/deletes
    - Cons:
        - More complex markdown parsing
        - IDs visible in markdown

3. Diff-based Approach
    - Implement observation-aware diffing
    - Track changes at observation level
    - Pros:
        - More efficient updates
        - Preserves manual edits
    - Cons:
        - More complex implementation
        - Need to handle merge conflicts

4. Position-based Management
    - Track observations by their position/order
    - Pros:
        - No need for explicit IDs
        - Clean markdown
    - Cons:
        - Fragile if order changes
        - Hard to handle concurrent edits

## Completed

- [x] Extract file operations to fileio.py module
- [x] Update EntityService to use fileio functions
- [x] Initial ObservationService implementation
- [x] Basic test coverage

## Future Work

- [ ] Implement observation updates/removals (exploring options above)
- [ ] Proper session management for concurrent operations
- [ ] EntityService tests using new fileio module
- [ ] More sophisticated search functionality
- [ ] Handle markdown formatting edge cases

## TODO

### refactor input schema

1. Observations Format:
   Old (JSON) way I tried first:

```python
"observations": ["First observation", "Second observation"]  # Simple string array
```

New required format:

```python
"observations": [
    {"content": "First observation"},
    {"content": "Second observation"}
]  # Array of objects with content field
```

2. Relations Format:
   Old way:

```python
"relations": [
    {"from": "EntityName", "to": "OtherEntity", "relationType": "relates_to"}  # Using names
]
```

New format:

```python
"relations": [
    {"fromId": "20241210-entity-id", "toId": "20241210-other-id", "relationType": "relates_to"}  # Using IDs
]
```

My preferences:

1. For observations: The simple string array felt more intuitive for basic use, but I can see the benefits of the object
   format:
    - Allows for additional metadata (context, timestamps, etc.)
    - More explicit about what each field means
    - Consistent with how we'd want to store this in a database

2. For relations: Using IDs is technically better but requires an extra lookup step in my workflow:
    - I have to first create the entities to get their IDs
    - Then use those IDs to create relations
    - Makes it harder to create entities and relations in a single step

Suggestions for making it more intuitive:

1. For observations: We could have a helper function that accepts either format:

```python
# Both would work:
create_entities([{
    "name": "Entity",
    "entityType": "type",
    "observations": ["Simple string obs"]  # Auto-converted to object format
}])

create_entities([{
    "name": "Entity",
    "entityType": "type",
    "observations": [{"content": "Full object obs"}]  # Native format
}])
```

2. For relations: Maybe allow a name-based helper function:

```python
# Instead of requiring IDs:
create_relations_by_name([{
    "from": "EntityName",
    "to": "OtherEntity",
    "relationType": "relates_to"
}])
```

3. A combined creation function for when we want to create entities and their relations together:

```python
create_entity_with_relations({
    "entity": {
        "name": "NewEntity",
        "entityType": "type",
        "observations": ["Obs 1", "Obs 2"]
    },
    "relations": [{
        "to": "ExistingEntity",
        "relationType": "relates_to"
    }]
})
```

The current schema is more "correct" from a software engineering perspective, but these helpers could make it more
natural to use while maintaining the rigorous underlying structure. What do you think about these suggestions? Would you
prefer to keep it strict for clarity, or add some convenience layers?

### entity file organization

- my problems
    - wall of text is hard to scan visually
    - files are not ordered or grouped granular enough. Only `<date>_<entity_name>.md`
    - hard to tell when a new entity file is added

Possible fixes:

- use subdirectories?

## TASKS

1. **Core Functionality Improvements**
    - [ ] entity.description addition
    - [ ] subdirectories 
      - Paul needs this for markdown view
    - [ ] improve tool api
    - [ ] Choose and implement observation update/removal strategy
    - [ ] Handle relationship updates in files
    - [ ] Complete full CRUD operations
      - delete
    - [ ] Improve search functionality (currently broken as we discovered)

### Suggested Sequence

1. **Schema Update First**
   - Add `entity.description` field
   - This affects database, Pydantic models, and file format
   - Good foundation for other changes

2. **File Organization**
   - Add subdirectory support
   - Affects:
     - File path handling
     - Entity loading/saving
     - URI resolution
   - Will make Paul's markdown viewing experience better

3. **Tool API Improvements**
   - Cleaner input/output schemas
   - More consistent patterns
   - Better error handling
   - This sets us up for implementing the remaining operations

4. **Core Operations**
   - Implement delete operations
   - Update/remove observations
   - Relationship updates in files
   - Building on the improved API

5. **Search Fix**
   - Can properly tackle this after file organization
   - Will benefit from improved schema

Would you like me to:
1. Start with the schema update for entity.description?
2. Plan out the subdirectory implementation?
3. Or focus on a different area?

I think the schema update would be a clean, contained change to start with, but I'm happy to tackle whichever part you think would be most valuable first.


2. **Robustness & Testing**
    - Fix DI issues
      - Learn from fastmcp patterns
    - Markdown service
      - markdown.py
      -python-frontmatter
    - Complete test coverage
      - Expand testing across services
      - 100% coverate
    - Improve error handling and logging
    - Add comprehensive type hints

3. **Architecture Improvements**
    - Handle concurrent file operations safely
    - Implement proper session management
    - Balance file operations and DB sync
    - Handle markdown formatting edge cases

4. **Documentation & Infrastructure**
    - Document core modules
    - Implement proper backup strategy
    - Add file change versioning
    - Improve CLI interface


## Ideas

- need update tool

### 2-way sync

- Enable updates to the markdown files to be able to be seen by AI
    - possible via tool sync
    - filesystem notifications via agent?
    - Claude can use `file_write` tool to edit Entity files also

### Projects

- support multiple projects
- figure out flow
    - load project at startup?
    - switch project during chat?

### References

- better support for ref:// references
- should we call them memory://<project>/<entity>
- use Prompt to invoke reference uri

### Entity File format

- Consider using wiki link format:
  [[20241210-ai_human_collaboration_model]] improves

instead of
[20241210-basic-memory] validates_design_of

- use frontmatter for file header

### Code

- cleanup server.py
- use markdown.py?
- fastmcp?
- Entity.description

### Other Features

- Search
- webui
- python notebook?
- vector eb extension for sqlite

#### Obsidian

- use as file viewer editor
- create knowledge graph?

#### Save chats

I'll sketch out a potential schema for chat sessions in our system:

```
{
  `entities`: [
    {
      `name`: `Chat_Entity_Design`,
      `entityType`: `design_proposal`,
      `observations`: [
        {
          `content`: `Entity Schema:
type: chat_session
date: ISO timestamp
participants: [human, ai]
topic: string
context_refs: [memory://<project>/<entity_id>]
key_decisions: [string]
summary: string`
        },
        {
          `content`: `File Format (frontmatter):
---
type: chat_session
date: 2024-12-10T10:30:00Z
participants:
  - human: paul
  - ai: claude
topic: Chat Session Storage Design
context_refs:
  - memory://basic-memory/20241210-chat-entity-design
key_decisions:
  - Store chats as first-class entities
  - Use memory:// URI scheme
summary: Designed schema for chat storage
---`
        },
        {
          `content`: `Example Relations:
- chat_session references design_proposal
- chat_session implements feature
- chat_session discusses concept
- chat_session continues_from previous_chat`
        },
        {
          `content`: `Auto-generation approach:
1. At end of chat, Claude summarizes key points
2. Creates chat entity with metadata
3. Adds relations to referenced entities
4. Updates any entities modified during chat`
        },
        {
          `content`: `Integration points:
- memory:// URI scheme for references
- Relations to track context chain
- File format matches entity schema
- Automatic metadata generation`
        }
      ]
    }
  ]
} 
```

```
{
  `entities`: [
    {
      `name`: `Chat_Session_Workflow`,
      `entityType`: `process`,
      `observations`: [
        {
          `content`: `Start of chat:
- Load any referenced context via memory:// URIs
- Initialize new chat session metadata
- Track entities being discussed/modified`
        },
        {
          `content`: `During chat:
- Update references as new entities are mentioned
- Track key decisions and changes
- Note any new relations discovered`
        },
        {
          `content`: `End of chat:
- Generate summary and key points
- Create chat session entity
- Add relations to referenced entities
- Update any modified entities`
        },
        {
          `content`: `Future chat reference:
- Can reference previous chat via memory:// URI
- Loads relevant context and decisions
- Creates continues_from relation automatically`
        }
      ]
    }
  ]
}
```

Key aspects of this design:

1. Chat Session as Entity

- Clear metadata (participants, date, topic)
- Explicit references to other entities via memory:// URIs
- Captures key decisions and summary
- Uses frontmatter for clean file format

2. Rich Relations

- Can track chat-to-chat continuity
- Links to entities discussed/modified
- Captures purpose (discusses, implements, etc.)
- Maintains context chain

3. Automated Workflow

- I could generate metadata during chat
- Create summary and relations at end
- Update any modified entities
- Makes context loading explicit

4. Integration

- memory:// URI scheme fits naturally
- File format matches our entity pattern
- Two-way links between chats and entities
- Clear context persistence model

The nice thing about this design is that it makes chat sessions "first-class citizens" in our knowledge graph while
keeping everything in human-readable markdown files.

Would you like me to:

1. Sketch out what this chat would look like as an entity?
2. Detail the MCP tool changes needed?
3. Mock up the file format more precisely?
4. Something else?
