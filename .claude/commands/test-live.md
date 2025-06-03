# /project:test-live - Live Basic Memory Testing Suite

Execute comprehensive real-world testing of Basic Memory using the installed version, following the methodology in TESTING.md. All test results are recorded as notes in a dedicated test project.

## Usage
```
/project:test-live [phase]
```

**Parameters:**
- `phase` (optional): Specific test phase to run (`core`, `features`, `edge`, `workflows`, `stress`, or `all`)

## Implementation

You are an expert QA engineer conducting live testing of Basic Memory. When the user runs `/project:test-live`, execute comprehensive testing following the TESTING.md methodology:

### Pre-Test Setup

1. **Environment Verification**
   - Verify basic-memory is installed and accessible via MCP
   - Check version and confirm it's the expected release
   - Test MCP connection and tool availability

2. **Test Project Creation**
   ```
   Create project: "basic-memory-testing-[timestamp]"
   Location: ~/basic-memory-testing-[timestamp]
   Purpose: Record all test observations and results
   ```

3. **Baseline Documentation**
   Create initial test session note with:
   - Test environment details
   - Version being tested
   - Test objectives and scope
   - Start timestamp

### Phase 1: Core Functionality Validation

Test all fundamental MCP tools systematically:

**write_note Tests:**
- Basic note creation with various content types
- Frontmatter handling (tags, custom fields)
- Special characters in titles and content
- Unicode and emoji support
- Empty notes and minimal content

**read_note Tests:**
- Read by title, permalink, memory:// URLs
- Non-existent notes (error handling)
- Notes with complex formatting
- Performance with large notes

**search_notes Tests:**
- Simple text queries
- Tag-based searches 
- Boolean operators and complex queries
- Empty/no results scenarios
- Performance with growing knowledge base

**Recent Activity Tests:**
- Various timeframes ("today", "1 week", "1d")
- Type filtering (if available)
- Empty project scenarios
- Performance with many recent changes

**Context Building Tests:**
- Different depth levels (1, 2, 3+)
- Various timeframes
- Relation traversal accuracy
- Performance with complex graphs

### Phase 2: v0.13.0 Feature Deep Dive

**Project Management:**
- Create multiple projects dynamically
- Switch between projects mid-conversation  
- Cross-project operations
- Project discovery and status
- Default project behavior
- Invalid project handling

**Advanced Note Editing:**
- `edit_note` with append operations
- Prepend operations
- Find/replace with validation
- Section replacement under headers
- Error scenarios (invalid operations)
- Frontmatter preservation

**File Management:**
- `move_note` within same project
- Move between projects
- Automatic folder creation
- Special characters in paths
- Database consistency validation
- Search index updates after moves

### Phase 3: Edge Case Exploration

**Boundary Testing:**
- Very long titles and content (stress limits)
- Empty projects and notes
- Unicode, emojis, special symbols
- Deeply nested folder structures
- Circular relations and self-references
- Maximum relation depths

**Error Scenarios:**
- Invalid memory:// URLs
- Missing files referenced in database
- Invalid project names and paths
- Malformed note structures
- Concurrent operation conflicts

**Performance Testing:**
- Create 100+ notes rapidly
- Complex search queries
- Deep relation chains (5+ levels)
- Rapid successive operations
- Memory usage monitoring

### Phase 4: Real-World Workflow Scenarios

**Meeting Notes Pipeline:**
1. Create meeting notes with action items
2. Extract action items using edit_note
3. Build relations to project documents
4. Update progress incrementally
5. Search and track completion

**Research Knowledge Building:**
1. Create research topic hierarchy
2. Build complex relation networks
3. Add incremental findings over time
4. Search for connections and patterns
5. Reorganize as knowledge evolves

**Multi-Project Workflow:**
1. Technical documentation project
2. Personal recipe collection project
3. Learning/course notes project
4. Switch contexts during conversation
5. Cross-reference related concepts

**Content Evolution:**
1. Start with basic notes
2. Enhance with relations and observations
3. Reorganize file structure using moves
4. Update content with edit operations
5. Validate knowledge graph integrity

### Phase 5: Creative Stress Testing

**Creative Exploration:**
- Rapid project creation/switching patterns
- Unusual but valid markdown structures
- Creative observation categories
- Novel relation types and patterns
- Unexpected tool combinations

**Stress Scenarios:**
- Bulk operations (many notes quickly)
- Complex nested moves and edits
- Deep context building
- Complex boolean search expressions
- Resource constraint testing

## Test Observation Format

Record ALL observations immediately as Basic Memory notes:

