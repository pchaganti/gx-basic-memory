# /beta - Create Beta Release

Create a new beta release for the current version with automated quality checks and tagging.

## Usage
```
/beta [version]
```

**Parameters:**
- `version` (optional): Beta version like `v0.13.0b4`. If not provided, auto-increments from latest beta tag.

## Implementation

You are an expert release manager for the Basic Memory project. When the user runs `/beta`, execute the following steps:

### Step 1: Pre-flight Checks
1. Check current git status for uncommitted changes
2. Verify we're on the `main` branch
3. Get the latest beta tag to determine next version if not provided

### Step 2: Quality Assurance
1. Run `make check` to ensure code quality
2. If any checks fail, report issues and stop
3. Run `make update-deps` to ensure latest dependencies
4. Commit any dependency updates with proper message

### Step 3: Version Determination
If version not provided:
1. Get latest git tags with `git tag -l "v*b*" --sort=-version:refname | head -1`
2. Auto-increment beta number (e.g., `v0.13.0b2` → `v0.13.0b3`)
3. Confirm version with user before proceeding

### Step 4: Release Creation
1. Commit any remaining changes
2. Push to main: `git push origin main`
3. Create tag: `git tag {version}`
4. Push tag: `git push origin {version}`

### Step 5: Monitor Release
1. Check GitHub Actions workflow starts successfully
2. Provide installation instructions for beta
3. Report status and next steps

## Error Handling
- If quality checks fail, provide specific fix instructions
- If git operations fail, provide manual recovery steps  
- If GitHub Actions fail, provide debugging guidance

## Success Output
```
✅ Beta Release v0.13.0b4 Created Successfully!

🏷️  Tag: v0.13.0b4
🚀 GitHub Actions: Running
📦 PyPI: Will be available in ~5 minutes

Install with:
uv tool upgrade basic-memory --prerelease=allow

Monitor release: https://github.com/basicmachines-co/basic-memory/actions
```

## Context
- Use the existing Makefile targets (`make check`, `make update-deps`)
- Follow semantic versioning for beta releases
- Maintain release notes in CHANGELOG.md
- Use conventional commit messages
- Leverage uv-dynamic-versioning for version management