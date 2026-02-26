# Lambda Function Testing Guide

Comprehensive testing guide for all Lambda functions in the automation framework.

## Overview

The framework includes two test suites:

1. **`test_lambda_functions.py`**: General Lambda function tests
   - Configuration validation
   - Handler loading and execution
   - Runtime compatibility
   - Template validation
   - Error handling

2. **`test_s3_trigger_functions.py`**: S3 trigger-specific tests
   - S3 event processing
   - File transformation workflows
   - Storage operations
   - Performance testing

## Running Tests

### Run All Tests
```bash
# Windows
run.bat test-fast    # Fast (no SAM)
run.bat test         # Full (with SAM)

# macOS/Linux
make test-fast       # Fast (no SAM)
make test            # Full (with SAM)

# Direct pytest
pytest tests/ -v
```

### Run Individual Test Suites

**Lambda Function Tests**:
```bash
pytest tests/test_lambda_functions.py -v
```

**S3 Trigger Tests**:
```bash
pytest tests/test_s3_trigger_functions.py -v
```

**Automation Script Tests**:
```bash
pytest tests/test_check_runtime_versions.py -v
pytest tests/test_compare_lambda_functions.py -v
pytest tests/test_deploy_lambda_functions.py -v
pytest tests/test_upgrade_lambda_runtime.py -v
```

### Run Specific Test Classes

**Lambda Function Tests**:
```bash
pytest tests/test_lambda_functions.py::TestAllFunctions -v
pytest tests/test_lambda_functions.py::TestErrorScenarios -v
```

**S3 Trigger Tests**:
```bash
pytest tests/test_s3_trigger_functions.py::TestS3TriggerProcessingStorage -v
pytest tests/test_s3_trigger_functions.py::TestS3TriggerErrorHandling -v
```

**Automation Script Tests**:
```bash
pytest tests/test_deploy_lambda_functions.py::TestPackageFunction -v
pytest tests/test_upgrade_lambda_runtime.py::TestUpgradeFunction -v
```

### Run Single Tests

**Lambda Function Test**:
```bash
pytest tests/test_lambda_functions.py::TestAllFunctions::test_function_config_valid -v
```

**S3 Trigger Test**:
```bash
pytest tests/test_s3_trigger_functions.py::TestS3TriggerProcessingStorage::test_successful_trigger_and_processing -v
```

**Automation Script Test**:
```bash
pytest tests/test_deploy_lambda_functions.py::TestPackageFunction::test_package_function_success -v
```

## Mock Test Files

Located in `tests/mock_data/`:

| File | Purpose |
|------|---------|
| `sample.txt` | Basic text processing |
| `sample.json` | JSON data processing |
| `unicode.txt` | Unicode/emoji handling |
| `data.csv` | CSV data processing |
| `empty.txt` | Edge case testing |

## Test Coverage Details

### test_lambda_functions.py

**1. Configuration Tests**
- Valid YAML structure
- Required fields present
- Memory and timeout values
- Runtime version

**2. File Structure Tests**
- lambda_function.py exists
- template.yml exists
- requirements.txt exists (if needed)

**3. Handler Tests**
- Handler function exists
- Handler is callable
- Handler executes without errors

**4. Runtime Tests**
- Python 3.13 compatibility
- Syntax validation
- Dependency compatibility

**5. Error Handling Tests**
- Invalid event structures
- AWS service errors
- Graceful error responses

**6. SAM Tests (Optional)**
- SAM build succeeds
- Build artifacts created

### test_s3_trigger_functions.py

**1. S3 Trigger Tests**
- Valid S3 events
- Invalid event structures
- Multiple event types
- Event parsing and validation

**2. Processing Tests**
- Text file transformation
- JSON parsing and manipulation
- CSV data processing
- Unicode content handling
- Large file processing (100KB+)
- Empty file handling
- Binary file rejection

**3. Storage Tests**
- Writing to destination bucket
- Verifying stored content
- Handling storage errors
- Permission issues

**4. Error Handling Tests**
- Missing source bucket
- Missing object key
- Missing destination bucket
- Invalid file encoding
- AWS service errors
- Timeout scenarios

**5. Configuration Tests**
- S3 trigger configuration validation
- Environment variable usage
- Bucket name configuration
- Event filter configuration

**6. Performance Tests**
- Execution time < configured timeout
- Memory usage within limits
- Multiple sequential invocations
- Concurrent processing simulation

## Test Results

### Complete Test Suite
```
======================== 46 passed, 2 skipped in 7.81s ========================
```

**Breakdown**:
- `test_lambda_functions.py`: 29 passed, 2 skipped (SAM tests)
- `test_s3_trigger_functions.py`: 17 passed

### Individual Suites

**General Lambda Tests**:
```
tests/test_lambda_functions.py::TestAllFunctions::test_function_config_valid[myTestFunction1] PASSED
tests/test_lambda_functions.py::TestAllFunctions::test_function_file_exists[myTestFunction1] PASSED
tests/test_lambda_functions.py::TestAllFunctions::test_function_handler_exists[myTestFunction1] PASSED
...
======================== 31 tests in 4.5s ========================
```

