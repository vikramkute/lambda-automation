# Lambda Function Comparison Guide

## Overview

The comparison feature allows you to compare two Lambda functions side-by-side, highlighting differences in code, configuration, and dependencies. Reports are generated in both TXT and PDF formats.

## Features

- **Side-by-side comparison** of all files in function directories
- **Color-coded output** (terminal) with additions/deletions
- **TXT reports** with detailed line-by-line differences
- **PDF reports** with formatted, professional output
- **Batch comparisons** from configuration file
- **Diff statistics** showing total lines changed

## Quick Start

### Compare Two Functions

**Windows:**
```cmd
run.bat compare myTestFunction1 myTestFunction2
```

**macOS/Linux:**
```bash
make compare FUNC1=myTestFunction1 FUNC2=myTestFunction2
```

**Direct Python:**
```bash
python compare_lambda_functions.py myTestFunction1 myTestFunction2
```

### Compare Multiple Pairs

**Windows:**
```cmd
run.bat compare-config
```

**macOS/Linux:**
```bash
make compare-config
```

**Direct Python:**
```bash
python compare_lambda_functions.py comparison.config.yaml
```

## Configuration File

Edit `comparison.config.yaml` to define function pairs:

```yaml
comparisons:
  - function1: myTestFunction1
    function2: myTestFunction2
  
  - function1: myTestFunction3
    function2: myTestFunction4

  - function1: myTestFunction1
    function2: myTestFunction5
```

## Output

### Report Location

All comparison reports are saved to the `comparisons/` directory with timestamped filenames:

```
comparisons/
├── comparison_myTestFunction1_vs_myTestFunction2_20260206_100339.txt
├── comparison_myTestFunction1_vs_myTestFunction2_20260206_100339.pdf
├── comparison_myTestFunction3_vs_myTestFunction4_20260206_100339.txt
└── comparison_myTestFunction3_vs_myTestFunction4_20260206_100339.pdf
```

### Report Contents

Each report includes:
- **Header**: Timestamp, function names, total differences
- **File-by-file comparison**: All files in both function directories
- **Side-by-side diff**: Line-by-line comparison with markers
- **Summary**: Total lines not matching

### Diff Markers

- `➖` Red: Lines removed/only in first function
- `➕` Green: Lines added/only in second function
- `✓` Files are identical
- `❌` File missing in one function

## Command Options

### Disable PDF Generation

If you only need TXT reports:

```bash
python compare_lambda_functions.py func1 func2 --no-pdf
python compare_lambda_functions.py comparison.config.yaml --no-pdf
```

### Custom Output Directory

By default, reports are saved to `comparisons/`. To change this, modify the script:

```python
compare_functions('func1', 'func2', output_dir='my_reports')
```

## Use Cases

### 1. Code Review
Compare functions to identify differences before merging changes:
```bash
run.bat compare myFunction_dev myFunction_prod
```

### 2. Template Validation
Ensure new functions match template structure:
```bash
run.bat compare myNewFunction myTemplateFunction
```

### 3. Migration Verification
Verify functions after runtime upgrades:
```bash
# Before upgrade
run.bat compare func1 func2

# After upgrade
run.bat upgrade
run.bat compare func1 func2
```

### 4. Dependency Audit
Compare requirements.txt across functions:
```bash
run.bat compare-config
# Review PDF reports for dependency differences
```

## Files Compared

The comparison includes all files in function directories:
- `src/lambda_function.py` - Main Lambda handler
- `src/requirements.txt` - Python dependencies
- `template.yml` - SAM template configuration
- Any additional files in function directories

**Excluded:**
- `.aws-sam/` - SAM build artifacts
- `.build/` - Build directory
- `__pycache__/` - Python cache

## Terminal Output

### Example Output

```
================================================================================
Lambda Function Comparison Report
Generated: 2026-02-06 10:03:39
Function 1: myTestFunction1
Function 2: myTestFunction2
================================================================================

────────────────────────────────────────────────────────────────────────────────
File: src/lambda_function.py
────────────────────────────────────────────────────────────────────────────────
⚠ Lines not matching: 5

myTestFunction1                                      | myTestFunction2
----------------------------------------------------------------------+-----------
import json                                          | import json
import boto3                                         | import boto3
                                                     |
def lambda_handler(event, context):                  | def lambda_handler(event, context):
➖     return {'statusCode': 200}                    |
                                                     | ➕     return {'statusCode': 201}

================================================================================
Total lines not matching: 5
================================================================================

✓ Report saved to: comparisons/comparison_myTestFunction1_vs_myTestFunction2_20260206_100339.txt
✓ PDF report saved to: comparisons/comparison_myTestFunction1_vs_myTestFunction2_20260206_100339.pdf
```

## PDF Report Features

- **Professional formatting** with headers and metadata
- **Color-coded differences** (red for deletions, green for additions)
- **Table layout** for side-by-side comparison
- **Pagination** for large diffs
- **Truncation notice** if differences exceed 100 lines per file

## Troubleshooting

### Function Not Found

```
❌ Function directory does not exist: myFunction
```

**Solution:** Verify function directory exists and name is correct.

### No Differences Found

```
✓ Files are identical
Total lines not matching: 0
```

**Solution:** Functions are identical. This is expected if comparing a function to itself.

### PDF Generation Failed

```
⚠ Failed to generate PDF: [error message]
```

**Solution:** TXT report is still generated. Check reportlab installation:
```bash
pip install reportlab
```

### Permission Denied

```
❌ Cannot write to output file: Permission denied
```

**Solution:** Ensure `comparisons/` directory is writable or run with appropriate permissions.

## Integration with Workflow

### Pre-Deployment Comparison

```bash
# Compare before deploying
run.bat compare myFunction_staging myFunction_prod
# Review differences
# Deploy if acceptable
run.bat deploy
```

### Automated Comparison in CI/CD

```yaml
# Example GitHub Actions workflow
- name: Compare Functions
  run: |
    python compare_lambda_functions.py comparison.config.yaml
    
- name: Upload Reports
  uses: actions/upload-artifact@v2
  with:
    name: comparison-reports
    path: comparisons/
```

## Best Practices

✅ **DO:**
- Compare functions before production deployment
- Use config file for regular comparisons
- Review both TXT and PDF reports
- Keep comparison reports in version control for audit trail
- Compare after runtime upgrades

❌ **DON'T:**
- Compare functions with different purposes
- Ignore large differences without investigation
- Skip comparison for critical deployments
- Delete comparison reports immediately

## Advanced Usage

### Programmatic Comparison

```python
from compare_lambda_functions import compare_functions

# Compare two functions
compare_functions(
    'myTestFunction1',
    'myTestFunction2',
    output_dir='custom_reports',
    generate_pdf=True
)
```

### Batch Processing

```python
from compare_lambda_functions import compare_from_config

# Compare all pairs from config
compare_from_config(
    'comparison.config.yaml',
    output_dir='comparisons',
    generate_pdf=True
)
```

## Related Commands

- `run.bat list-functions` - List all configured functions
- `run.bat validate-config` - Validate function configuration
- `run.bat check-runtime-version` - Check runtime versions
- `run.bat test-fast` - Test functions before comparison

---

**See also:** [README.md](README.md) • [REFERENCE.md](REFERENCE.md) • [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
