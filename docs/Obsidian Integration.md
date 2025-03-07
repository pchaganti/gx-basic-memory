---
title: Obsidian Integration
type: note
permalink: docs/obsidian-integration
---

# Obsidian Integration

Basic Memory integrates seamlessly with [Obsidian](https://obsidian.md), providing powerful visualization and navigation capabilities for your knowledge graph.

## Setup

### Creating an Obsidian Vault

1. Download and install [Obsidian](https://obsidian.md)
2. Create a new vault
3. Point it to your Basic Memory directory (~/basic-memory by default)
4. Enable core plugins like Graph View, Backlinks, and Tags

## Visualization Features

### Graph View

Obsidian's Graph View provides a visual representation of your knowledge network:

- Each document appears as a node
- Relations appear as connections between nodes
- Colors can be customized to distinguish types
- Filters let you focus on specific aspects
- Local graphs show connections for individual documents

### Backlinks

Obsidian automatically tracks references between documents:

- View all documents that reference the current one
- See the exact context of each reference
- Navigate easily through connections
- Track how concepts relate to each other

### Tag Explorer

Use tags to organize and filter content:

- View all tags in your knowledge base
- See how many documents use each tag
- Filter documents by tag combinations
- Create hierarchical tag structures

## Knowledge Elements

Basic Memory's knowledge format works natively with Obsidian:

### Wiki Links

```markdown
## Relations
- implements [[Search Design]]
- depends_on [[Database Schema]]
```

These display as clickable links in Obsidian and appear in the graph view.

### Observations with Tags

```markdown
## Observations
- [tech] Using SQLite #database
- [design] Local-first #architecture
```

Tags become searchable and filterable in Obsidian's tag pane.

### Frontmatter

```yaml
---
title: Document Title
type: note
tags: [search, design]
---
```

Frontmatter provides metadata for Obsidian to use in search and filtering.

## Canvas Integration

Basic Memory can create [Obsidian Canvas](https://obsidian.md/canvas) files:

1. Ask Claude to create a visualization:
   ```
   You: "Create a canvas showing the structure of our project components."
   ```

2. Claude generates a .canvas file in your knowledge base

3. Open the file in Obsidian to view and edit the visual representation

4. Canvas files maintain references to your documents

## Recommended Plugins

These Obsidian plugins work especially well with Basic Memory:

- **Dataview**: Query your knowledge base programmatically
- **Kanban**: Organize tasks from knowledge files
- **Calendar**: View and navigate temporal knowledge
- **Templates**: Create consistent knowledge structures

## Workflow Suggestions

### Daily Notes

```markdown
# 2024-01-21

## Progress
- Updated [[Search Design]]
- Fixed [[Bug Report 123]]

## Notes
- [idea] Better indexing #enhancement
- [todo] Update docs #documentation

## Links
- relates_to [[Current Sprint]]
- updates [[Project Status]]
```

### Project Tracking

```markdown
# Current Sprint

## Tasks
- [ ] Update [[Search]]
- [ ] Fix [[Auth Bug]]

## Tags
#sprint #planning #current
```

## Relations
- enhances [[Introduction to Basic Memory]] (Overview of system)
- relates_to [[Canvas]] (Visual knowledge mapping)
- complements [[User Guide]] (Using Basic Memory)