**S3 Trigger Tests**:
```
tests/test_s3_trigger_functions.py::TestS3TriggerProcessingStorage::test_successful_trigger_and_processing[myTestFunction1] PASSED
tests/test_s3_trigger_functions.py::TestS3TriggerErrorHandling::test_invalid_event_structure[myTestFunction1] PASSED
...
======================== 17 tests in 3.2s ========================
```

## Adding New Functions

### General Lambda Function

1. **Add to `functions.config.yaml`**:
```yaml
functions:
  - name: myNewFunction
    path: ./myNewFunction
    runtime: python3.13
    enabled: true
    memory: 128
    timeout: 30
```

2. **Tests automatically run** for all enabled functions in `test_lambda_functions.py`

### S3 Trigger Lambda Function

1. **Add S3 trigger configuration to `functions.config.yaml`**:
```yaml
functions:
  - name: myNewFunction
    path: ./myNewFunction
    runtime: python3.13
    enabled: true
    environment:
      S3_DESTINATION_BUCKET_NAME: "my-dest-bucket"
    s3_trigger:
      bucket: "my-source-bucket"
      events: ["s3:ObjectCreated:*"]
      filter_prefix: ""
      filter_suffix: ""
```

2. **Implement Lambda Handler**:
```python
import boto3
import json
import os

s3 = boto3.client('s3')

def lambda_handler(event, context):
    try:
        # 1. Extract S3 event details
        source_bucket = event['Records'][0]['s3']['bucket']['name']
        file_key = event['Records'][0]['s3']['object']['key']
    except (KeyError, IndexError) as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid event'})
        }
    
    dest_bucket = os.environ.get('S3_DESTINATION_BUCKET_NAME')
    
    try:
        # 2. Read from S3
        response = s3.get_object(Bucket=source_bucket, Key=file_key)
        content = response['Body'].read().decode('utf-8')
        
        # 3. Process content
        processed = content.upper()  # Your processing logic
        
        # 4. Store result
        s3.put_object(Bucket=dest_bucket, Key=file_key, Body=processed)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Success'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

3. **Tests automatically run** for all functions with `s3_trigger` configuration

## Custom Test Cases

### Adding Function-Specific Tests

**For general Lambda functions**:
```python
class TestMyNewFunction:
    @pytest.fixture(autouse=True)
    def setup(self, aws_credentials):
        self.handler = LambdaTestHelper.load_lambda_handler('myNewFunction')
        self.config = LambdaTestHelper.get_function_config('myNewFunction')
    
    def test_custom_logic(self, lambda_context):
        """Test your specific logic."""
        event = {'key': 'value'}
        response = self.handler(event, lambda_context)
        assert response['statusCode'] == 200
```

**For S3 trigger functions**:
```python
class TestMyNewFunction:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.handler, self.config = S3TriggerTestHelper.load_handler('myNewFunction')
    
    @mock_aws
    def test_custom_processing_logic(self, lambda_context):
        """Test your specific processing logic."""
        s3 = boto3.client('s3', region_name='us-east-1')
        # Your custom test implementation
```

## Best Practices

1. **Use Mock AWS Services**: Always use `@mock_aws` decorator
2. **Test Edge Cases**: Empty files, large files, unicode, binary
3. **Validate Responses**: Check statusCode and response body
4. **Clean Environment**: Reset environment variables after tests
5. **Parameterize Tests**: Use pytest.mark.parametrize for multiple scenarios
6. **Test Error Paths**: Verify error handling and messages
7. **Performance Testing**: Ensure execution within timeout limits

## Troubleshooting

### Test Failures

**Import Errors**:
```bash
pip install -r requirements.txt
```

**Mock AWS Issues**:
```bash
pip install --upgrade moto boto3
```

**Configuration Errors**:
```bash
run.bat validate-config  # Windows
make validate-config      # macOS/Linux
```

### Common Issues

1. **Missing Environment Variables**: Set in test fixtures
2. **Bucket Not Found**: Ensure buckets created in test setup
3. **Encoding Errors**: Test with unicode mock files
4. **Timeout Errors**: Adjust test timeout in pytest.ini

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run Lambda Tests
  run: |
    pip install -r requirements.txt
    pytest tests/ -v --cov --cov-report html
```

### Pre-commit Hook

```bash
#!/bin/bash
pytest tests/ --maxfail=1
```

## Test Metrics

Track these metrics for quality assurance:

- **Code Coverage**: Target 80%+ for Lambda handlers
- **Test Execution Time**: < 10 seconds for full suite
- **Pass Rate**: 100% before deployment
- **Error Coverage**: All error paths tested

## Next Steps

1. **Run all tests**: `run.bat test-fast` or `make test-fast`
2. **Review coverage**: `pytest --cov tests/ --cov-report html`
3. **Add custom tests** for specific business logic
4. **Integrate into CI/CD** pipeline
5. **Monitor metrics** and maintain 100% pass rate

---

**Related Documentation**: [README.md](../README.md) • [REFERENCE.md](../REFERENCE.md) • [AUTOMATION_GUIDE.md](../AUTOMATION_GUIDE.md)
