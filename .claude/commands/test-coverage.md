# /test-coverage - Run Tests with Coverage Analysis

Execute test suite with comprehensive coverage reporting and analysis.

## Usage
```
/test-coverage [pattern]
```

**Parameters:**
- `pattern` (optional): Test pattern to run specific tests (e.g., `test_mcp`, `*integration*`)

## Implementation

You are an expert QA engineer for the Basic Memory project. When the user runs `/test-coverage`, execute the following steps:

### Step 1: Test Execution
1. **Run Tests with Coverage**
   ```bash
   # Full test suite
   uv run pytest --cov=basic_memory --cov-report=html --cov-report=term -v
   
   # Or with pattern if provided
   uv run pytest tests/*{pattern}* --cov=basic_memory --cov-report=html --cov-report=term -v
   ```

2. **Generate Coverage Reports**
   - Terminal summary with percentages
   - HTML report for detailed analysis
   - Identify files below coverage threshold

### Step 2: Coverage Analysis
1. **Summary Statistics**
   - Overall coverage percentage
   - Number of files with 100% coverage
   - Files below 95% threshold
   - Total lines covered/missed

2. **Detailed Breakdown**
   - Coverage by module/package
   - Identify untested code paths
   - Find missing edge case tests

### Step 3: Report Generation
Generate comprehensive coverage report:

```
🧪 Test Coverage Report

📊 OVERALL COVERAGE: 98.2% (target: 95%+)

✅ EXCELLENT COVERAGE (>95%):
├── basic_memory/mcp/: 99.1%
├── basic_memory/services/: 98.8%
├── basic_memory/repository/: 97.9%
└── basic_memory/api/: 96.2%

⚠️  NEEDS ATTENTION (<95%):
├── basic_memory/sync/: 94.1% (missing 12 lines)
└── basic_memory/importers/: 91.8% (missing 23 lines)

🎯 SPECIFIC GAPS:
├── sync_service.py:142-145 (error handling)
├── importer_base.py:67-70 (edge case)
└── file_utils.py:89 (exception path)

📁 HTML Report: htmlcov/index.html
🚀 Run `open htmlcov/index.html` to view detailed report
```

### Step 4: Actionable Recommendations
1. **Coverage Improvements**
   - Suggest specific tests to add
   - Identify edge cases to cover
   - Recommend integration tests

2. **Quality Insights**
   - Highlight well-tested modules
   - Point out testing patterns to follow
   - Suggest refactoring for testability

## Advanced Analysis

### Performance Metrics
- Test execution time by module
- Slowest tests identification
- Coverage collection overhead

### Integration Coverage
- MCP tool integration tests
- API endpoint coverage
- Database operation coverage
- File system operation coverage

## Output Examples

### Full Coverage Success
```
🎉 EXCELLENT COVERAGE!

📊 Coverage: 98.7% (744 tests passed)
✅ All modules above 95% threshold
🏆 23 files with 100% coverage
⚡ Tests completed in 45.2s

Ready for release! 🚀
```

### Coverage Issues Found
```
⚠️  COVERAGE GAPS DETECTED

📊 Coverage: 92.1% (below 95% target)
❌ 3 modules need attention
🔍 43 uncovered lines found

Priority fixes:
1. Add tests for error handling in sync_service.py
2. Cover edge cases in importer_base.py
3. Test exception paths in file_utils.py

Run specific tests:
uv run pytest tests/sync/ -v
```

## Context
- Uses pytest with coverage plugin
- Generates both terminal and HTML reports
- Focuses on actionable improvement suggestions
- Integrates with existing test infrastructure
- Helps maintain high code quality standards