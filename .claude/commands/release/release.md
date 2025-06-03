# /release - Create Stable Release

Create a stable release from the current main branch with comprehensive validation.

## Usage
```
/release <version>
```

**Parameters:**
- `version` (required): Release version like `v0.13.0`

## Implementation

You are an expert release manager for the Basic Memory project. When the user runs `/release`, execute the following steps:

### Step 1: Pre-flight Validation
1. Verify version format matches `v\d+\.\d+\.\d+` pattern
2. Check current git status for uncommitted changes  
3. Verify we're on the `main` branch
4. Confirm no existing tag with this version

### Step 2: Comprehensive Quality Checks
1. Run `make check` (lint, format, type-check, full test suite)
2. Verify test coverage meets minimum requirements (95%+)
3. Check that CHANGELOG.md contains entry for this version
4. Validate all high-priority issues are closed

### Step 3: Release Preparation
1. Update any version references if needed
2. Commit any final changes with message: `chore: prepare for ${version} release`
3. Push to main: `git push origin main`

### Step 4: Release Creation
1. Create annotated tag: `git tag -a ${version} -m "Release ${version}"`
2. Push tag: `git push origin ${version}`
3. Monitor GitHub Actions for release automation

### Step 5: Post-Release Validation
1. Verify GitHub release is created automatically
2. Check PyPI publication
3. Validate release assets
4. Test installation: `uv tool install basic-memory`

### Step 6: Documentation Update
1. Update any post-release documentation
2. Create follow-up tasks if needed

## Pre-conditions Check
Before starting, verify:
- [ ] All beta testing is complete
- [ ] Critical bugs are fixed
- [ ] Breaking changes are documented
- [ ] CHANGELOG.md is updated
- [ ] Version number follows semantic versioning

## Error Handling
- If any quality check fails, stop and provide fix instructions
- If changelog entry missing, prompt to create one
- If tests fail, provide debugging guidance
- If GitHub Actions fail, provide manual release steps

## Success Output
```
🎉 Stable Release v0.13.0 Created Successfully!

🏷️  Tag: v0.13.0
📋 GitHub Release: https://github.com/basicmachines-co/basic-memory/releases/tag/v0.13.0
📦 PyPI: https://pypi.org/project/basic-memory/0.13.0/
🚀 GitHub Actions: Completed

Install with:
uv tool install basic-memory

Users can now upgrade:
uv tool upgrade basic-memory
```

## Context
- This creates production releases used by end users
- Must pass all quality gates before proceeding
- Follows the release workflow documented in CLAUDE.md
- Uses uv-dynamic-versioning for automatic version management
- Triggers automated GitHub release with changelog