# AWS Lambda Functions Automation Guide

## Overview

This automation framework provides a complete end-to-end solution for managing AWS Lambda functions with Python using SAM CLI, Terraform, and pytest. All tasks are configuration-driven and easily extensible for additional functions.

## Architecture

```
├── functions.config.yaml           # Master configuration for all functions
├── upgrade_lambda_runtime.py       # Upgrade Lambda runtimes
├── deploy_lambda_functions.py      # Test, build, and deploy pipeline
├── terraform.tf                    # Terraform provider setup
├── terraform_lambda.tf             # Lambda infrastructure as code
├── tests/                          # Pytest test suite
│   └── test_lambda_functions.py    # All function tests
├── Makefile                        # Automation targets
├── run.bat / run.ps1               # Windows automation
├── myTestFunction1-4/              # Individual Lambda functions
│   ├── template.yml                # SAM template
│   └── src/
│       ├── lambda_function.py      # Handler code
│       └── requirements.txt        # Dependencies
└── .build/                         # Build artifacts (generated)
```

## Quick Start

### Prerequisites

**Windows Users**: Use built-in batch/PowerShell scripts:
```cmd
run.bat setup
```

**macOS Users**:
```bash
brew install make
make setup
```

**Linux Users** (Ubuntu/Debian):
```bash
sudo apt-get install make
make setup
```

### 1. Initial Setup

```bash
# Install dependencies and setup virtual environment
make setup
# or: run.bat setup (Windows)

# Validate configuration
make validate-config
# or: run.bat validate-config (Windows)
```

### 2. Upgrade Lambda Runtimes

Upgrade all configured functions to Python 3.14:

```bash
make upgrade
# or: run.bat upgrade (Windows)
```

This script will:
- Read all function configurations from `functions.config.yaml`
- Update each function's `template.yml` with the new runtime
- Create `requirements.txt` if missing
- Run SAM build for each function
- Generate Terraform variables

### 3. Run Tests

Test all Lambda functions locally:

```bash
# Full test suite
make test
# or: run.bat test (Windows)

# Fast mode (skip SAM tests)
make test-fast
# or: run.bat test-fast (Windows)
```

Tests include:
- Configuration validation
- Handler existence verification
- S3 operations testing (mocked with moto)
- Runtime version checks
- Local SAM execution tests (optional)
- Parameterized tests for all functions

### 4. Build and Package

Build and package functions for deployment:

```bash
make build      # Build with SAM CLI
make package    # Package into ZIP files
# or: run.bat build && run.bat package (Windows)
```

### 5. Deploy to AWS

Deploy infrastructure and functions:

```bash
# Plan changes (review before applying)
make plan-deploy
# or: run.bat plan-deploy (Windows)

# Apply Terraform and deploy
make deploy
# or: run.bat deploy (Windows)
```

Or run the complete pipeline:

```bash
make deploy
# or: run.bat deploy (Windows)
```

## Configuration Management

### Adding New Lambda Functions

Edit `functions.config.yaml`:

```yaml
functions:
  - name: myNewFunction
    path: ./myNewFunction
    runtime: python3.14
    description: "New Lambda function"
    enabled: true
    memory: 256
    timeout: 60
```

Directory structure required:

```
myNewFunction/
├── template.yml
└── src/
    ├── lambda_function.py
    └── requirements.txt  # Optional
```

### Function Configuration Options

```yaml
name:                    # Function name (required)
path:                    # Path to function directory (required)
runtime:                 # Python runtime version (required)
memory:                  # Memory in MB (default: 128)
timeout:                 # Timeout in seconds (default: 30)
description:             # Function description
enabled:                 # Include in deployment (default: true)
```

## Scripts

### upgrade_lambda_runtime.py

Upgrades all Lambda functions to specified Python runtime.

```bash
python upgrade_lambda_runtime.py
```

Features:
- Reads from `functions.config.yaml`
- Updates SAM templates automatically
- Manages requirements.txt
- Validates runtime versions
- Runs SAM build for validation
- Comprehensive logging and error handling

### deploy_lambda_functions.py

Complete deployment pipeline: test → build → package → deploy.

```bash
# Full deployment
python deploy_lambda_functions.py

# Custom config file
python deploy_lambda_functions.py --config custom.yaml
```

Features:
- Builds with SAM CLI or creates ZIP packages directly
- Packages into ZIP files
- Generates Terraform variables
- Applies Terraform configuration
- Interactive confirmation before AWS deployment

### test_lambda_functions.py

Pytest test suite for all functions.

```bash
# Run all tests
pytest tests/test_lambda_functions.py -v

# Run specific test class
pytest tests/test_lambda_functions.py::TestMyTestFunction1 -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

Test Coverage:
- Configuration validation
- File existence checks
- Handler imports and callability
- Runtime version validation
- S3 operations (mocked with moto)
- SAM CLI build verification (optional)
- All functions parameterized for scalability

## Terraform Infrastructure

### Resources Created

The Terraform configuration creates:

```
1. Data Source
   - Existing IAM Role (LambdaFullAccessForS3Role)

2. Lambda Functions
   - All configured functions with proper runtimes, memory, timeout
   - Environment variables from configuration
   - Automatic source code from ZIP packages

3. Outputs
   - Lambda function ARNs
   - Lambda function names
```

### Environment Variables

Functions receive environment variables as configured in `functions.config.yaml`. AWS reserved environment variables are automatically filtered out.

### Outputs

After deployment, retrieve:

```bash
# Get all outputs
terraform output -json

