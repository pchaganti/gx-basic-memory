"""Script to migrate entity files into type-based folders."""
import re
import asyncio
from pathlib import Path

from basic_memory.models import Entity

async def migrate_files(entities_path: Path):
    """Move entity files into type-based directories."""
    
    # Get all markdown files
    files = list(entities_path.glob("*.md"))
    print(f"Found {len(files)} markdown files")
    
    # Track progress
    moved = []
    errors = []
    
    for file in files:
        try:
            # Read file
            content = file.read_text()
            
            # Extract type using regex
            type_match = re.search(r'^type:\s*(.+?)$', content, re.MULTILINE)
            if not type_match:
                errors.append((file, "No type found"))
                continue
                
            entity_type = type_match.group(1).strip()
            
            # Create type directory
            type_dir = entities_path / entity_type
            type_dir.mkdir(exist_ok=True)
            
            # Move the file
            new_path = type_dir / file.name
            file.rename(new_path)
            
            moved.append((file, new_path))
            print(f"Moved {file.name} to {entity_type}/")
            
        except Exception as e:
            errors.append((file, str(e)))
            print(f"Error processing {file}: {e}")
    
    # Print summary
    print("\nMigration complete!")
    print(f"Successfully moved: {len(moved)}")
    if errors:
        print("\nErrors:")
        for file, error in errors:
            print(f"  {file.name}: {error}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python migrate_to_folders.py <entities_path>")
        sys.exit(1)
        
    entities_path = Path(sys.argv[1])
    if not entities_path.exists():
        print(f"Entities directory not found: {entities_path}")
        sys.exit(1)
        
    asyncio.run(migrate_files(entities_path))
