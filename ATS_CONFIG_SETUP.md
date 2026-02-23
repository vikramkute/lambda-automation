# ATS Comparison Configuration Setup

## Overview

The `compare_lambda_functions_ats.py` script has been updated to:
- **Read comparison.config.yaml** for batch comparisons (like compare_lambda_functions.py)
- **Auto-generate comparisons-ats folder** to store all reports
- **Create timestamped reports** (txt + json) for each comparison
- **Support both modes**: single comparison or batch from config

## Key Changes

### 1. New Output Directory
```
comparisons-ats/
├── ats_comparison_func1_vs_func2_20260223_155321.txt
├── ats_comparison_func1_vs_func2_20260223_155321.json
├── ats_comparison_func3_vs_func4_20260223_155401.txt
└── ats_comparison_func3_vs_func4_20260223_155401.json
```

### 2. New Functions

#### `_prepare_ats_output_file(output_dir, func1_name, func2_name)`
- Creates output directory if needed
- Generates timestamped filename: `ats_comparison_{func1}_vs_{func2}_{timestamp}.txt`
- Returns Path object to output file

#### `compare_functions_ats(func1, func2, output_dir="comparisons-ats")`
- Single comparison wrapper with automatic output handling
- Saves both TXT and JSON reports to comparisons-ats folder
- Prints report to console AND saves to file

#### `compare_from_config_ats(config_file, output_dir="comparisons-ats")`
- Batch comparisons from YAML config file
- Reads `comparison.config.yaml` (same format as code-level comparisons)
- Generates reports for all defined function pairs
- Shows progress: `[idx/total]` for each comparison

### 3. Updated main()
Intelligently detects mode based on argument:
```
# Config file mode (detects .yaml or .yml extension)
python compare_lambda_functions_ats.py comparison.config.yaml

# Single comparison mode (detects 2+ arguments)
python compare_lambda_functions_ats.py myTestFunction1 myTestFunction2
```

## Usage Examples

### Single Comparison
```bash
# Auto-saves to: comparisons-ats/ats_comparison_func1_vs_func2_<timestamp>.{txt,json}
python compare_lambda_functions_ats.py myTestFunction1 myTestFunction2

# Or via Makefile (macOS/Linux)
make compare-ats FUNC1=myTestFunction1 FUNC2=myTestFunction2

# Or via run scripts (Windows)
run.bat compare-ats myTestFunction1 myTestFunction2
run.ps1 compare-ats myTestFunction1 myTestFunction2
```

**Output:**
```
[OK] Report saved to: C:\...\comparisons-ats\ats_comparison_myTestFunction1_vs_myTestFunction2_20260223_155321.txt
[OK] JSON report saved to: C:\...\comparisons-ats\ats_comparison_myTestFunction1_vs_myTestFunction2_20260223_155321.json

================================================================================
AWS Lambda Function ATS-Level Comparison Report
================================================================================
[Report content...]
```

### Batch Comparisons from Config
```bash
python compare_lambda_functions_ats.py comparison.config.yaml
```

**Output:**
```
================================================================================
Starting 3 ATS comparison(s) from comparison.config.yaml
Output directory: comparisons-ats
================================================================================

[1/3] Running ATS comparison: myTestFunction1 vs myTestFunction2
================================================================================
[OK] Report saved to: ...
[AWS Lambda Function ATS-Level Comparison Report]
[OK] JSON report saved to: ...

[2/3] Running ATS comparison: myTestFunction3 vs myTestFunction4
================================================================================
[OK] Report saved to: ...
[AWS Lambda Function ATS-Level Comparison Report]
[OK] JSON report saved to: ...

[3/3] Running ATS comparison: myTestFunction1 vs myTestFunction5
================================================================================
[OK] Report saved to: ...
[AWS Lambda Function ATS-Level Comparison Report]
[OK] JSON report saved to: ...

================================================================================
[OK] Completed all 3 ATS comparison(s)
[OK] Reports saved to: comparisons-ats
================================================================================
```

## Configuration File Format

