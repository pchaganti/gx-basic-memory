# Basic Memory Tasks

## Current Focus

### Observation Management
Implement update/remove functionality for observations with a focus on maintainability and consistency with our "filesystem is source of truth" principle.

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