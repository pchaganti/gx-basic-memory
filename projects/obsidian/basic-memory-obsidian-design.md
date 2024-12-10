# Basic Memory Obsidian Integration Design

## Why Basic Memory + Obsidian Integration is a Game-Changer

Imagine your AI conversations automatically organizing themselves into a beautiful, navigable knowledge base. That's what Basic Memory + Obsidian delivers.

### What It Does
- Your AI interactions create structured markdown files
- Obsidian automatically turns these into visual knowledge graphs
- Auto-generated indexes give you multiple ways to explore
- Everything stays local and human-readable on your machine

### Why It's Different
- No more lost context between AI chats
- See connections you wouldn't otherwise notice
- Navigate your knowledge visually
- Keep working in familiar Obsidian interface
- AI becomes a natural part of your thought process

### Perfect For
- Researchers using AI for discovery
- Developers managing complex projects
- Writers organizing ideas and drafts
- Knowledge workers synthesizing information
- Anyone who wants to think better with AI

### The Magic
Basic Memory provides the structure and AI integration. Obsidian provides the visualization and navigation. Together, they create a system that's greater than the sum of its parts - a truly augmented intelligence platform that grows with you.

Best part? It builds on tools you might already use, extending them naturally rather than replacing them. This isn't just another AI tool - it's a way to make your existing knowledge management system AI-native.

## Overview

Basic Memory will adopt Obsidian-compatible markdown formatting to enable seamless integration with Obsidian's powerful knowledge management features. This leverages Obsidian's existing user base and visualization capabilities while maintaining Basic Memory's rigorous knowledge graph structure.

## File Format

### Entity Files
```markdown
---
type: <entity_type>
created: <ISO timestamp>
updated: <ISO timestamp>
description: Short description of entity purpose
tags: [<entity_type>, <category>, ...]
---

# Entity Name

## Description
Detailed entity description

## Observations
- First observation
- Second observation
- etc...

## Relations
- [[RelatedEntity]] implements
- [[AnotherEntity]] depends_on
- [[ThirdEntity]] relates_to

## References
- Source links, citations, etc.
```

### Index Files

#### Entity Type Index
```markdown
---
type: index
index_type: entity_type
entity_type: technical_component
auto_generated: true
updated: <ISO timestamp>
---

# Technical Components

## Active Components
- [[Component1]] - Short description
- [[Component2]] - Short description

## In Development
- [[PlannedComponent]] - Development status

## Recently Updated
- [[UpdatedComponent]] - Change summary
```

#### Timeline Index
```markdown
---
type: index
index_type: timeline
period: weekly
auto_generated: true
updated: <ISO timestamp>
---

# Weekly Development Log

## Week of 2024-12-10
### New Components
- [[NewComponent]] - Added component for X
### Updates
- [[ExistingComponent]] - Improved functionality Y
### Decisions
- [[DecisionRecord]] - Chose approach Z
```

#### Project Status Index
```markdown
---
type: index
index_type: status
auto_generated: true
updated: <ISO timestamp>
---

# Project Status

## Active Development
- [[CurrentFeature]] - Implementation status
- [[PlannedFeature]] - Next in queue

## Recent Decisions
- [[Decision1]] - Impact and context
- [[Decision2]] - Rationale

## Known Issues
- [[Issue1]] - Status and plan
```

## Implementation Approach

### 1. File Generation
- Update MemoryService to write Obsidian-compatible markdown
- Add frontmatter support to file operations
- Implement wiki-link format for relations
- Support Obsidian tags in frontmatter

### 2. Index Generation Service
```python
class IndexGenerationService:
    def __init__(self, memory_service, file_service):
        self.memory_service = memory_service
        self.file_service = file_service
        self.index_configs = self.load_index_configs()
    
    async def update_indexes(self, trigger_entity=None):
        """Update affected indexes when entities change"""
        for config in self.index_configs:
            if self.should_update_index(config, trigger_entity):
                await self.generate_index(config)
    
    async def generate_index(self, config):
        """Generate specific index based on config"""
        entities = await self.query_relevant_entities(config)
        content = self.format_index_content(config, entities)
        await self.file_service.write_index(config.name, content)
```

### 3. Update Triggers
- Entity creation/modification
- Scheduled updates (daily/weekly)
- Manual refresh command
- Bulk updates after imports

### 4. Integration Points
- File system monitoring for external edits
- Obsidian URI scheme support
- Plugin hooks for future extensions
- Graph data export

## User Experience

### Setup
1. User points Obsidian vault to Basic Memory entity directory
2. Basic Memory detects Obsidian usage, enables compatible features
3. Index files are generated automatically
4. Graph view becomes available immediately

### Regular Usage
1. View knowledge graph in Obsidian
2. Navigate via auto-generated indexes
3. Edit files directly in Obsidian
4. Basic Memory maintains consistency
5. AI interactions continue updating graph

### Benefits
1. Leverage existing Obsidian skills
2. Multiple views of knowledge
3. Rich visualization
4. Local-first architecture
5. Large ecosystem of plugins

## Next Steps

1. Implementation Priorities
- Update file format
- Create index generation service
- Add Obsidian format detection
- Implement update triggers

2. Future Enhancements
- Custom index templates
- Plugin development
- Enhanced graph visualizations
- Collaborative features

## Market Opportunity

1. Target Audience
- Existing Obsidian users
- AI power users
- Knowledge workers
- Researchers and writers

2. Value Proposition
- Enhanced AI interaction
- Automated organization
- Structured knowledge capture
- Familiar interface

