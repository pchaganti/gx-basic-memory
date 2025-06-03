# /project:lint-fix - Comprehensive Code Quality Fix

Run comprehensive linting and auto-fix code quality issues across the codebase.

## Usage
```
/project:lint-fix
```

## Implementation

You are an expert code quality engineer for the Basic Memory project. When the user runs `/project:lint-fix`, execute the following steps:

### Step 1: Pre-flight Check
1. **Verify Clean Working Directory**
   ```bash
   git status --porcelain
   ```
   - Check for uncommitted changes
   - Warn if working directory is not clean
   - Suggest stashing changes if needed

### Step 2: Import Organization
1. **Fix Import Order and Cleanup**
   ```bash
   uv run ruff check --select I --fix .
   ```
   - Sort imports by category (standard, third-party, local)
   - Remove unused imports
   - Fix import spacing and organization

### Step 3: Code Formatting
1. **Apply Consistent Formatting**
   ```bash
   uv run ruff format .
   ```
   - Format code according to project style
   - Fix line length issues (100 chars max)
   - Standardize quotes and spacing

### Step 4: Linting with Auto-fix
1. **Fix Linting Issues**
   ```bash
   uv run ruff check --fix .
   ```
   - Auto-fix safe linting issues
   - Report any remaining manual fixes needed
   - Focus on code quality and best practices

### Step 5: Type Checking
1. **Validate Type Annotations**
   ```bash
   uv run pyright
   ```
   - Check for type errors
   - Report any missing type annotations
   - Validate type compatibility

### Step 6: Report Generation
Generate comprehensive quality report:

```
🔧 Code Quality Fix Report

✅ FIXES APPLIED:
├── Import organization: 12 files updated
├── Code formatting: 8 files reformatted  
├── Auto-fixable lint issues: 23 issues resolved
└── Total files processed: 156

⚠️  MANUAL ATTENTION NEEDED:
├── Type annotations missing in entity_service.py:45
├── Complex function needs refactoring in sync_service.py:123
└── Unused variable in test_utils.py:67

🎯 QUALITY SCORE: 96.2% (excellent)

📁 Run `git diff` to review all changes
```

## Error Handling

### Common Issues
- **Merge Conflicts**: Provide resolution guidance
- **Syntax Errors**: Point to specific files and lines
- **Type Errors**: Suggest specific fixes
- **Import Errors**: Check for missing dependencies

### Recovery Steps
- If auto-fixes introduce issues, provide rollback instructions
- If type checking fails, suggest incremental fixes
- If tests break, provide debugging guidance

## Quality Gates

### Must Pass
- [ ] All auto-fixable lint issues resolved
- [ ] Code formatting consistent
- [ ] No syntax errors
- [ ] Import organization clean

### Should Pass (Warnings)
- [ ] No type checking errors
- [ ] No complex function warnings
- [ ] No unused variables/imports
- [ ] Consistent naming conventions

## Output Examples

### Successful Fix
```
🎉 CODE QUALITY IMPROVED!

✅ All auto-fixes applied successfully
📏 Code formatting: 100% compliant
🔍 Linting: No issues found
🏷️  Type checking: All passed

Ready for commit! Use:
git add -A && git commit -m "style: fix code quality issues"
```

### Issues Requiring Attention
```
⚠️  PARTIAL SUCCESS - MANUAL FIXES NEEDED

✅ Auto-fixes applied: 45 issues
❌ Manual fixes needed: 3 issues

Priority fixes:
1. Fix type annotation in services/entity_service.py:142
2. Simplify complex function in sync/sync_service.py:67
3. Remove unused import in tests/conftest.py:12

Run these commands:
# Fix specific file
uv run pyright src/basic_memory/services/entity_service.py
```

## Context
- Uses ruff for fast Python linting and formatting
- Uses pyright for type checking
- Follows project code style guidelines (100 char line length)
- Maintains backward compatibility
- Integrates with existing pre-commit hooks