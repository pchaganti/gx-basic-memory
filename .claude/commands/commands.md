# Basic Memory Custom Commands

This directory contains custom Claude Code slash commands for the Basic Memory project.

## Available Commands

### Release Management (`/project:release:*`)
- `/project:release:beta` - Create beta releases with automated quality checks
- `/project:release:release` - Create stable releases with comprehensive validation  
- `/project:release:release-check` - Pre-flight validation without making changes
- `/project:release:changelog` - Generate changelog entries from commits

### Development (`/project:*`)
- `/project:test-coverage` - Run tests with detailed coverage analysis
- `/project:test-live` - Live testing suite using real Basic Memory installation
- `/project:lint-fix` - Run comprehensive linting with auto-fix
- `/project:check-health` - Comprehensive project health assessment

## Command Structure

Commands are organized by functionality:
```
.claude/commands/
├── release/          # Release management commands
│   ├── beta.md       # /project:release:beta
│   ├── release.md    # /project:release:release
│   ├── release-check.md # /project:release:release-check
│   └── changelog.md  # /project:release:changelog
├── test-coverage.md  # /project:test-coverage
├── test-live.md      # /project:test-live
├── lint-fix.md       # /project:lint-fix
├── check-health.md   # /project:check-health
└── commands.md       # This overview file
```

## Usage

Commands are invoked using the `/project:` prefix:
- `/project:release:beta v0.13.0b4`
- `/project:test-coverage mcp`
- `/project:test-live core`
- `/project:release:release-check`
- `/project:check-health`

## Implementation

Each command is implemented as a Markdown file containing structured prompts that:
1. Validate preconditions
2. Execute steps in the correct order
3. Handle errors gracefully  
4. Provide clear status updates
5. Return actionable results

## Tooling Integration

Commands leverage existing project tooling:
- `make check` - Quality checks
- `make test` - Test suite
- `make update-deps` - Dependency updates  
- `uv` - Package management
- `git` - Version control
- GitHub Actions - CI/CD pipeline