3. Distribution
- Direct to Obsidian community
- AI tooling channels
- Knowledge management space


# Basic Memory Obsidian Integration Implementation Plan

## Phase 1: File Format Updates

### New File Format
```markdown
---
type: technical_component
created: 2024-12-10T15:30:00Z
updated: 2024-12-10T15:30:00Z
description: Core service handling entity lifecycle and persistence
tags: [technical, implementation, core]
---

# EntityService

## Description
Manages entity lifecycle including creation, updates, and deletion while maintaining consistency between filesystem and database.

## Observations
- Implements filesystem-as-source-of-truth pattern
- Handles atomic file operations
- Maintains SQLite index
- Coordinates with other services

## Relations
- [[FileIOService]] uses
- [[ObservationService]] coordinates_with
- [[DatabaseService]] maintains_index_in

## References
- Link to relevant specs/docs
```

### Implementation Tasks
1. Update MemoryService
```python
class MemoryService:
    async def write_entity_file(self, entity):
        """Generate Obsidian-compatible markdown"""
        frontmatter = {
            "type": entity.entity_type,
            "created": entity.created_at,
            "updated": entity.updated_at,
            "description": entity.description,
            "tags": [entity.entity_type, *self.generate_tags(entity)]
        }
        
        content = f"""# {entity.name}

## Description
{entity.description}

## Observations
{self.format_observations(entity.observations)}

## Relations
{self.format_relations_as_wikilinks(entity.relations)}
"""
        return self.write_with_frontmatter(frontmatter, content)
```

2. Add Frontmatter Support
```python
def write_with_frontmatter(self, frontmatter: dict, content: str) -> str:
    """Combine frontmatter and content in Obsidian format"""
    yaml_fm = yaml.dump(frontmatter, sort_keys=False)
    return f"---\n{yaml_fm}---\n\n{content}"
```

3. Wiki-Link Generation
```python
def format_relations_as_wikilinks(self, relations: List[Relation]) -> str:
    """Convert relations to Obsidian wiki-link format"""
    return "\n".join(
        f"- [[{relation.to_entity.name}]] {relation.relation_type}"
        for relation in relations
    )
```

## Phase 2: Index Generation

### Index Types and Configurations
```python
INDEX_CONFIGS = {
    "entity_type_index": {
        "template": "entity_type_index.md",
        "group_by": "entity_type",
        "sort_by": "updated_at",
        "update_trigger": "entity_change"
    },
    "timeline_index": {
        "template": "timeline_index.md",
        "group_by": "week",
        "sort_by": "created_at",
        "update_trigger": "daily"
    },
    "status_index": {
        "template": "status_index.md",
        "group_by": "status",
        "sort_by": "priority",
        "update_trigger": "entity_change"
    }
}
```

### IndexGenerationService Implementation
```python
class IndexGenerationService:
    def __init__(self, memory_service: MemoryService):
        self.memory_service = memory_service
        self.index_configs = INDEX_CONFIGS
        
    async def update_indexes(self, trigger: str = None):
        """Update all indexes or those matching trigger"""
        for name, config in self.index_configs.items():
            if not trigger or config["update_trigger"] == trigger:
                await self.generate_index(name, config)
                
    async def generate_index(self, name: str, config: dict):
        """Generate single index based on configuration"""
        entities = await self.get_entities_for_index(config)
        grouped = self.group_entities(entities, config["group_by"])
        content = self.apply_template(config["template"], grouped)
        await self.memory_service.write_index_file(name, content)
```

## Phase 3: Testing Strategy

### Test Cases
1. File Format Tests
```python
async def test_entity_file_generation():
    """Test Obsidian-compatible file generation"""
    entity = create_test_entity()
    content = await memory_service.write_entity_file(entity)
    
    assert "---" in content  # Has frontmatter
    assert "[[" in content   # Has wiki-links
    assert content.count("##") >= 3  # Has sections
```

2. Index Generation Tests
```python
async def test_index_generation():
    """Test index file creation and updates"""
    await index_service.generate_index("entity_type_index")
    
    content = await read_index_file("entity_type_index")
    assert "# Technical Components" in content
    assert "[[" in content  # Has entity links
```

3. Integration Tests
```python
async def test_obsidian_compatibility():
    """Test full Obsidian compatibility"""
    # Create test vault
    # Generate entities and indexes
    # Verify Obsidian can parse and display
```

## Phase 4: Launch Preparation

### Documentation Template
```markdown
# Basic Memory Obsidian Integration

## Setup
1. Install Basic Memory
2. Create/Open Obsidian vault
3. Point to Basic Memory entity directory
4. Configure index generation

## Features
- Automatic knowledge graph visualization
- Generated index views
- Wiki-link navigation
- AI integration via Basic Memory

## Usage Examples
1. Creating new entities
2. Navigating via indexes
3. Using graph view
4. AI interaction workflow
```

### Launch Checklist
- [ ] All tests passing
- [ ] Example vault created
- [ ] Setup documentation complete
- [ ] Demo video recorded
- [ ] Launch announcement drafted
- [ ] Initial indexes refined
- [ ] User feedback incorporated

## Implementation Schedule

1. Week 1: File Format
- Implement new format
- Add frontmatter support
- Test basic Obsidian compatibility

2. Week 2: Index Generation
- Build IndexGenerationService
- Create initial templates
- Test update triggers

3. Week 3: Testing & Refinement
- Comprehensive testing
- User testing with example vault
- Refinement based on feedback

4. Week 4: Launch Prep
- Documentation
- Examples
- Demo materials
- Launch announcement