The script uses the same `comparison.config.yaml` as the code-level comparison:

```yaml
comparisons:
  - function1: myTestFunction1
    function2: myTestFunction2
  
  - function1: myTestFunction3
    function2: myTestFunction4

  - function1: myTestFunction1
    function2: myTestFunction5
```

## Report Files

Each comparison generates **2 files**:

### 1. Text Report (.txt)
- Human-readable format
- Configuration differences with significance levels
- Dependency analysis
- Performance metrics
- Event source detection
- Test reliability scores

### 2. JSON Report (.json)
- Machine-readable structured data
- All comparison details in JSON format
- Easy integration with dashboards
- Suitable for CI/CD pipelines
- Programmatic analysis

## Comparison Analysis

Each ATS comparison includes:

**Configuration Changes**
```
[!] runtime (CRITICAL)
  myTestFunction1: python3.12
  myTestFunction2: python3.14

[~] memory (IMPORTANT)
  myTestFunction1: 128
  myTestFunction2: 256
```

**Significance Levels:**
- `[!]` = CRITICAL (affects function behavior)
- `[~]` = IMPORTANT (affects capabilities)
- `[ ]` = MINOR (metadata/description)

**Dependencies**
```
myTestFunction1: 5 packages
myTestFunction2: 8 packages
Difference: 3 packages

[PKG] Only in myTestFunction2:
  - boto3==1.26.0
  - pandas==1.5.0
  - numpy==1.23.0
```

**Performance & Reliability**
```
Estimated Cold Start Time:
  myTestFunction1: 1500 ms
  myTestFunction2: 1200 ms
  [*] myTestFunction2 is ~300ms faster

Code Complexity:
  myTestFunction1: 45.5/100
  myTestFunction2: 65.2/100
```

**Test Results**
```
myTestFunction1: 138/140 passed
myTestFunction2: 138/140 passed

[OK] myTestFunction2 shows better test reliability (+2)
```

## Integration with CI/CD

### GitHub Actions Example
```yaml
- name: ATS Batch Comparisons
  run: |
    python compare_lambda_functions_ats.py comparison.config.yaml
    
- name: Upload Reports
  uses: actions/upload-artifact@v2
  with:
    name: ats-comparisons
    path: comparisons-ats/
```

### Archive Reports
```bash
# Store reports for audit trail
zip -r ats_reports_$(date +%Y%m%d).zip comparisons-ats/
```

## Performance Notes

- **Single comparison**: ~10-30 seconds (includes test execution)
- **Batch comparison**: ~10-30 seconds per pair (parallel if needed)
- **Test timeout**: 15 seconds per test file
- **Memory usage**: <100MB per comparison

## File Organization

```
lambda-automation/
├── comparison.config.yaml           # Config file for batch comparisons
├── compare_lambda_functions_ats.py  # Updated ATS comparison script
├── comparisons-ats/                 # NEW: ATS report storage (auto-created)
│   ├── ats_comparison_func1_vs_func2_20260223_155321.txt
│   ├── ats_comparison_func1_vs_func2_20260223_155321.json
│   ├── ats_comparison_func3_vs_func4_20260223_155401.txt
│   └── ats_comparison_func3_vs_func4_20260223_155401.json
├── comparisons/                     # File-level comparison reports (existing)
└── [other files...]
```

## Benefits of Config-Based Approach

✓ **Consistency**: Same format as code-level comparisons  
✓ **Batch Processing**: Run multiple comparisons at once  
✓ **Automation**: Easy to integrate into CI/CD pipelines  
✓ **Organization**: Reports automatically organized by timestamp  
✓ **Audit Trail**: All historical comparisons preserved  
✓ **Easy Updates**: Just modify comparison.config.yaml to change pairs  

## See Also

- [ATS_COMPARISON_GUIDE.md](ATS_COMPARISON_GUIDE.md) - Full ATS documentation
- [ATS_QUICK_START.md](ATS_QUICK_START.md) - Quick reference guide
- [COMPARISON_GUIDE.md](COMPARISON_GUIDE.md) - File-level comparison docs