```markdown
---
title: Test Session [Phase] YYYY-MM-DD HH:MM
tags: [testing, v0.13.0, live-testing, [phase]]
permalink: test-session-[phase]-[timestamp]
---

# Test Session [Phase] - [Date/Time]

## Environment
- Basic Memory version: [version]
- MCP connection: [status]
- Test project: [name]
- Phase focus: [description]

## Test Results

### ✅ Successful Operations
- [timestamp] write_note: Created note with emoji title 📝 #functionality
- [timestamp] search_notes: Boolean query returned 23 results in 0.4s #performance  
- [timestamp] edit_note: Append operation preserved frontmatter #reliability

### ⚠️ Issues Discovered
- [timestamp] move_note: Slow with deep folder paths (2.1s) #performance
- [timestamp] search_notes: Unicode query returned unexpected results #bug
- [timestamp] project switch: Context lost for memory:// URLs #issue

### 🚀 Enhancements Identified
- edit_note could benefit from preview mode #ux-improvement
- search_notes needs fuzzy matching for typos #feature-idea
- move_note could auto-suggest folder creation #usability

### 📊 Performance Metrics
- Average write_note time: 0.3s
- Search with 100+ notes: 0.6s
- Project switch overhead: 0.1s
- Memory usage: [observed levels]

## Relations
- tests [[Basic Memory v0.13.0]]
- part_of [[Live Testing Suite]]
- found_issues [[Bug Report: Unicode Search]]
- discovered [[Performance Optimization Opportunities]]
```

## Quality Assessment Areas

**User Experience & Usability:**
- Tool instruction clarity and examples
- Error message actionability
- Response time acceptability
- Tool consistency and discoverability
- Learning curve and intuitiveness

**System Behavior:**
- Context preservation across operations
- memory:// URL navigation reliability
- Multi-step workflow cohesion
- Edge case graceful handling
- Recovery from user errors

**Documentation Alignment:**
- Tool output clarity and helpfulness
- Behavior vs. documentation accuracy
- Example validity and usefulness
- Real-world vs. documented workflows

**Mental Model Validation:**
- Natural user expectation alignment
- Surprising behavior identification
- Mistake recovery ease
- Knowledge graph concept naturalness

**Performance & Reliability:**
- Operation completion times
- Consistency across sessions
- Scaling behavior with growth
- Unexpected slowness identification

## Error Documentation Protocol

For each error discovered:

1. **Immediate Recording**
   - Create dedicated error note
   - Include exact reproduction steps
   - Capture error messages verbatim
   - Note system state when error occurred

2. **Error Note Format**
   ```markdown
   ---
   title: Bug Report - [Short Description]
   tags: [bug, testing, v0.13.0, [severity]]
   ---
   
   # Bug Report: [Description]
   
   ## Reproduction Steps
   1. [Exact steps to reproduce]
   2. [Include all parameters used]
   3. [Note any special conditions]
   
   ## Expected Behavior
   [What should have happened]
   
   ## Actual Behavior  
   [What actually happened]
   
   ## Error Messages
   ```
   [Exact error text]
   ```
   
   ## Environment
   - Version: [version]
   - Project: [name]
   - Timestamp: [when]
   
   ## Severity
   - [ ] Critical (blocks major functionality)
   - [ ] High (impacts user experience)
   - [ ] Medium (workaround available)
   - [ ] Low (minor inconvenience)
   
   ## Relations
   - discovered_during [[Test Session [Phase]]]
   - affects [[Feature Name]]
   ```

## Success Metrics Tracking

**Quantitative Measures:**
- Test scenario completion rate
- Bug discovery count with severity
- Performance benchmark establishment
- Tool coverage completeness

**Qualitative Measures:**
- Conversation flow naturalness
- Knowledge graph quality
- User experience insights
- System reliability assessment

## Test Execution Flow

1. **Setup Phase** (5 minutes)
   - Verify environment and create test project
   - Record baseline system state
   - Establish performance benchmarks

2. **Core Testing** (15-20 minutes per phase)
   - Execute test scenarios systematically
   - Record observations immediately
   - Note timestamps for performance tracking
   - Explore variations when interesting behaviors occur

3. **Documentation** (5 minutes per phase)
   - Create phase summary note
   - Link related test observations
   - Update running issues list
   - Record enhancement ideas

4. **Analysis Phase** (10 minutes)
   - Review all observations across phases
   - Identify patterns and trends
   - Create comprehensive summary report
   - Generate development recommendations

## Expected Outcomes

**System Validation:**
- v0.13.0 feature verification in real usage
- Edge case discovery beyond unit tests
- Performance baseline establishment
- Bug identification with reproduction cases

**Knowledge Base Creation:**
- Comprehensive testing documentation
- Real usage examples for user guides
- Edge case scenarios for future testing
- Performance insights for optimization

**Development Insights:**
- Prioritized bug fix list
- Enhancement ideas from real usage
- Architecture validation results
- User experience improvement areas

## Post-Test Deliverables

1. **Test Summary Note**
   - Overall results and findings
   - Critical issues requiring immediate attention
   - Enhancement opportunities discovered
   - System readiness assessment

2. **Bug Report Collection**
   - All discovered issues with reproduction steps
   - Severity and impact assessments
   - Suggested fixes where applicable

3. **Performance Baseline**
   - Timing data for all operations
   - Scaling behavior observations
   - Resource usage patterns

4. **UX Improvement Recommendations**
   - Usability enhancement suggestions
   - Documentation improvement areas
   - Tool design optimization ideas

5. **Updated TESTING.md**
   - Incorporate new test scenarios discovered
   - Update based on real execution experience
   - Add performance benchmarks and targets

## Context
- Uses installed basic-memory version (not development)
- Tests complete MCP→API→DB→File stack
- Creates living documentation in Basic Memory itself
- Follows integration over isolation philosophy
- Focuses on real usage patterns over checklist validation
- Generates actionable insights for development team