# Mock Test Data

This directory contains mock files for testing Lambda functions with S3 triggers.

## Files

- **sample.txt**: Basic text file for testing text processing
- **sample.json**: JSON file for testing structured data
- **unicode.txt**: Unicode and emoji characters for encoding tests
- **data.csv**: CSV file for testing tabular data processing
- **empty.txt**: Empty file for edge case testing

## Usage

These files are used by `test_s3_trigger_functions.py` to simulate S3 objects
being uploaded and triggering Lambda functions. The test suite automatically
uploads these files to mock S3 buckets using moto.

## Adding New Mock Files

1. Add the file to this directory
2. Update the MOCK_FILES dictionary in `test_s3_trigger_functions.py`
3. Run tests: `pytest tests/test_s3_trigger_functions.py -v`