# Specific outputs
terraform output lambda_function_arns
terraform output lambda_function_names
```

## Automation Commands

### Setup & Validation

| Command | Description |
|---------|-------------|
| `setup` | Setup environment and install dependencies |
| `validate-config` | Validate functions.config.yaml |
| `list-functions` | List all configured functions |
| `check-runtime-version` | Check Python runtime versions |

### Development Workflow

| Command | Description |
|---------|-------------|
| `upgrade` | Upgrade to latest Python runtime |
| `test` | Run full test suite |
| `test-fast` | Run tests without SAM |
| `build` | Build functions with SAM |
| `package` | Package into ZIP files |

### Deployment

| Command | Description |
|---------|-------------|
| `init-terraform` | Initialize Terraform |
| `plan-deploy` | Plan deployment changes |
| `deploy` | Complete pipeline: test → deploy |
| `destroy-infra` | Destroy AWS resources |

### Maintenance

| Command | Description |
|---------|-------------|
| `clean` | Remove artifacts and temp files |
| `terraform-output` | Show Terraform outputs |
| `full-pipeline` | Execute complete pipeline |

## Workflow Examples

### Development Iteration

```bash
# Make code changes
# Run fast tests
make test-fast
# or: run.bat test-fast (Windows)

# Build and verify locally
make build
# or: run.bat build (Windows)

# Deploy when ready
make deploy
# or: run.bat deploy (Windows)
```

### Complete Fresh Deployment

```bash
make clean
make setup
make validate-config
make upgrade
make test
make deploy
# or Windows equivalent with run.bat
```

### Upgrade Runtime and Deploy

```bash
# Edit functions.config.yaml - update runtime to python3.14
make upgrade
make test
make package
make deploy
# or Windows equivalent with run.bat
```

## Best Practices

### 1. Configuration Management

- Use `functions.config.yaml` as single source of truth
- Commit configuration changes to version control
- Use different configs for dev/staging/prod environments

### 2. Testing

- Always run tests before deployment
- Use `test-fast` for quick iteration during development
- Add function-specific tests to `test_lambda_functions.py`

### 3. Runtime Updates

- Use `upgrade` command to batch runtime changes
- Test thoroughly before production deployment
- Update `requirements.txt` for dependency upgrades

### 4. Terraform State

- Keep `terraform.tfstate` secure (consider S3 backend)
- Review `terraform plan` before applying
- Use version control for `terraform.tf` files

### 5. Deployment

- Always plan before applying (`plan-deploy`)
- Deploy during off-peak hours
- Verify deployment with `status` command

## Troubleshooting

### SAM CLI Not Found

```bash
# Install SAM CLI
pip install aws-sam-cli

# Or use package manager (macOS)
brew tap aws/tap && brew install aws-sam-cli
```

### Terraform Init Fails

```bash
# Reinitialize
make clean
rm -rf .terraform
make init-terraform
```

### Tests Fail

```bash
# Check configuration
make validate-config

# Run specific test with output
pytest tests/test_lambda_functions.py::TestAllFunctions::test_function_file_exists -v -s
```

### AWS Credentials Issues

```bash
# Set credentials
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1

# Or use AWS CLI
aws configure
```

## Advanced Usage

### Custom Terraform Variables

The deployment script automatically generates `terraform.tfvars.json` from your configuration:

```json
{
  "lambda_functions": {
    "myTestFunction1": {
      "runtime": "python3.14",
      "memory": 128,
      "timeout": 30,
      "environment": {},
      "description": "Test function 1 - S3 read operations"
    }
  },
  "aws_region": "us-east-1"
}
```

### CI/CD Integration

```yaml
# Example GitHub Actions
- name: Test Lambda Functions
  run: make test
  # or: run.bat test (Windows)

- name: Deploy to AWS
  run: make deploy
  # or: run.bat deploy (Windows)
```

### Monitoring and Logs

```bash
# Get function metrics
aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Duration --dimensions Name=FunctionName,Value=myTestFunction1 --start-time 2025-01-01T00:00:00Z --end-time 2025-12-31T23:59:59Z --period 3600 --statistics Average
```

## Extending the Framework

### Adding Custom Tests

Edit `tests/test_lambda_functions.py`:

```python
class TestMyCustomFunction:
    def test_custom_logic(self):
        handler = LambdaTestHelper.load_lambda_handler('myTestFunction1')
        response = handler({'custom': 'event'}, lambda_context)
        assert response['statusCode'] == 200
```

### Adding Build Steps

Modify `upgrade_lambda_runtime.py` or `deploy_lambda_functions.py` to add custom build logic.

### Custom Environment Variables

Add to `functions.config.yaml`:

```yaml
functions:
  - name: myFunction
    # ... other config ...
    # Note: environment_variables not currently supported in config
    # but can be added to the scripts
```

## Support and Documentation

- SAM CLI: https://docs.aws.amazon.com/serverless-application-model/
- Terraform AWS: https://registry.terraform.io/providers/hashicorp/aws/latest
- pytest: https://docs.pytest.org/
- boto3: https://boto3.amazonaws.com/

## Summary

This automation framework provides:

✅ **Configuration-Driven**: Single YAML file for all function configs
✅ **Fully Automated**: Commands for every operation
✅ **Scalable**: Add new functions without code changes
✅ **Tested**: Comprehensive pytest suite for validation
✅ **Infrastructure-as-Code**: Terraform for all AWS resources
✅ **CI/CD Ready**: Easy integration with pipelines
✅ **Cross-Platform**: Windows (batch/PowerShell), macOS/Linux (make)

Start with `make help` (or `run.bat help` on Windows) for all available commands!