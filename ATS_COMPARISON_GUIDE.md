# ATS-Level Lambda Comparison Guide

## Overview

The ATS (Application Test Suite) level comparison script performs **functional and behavioral comparisons** between two Lambda functions, going beyond simple code diffs. It analyzes configurations, dependencies, test results, performance characteristics, and event sources to provide a comprehensive application-level comparison.

## Key Features

### 1. **Configuration Analysis**
- Runtime versions and Python requirements
- Memory allocation and timeout settings
- Handler specifications
- Environment variables
- Lambda layers and architectures
- Tracing and storage configurations
- **Significance Levels**: CRITICAL, IMPORTANT, MINOR

### 2. **Dependencies Management**
- Package inventory and comparison
- Identification of unique dependencies
- Dependency count and size analysis
- Import analysis from code

### 3. **Performance Metrics**
- Estimated cold start times
- Memory efficiency scoring
- Code complexity analysis
- Dependency size impact
- Architecture optimization metrics

### 4. **Test Coverage**
- Execution of pytest suite
- Test pass/fail comparison
- Reliability metrics
- Test coverage summary

### 5. **Event Sources & Triggers**
- Supported trigger types (S3, API Gateway, DynamoDB, SQS, etc.)
- Identified through SAM templates and code analysis
- Compatibility matrix between functions

## Usage

### Basic Comparison
```bash
# Compare two functions and display report
python compare_lambda_functions_ats.py myTestFunction1 myTestFunction2

# Compare and save text report
python compare_lambda_functions_ats.py myTestFunction1 myTestFunction2 report.txt

# Also generates .json file automatically
```

### Windows Batch
```cmd
run.bat compare-ats myTestFunction1 myTestFunction2
```

## Real-World Scenarios

### Scenario 1: Upgrading Runtime
```bash
# Before upgrading Python 3.12 → 3.14
python compare_lambda_functions_ats.py current_func upgraded_func

# Output shows:
# 🔴 runtime (CRITICAL) ← Highlights the runtime change
# ⚡ Estimated cold start reduced by ~200ms
# ✅ All tests still passing
```

### Scenario 2: Analyzing Code Refactoring
```bash
# Compare original vs refactored version
python compare_lambda_functions_ats.py original_v1 refactored_v2

# Output shows:
# Configuration identical ✓
# Dependencies simplified (removed 3 packages)
# Code complexity reduced: 72.5 → 45.2
# Performance: 50ms faster cold start
# Test reliability: identical
```

### Scenario 3: Evaluating Alternative Implementations
```bash
# Compare two different approaches
python compare_lambda_functions_ats.py approach_sync approach_async

# Output shows:
# Memory difference: 256MB vs 512MB
# Different event sources: S3 vs SQS
# Cold start: 1500ms vs 2000ms (trade-off for async)
# Test reliability: both pass 100%
```

## JSON Output Structure

```json
{
  "timestamp": "2026-02-23T10:30:00",
  "function1": "myTestFunction1",
  "function2": "myTestFunction2",
  "configuration": {
    "function1": { ... },
    "function2": { ... },
    "differences": [
      {
        "field": "runtime",
        "function1": "python3.12",
        "function2": "python3.14",
        "significance": "CRITICAL"
      }
    ]
  },
  "dependencies": {
    "function1": { ... },
    "function2": { ... },
    "differences": {
      "only_in_function1": [...],
      "only_in_function2": [...],
      "common": [...],
      "total_difference": 3
    }
  },
  "metrics": {
    "function1": { ... },
    "function2": { ... },
    "comparison": { ... }
  },
  "tests": {
    "function1": [...],
    "function2": [...],
    "summary": { ... }
  },
  "event_sources": {
    "function1": [...],
    "function2": [...],
    "differences": [...]
  }
}
```

## Programmatic Usage

