---
title: Canvas Visualizations
type: note
permalink: docs/canvas
tags:
- visualization
- mapping
- obsidian
---

# Canvas Visualizations

Basic Memory can create visual knowledge maps using Obsidian's Canvas feature. These visualizations help you understand relationships between concepts, map out processes, and visualize your knowledge structure.

## Creating Canvas Visualizations

Ask Claude to create a visualization by describing what you want to map:

```
You: "Create a canvas visualization of my project components and their relationships."

You: "Make a concept map showing the main themes from our discussion about climate change."

You: "Can you make a canvas diagram of the perfect pour over method?"
```

![[Canvas.png]]

## Types of Visualizations

Basic Memory can create several types of visual maps:

### Document Maps
Visualize connections between your notes and documents

### Concept Maps
Create visual representations of ideas and their relationships

### Process Diagrams
Map workflows, sequences, and procedures

### Thematic Analysis
Organize ideas around central themes

### Relationship Networks
Show how different entities relate to each other

## Visualization Sources

Claude can create visualizations based on:

### Documents in Your Knowledge Base
```
You: "Create a canvas showing the connections between my project planning documents"
```

### Conversation Content
```
You: "Make a canvas visualization of the main points we just discussed"
```

### Search Results
```
You: "Find all my notes about psychology and create a visual map of the concepts"
```

### Themes and Relationships
```
You: "Create a visual map showing how different philosophical schools relate to each other"
```

## Visualization Workflow

1. **Request a visualization** by describing what you want to see
2. **Claude creates the canvas file** in your Basic Memory directory
3. **Open the file in Obsidian** to view the visualization
4. **Refine the visualization** by asking Claude for adjustments:
   ```
   You: "Could you reorganize the canvas to group related components together?"
   
   You: "Please add more detail about the connection between these two concepts."
   ```

## Technical Details

Behind the scenes, Claude:

1. Creates a `.canvas` file in JSON format
2. Adds nodes for each concept or document
3. Creates edges to represent relationships
4. Sets positions for visual clarity
5. Includes any relevant metadata

The resulting file is fully compatible with Obsidian's Canvas feature and can be edited directly in Obsidian.

## Tips for Effective Visualizations

- **Be specific** about what you want to visualize
- **Specify the level of detail** you need
- **Mention the visualization type** you want (concept map, process flow, etc.)
- **Start simple** and ask for refinements
- **Provide context** about what documents or concepts to include

## Relations
- enhances [[Obsidian Integration]] (Using Basic Memory with Obsidian)
- visualizes [[Knowledge Format]] (The structure of your knowledge)
- complements [[User Guide]] (Ways to use Basic Memory)