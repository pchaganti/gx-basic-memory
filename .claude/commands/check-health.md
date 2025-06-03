# /project:check-health - Project Health Assessment

Comprehensive health check of the Basic Memory project including code quality, test coverage, dependencies, and documentation.

## Usage
```
/project:check-health
```

## Implementation

You are an expert DevOps engineer for the Basic Memory project. When the user runs `/project:check-health`, execute the following comprehensive assessment:

### Step 1: Git Repository Health
1. **Repository Status**
   ```bash
   git status
   git log --oneline -5
   git branch -vv
   ```
   - Check working directory status
   - Verify branch alignment with remote
   - Check recent commit activity

2. **Branch Analysis**
   - Verify on main branch
   - Check if ahead/behind remote
   - Identify any untracked files

### Step 2: Code Quality Assessment
1. **Linting and Formatting**
   ```bash
   uv run ruff check .
   uv run pyright
   ```
   - Count linting issues by severity
   - Check type annotation coverage
   - Verify code formatting compliance

2. **Test Suite Health**
   ```bash
   uv run pytest --collect-only -q
   uv run pytest --co -q | wc -l
   ```
   - Count total tests
   - Check for test discovery issues
   - Verify test structure integrity

### Step 3: Dependency Analysis
1. **Dependency Health**
   ```bash
   uv tree
   uv lock --dry-run
   ```
   - Check for dependency conflicts
   - Identify outdated dependencies
   - Verify lock file consistency

2. **Security Scan**
   ```bash
   uv run pip-audit --desc
   ```
   - Scan for known vulnerabilities
   - Check dependency licenses
   - Identify security advisories

### Step 4: Performance Metrics
1. **Test Performance**
   ```bash
   uv run pytest --durations=10
   ```
   - Identify slowest tests
   - Check overall test execution time
   - Monitor test suite growth

2. **Build Performance**
   ```bash
   time uv run python -c "import basic_memory"
   ```
   - Check import time
   - Validate package installation
   - Monitor startup performance

### Step 5: Documentation Health
1. **Documentation Coverage**
   - Check README.md currency
   - Verify CLI documentation
   - Validate MCP tool documentation
   - Check changelog completeness

2. **API Documentation**
   - Verify docstring coverage
   - Check type annotation completeness
   - Validate example code

### Step 6: Project Metrics
1. **Code Statistics**
   ```bash
   find src -name "*.py" | xargs wc -l
   find tests -name "*.py" | xargs wc -l
   ```
   - Lines of code trends
   - Test-to-code ratio
   - File organization metrics

## Health Report Format

Generate comprehensive health dashboard:

```
🏥 Basic Memory Project Health Report

📊 OVERALL HEALTH: 🟢 EXCELLENT (92/100)

🗂️  GIT REPOSITORY
✅ Clean working directory
✅ Up to date with origin/main
✅ Recent commit activity (5 commits this week)

🔍 CODE QUALITY  
✅ Linting: 0 errors, 2 warnings
✅ Type checking: 100% coverage
✅ Formatting: Compliant
⚠️  Complex functions: 3 need refactoring

🧪 TEST SUITE
✅ Total tests: 744 
✅ Test discovery: All tests found
✅ Coverage: 98.2%
⚡ Performance: 45.2s (good)

📦 DEPENDENCIES
✅ Dependencies: Up to date
✅ Security: No vulnerabilities
✅ Conflicts: None detected
⚠️  Outdated: 2 minor updates available

📖 DOCUMENTATION
✅ README: Current
✅ API docs: 95% coverage
⚠️  CLI reference: Needs update
✅ Changelog: Complete

📈 METRICS
├── Source code: 15,432 lines
├── Test code: 8,967 lines  
├── Test ratio: 58% (excellent)
└── Complexity: Low (maintainable)

🎯 RECOMMENDATIONS:
1. Update CLI documentation
2. Refactor 3 complex functions
3. Update minor dependencies
4. Consider splitting large test files

🏆 PROJECT STATUS: Ready for v0.13.0 release!
```

## Health Scoring

### Excellent (90-100)
- All quality gates pass
- High test coverage (>95%)
- No security issues
- Documentation current

### Good (75-89)
- Minor issues present
- Good test coverage (>90%)
- No critical security issues
- Most documentation current

### Needs Attention (60-74)
- Several quality issues
- Adequate test coverage (>80%)
- Minor security concerns
- Documentation gaps

### Critical (<60)
- Major quality problems
- Low test coverage (<80%)
- Security vulnerabilities
- Significant documentation issues

## Context
- Provides comprehensive project overview
- Identifies potential issues before they become problems
- Tracks project health trends over time
- Helps prioritize maintenance tasks
- Supports release readiness decisions