```python
from compare_lambda_functions_ats import ATSComparator

# Create comparator
comparator = ATSComparator('myTestFunction1', 'myTestFunction2')

# Get comparison data
comparison = comparator.compare()

# Generate reports
text_report = comparator.generate_report('report.txt')
comparator.generate_json_report('report.json')

# Access specific data
config_diffs = comparison['configuration']['differences']
deps = comparison['dependencies']['differences']
metrics = comparison['metrics']['comparison']
```

## Metrics Explained

### Cold Start Time
- Estimated time to initialize the Lambda
- Affected by: dependencies, memory allocation, runtime
- Lower is better
- Formula: `1000ms + (dep_count * 10) - (memory_bonus)`

### Code Complexity Score (0-100)
- Based on number of lines of code
- Quick indicator of maintainability
- Lower is better
- Formula: `min(100, lines / 10)`

### Memory Efficiency Ratio
- Ratio of function2 memory to function1 memory
- Ratio > 1.0 means function2 uses more memory
- Consider cold start vs memory trade-offs

### Test Reliability
- Pass rate percentage
- Higher is better for production functions
- Measured as: `(passed_tests / total_tests) * 100`

## Configuration Sources

The script analyzes:

1. **functions.config.yaml** - Main configuration file
2. **template.yml** - SAM template specifications
3. **lambda_function.py** - Code-based inference
4. **requirements.txt** - Dependencies
5. **pytest results** - Test execution output

## Troubleshooting

### No tests found
- Ensure pytest is installed: `pip install pytest`
- Tests must be in `tests/` directory
- Test files must match `test_*.py` pattern

### Configuration not detected
- Verify `functions.config.yaml` exists in workspace root
- Check that function name matches YAML configuration
- Verify `template.yml` is in function directory

### Package analysis incomplete
- Ensure `requirements.txt` exists in `src/` subdirectory
- Check file format (one package per line)
- Handle commented lines (starting with `#`)

## Integration with Existing Tools

### Combine with File-Level Comparison
```bash
# Get code differences
python compare_lambda_functions.py func1 func2

# Get functional differences
python compare_lambda_functions_ats.py func1 func2

# Compare results to understand impact
```

### Batch Processing
Create a configuration file (e.g., `ats_comparisons.yaml`):
```yaml
comparisons:
  - function1: myTestFunction1
    function2: myTestFunction2
    output: func1_vs_func2_ats.txt
  
  - function1: myTestFunction3
    function2: myTestFunction4
    output: func3_vs_func4_ats.txt
```

Then process with a loop:
```bash
for pair in $(cat ats_comparisons.yaml | grep 'function1:'); do
  # Parse and run comparisons
done
```

## Performance and Limitations

- **Execution Time**: 5-30 seconds per comparison (includes test execution)
- **Test Timeout**: 30 seconds per test file
- **Memory**: Minimal (< 100MB for typical functions)
- **API Calls**: None (all local analysis)

## Best Practices

1. **Before Production Deployment**
   - Run ATS comparison between current and new versions
   - Verify CRITICAL differences are intentional
   - Check test reliability hasn't decreased

2. **During Code Reviews**
   - Include ATS comparison report in PR comments
   - Highlight CRITICAL and IMPORTANT differences
   - Share JSON report for detailed analysis

3. **Documentation**
   - Save historical comparisons for audit trails
   - Use JSON reports for dashboards/analytics
   - Track performance improvements over time

4. **CI/CD Integration**
   - Run ATS comparison in pipeline before deployment
   - Fail build if critical differences detected
   - Archive reports as build artifacts

## Contributing

To extend the script with additional metrics:

1. Add new fields to relevant `@dataclass` (e.g., `FunctionMetrics`)
2. Implement calculation method in `ATSComparator`
3. Add comparison logic if needed
4. Update report generation to display new metrics
5. Document in this guide

## See Also

- [COMPARISON_GUIDE.md](COMPARISON_GUIDE.md) - File-level comparison
- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Test execution details
- [AUTOMATION_GUIDE.md](AUTOMATION_GUIDE.md) - Deployment automation
