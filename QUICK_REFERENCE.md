# Quick Reference Guide

## Installation

### Install Make Command

**Windows (Chocolatey)**:
```powershell
# If you don't have Chocolatey, visit: https://chocolatey.org/install
choco install make
```

**Windows (No Installation - Use Built-in Scripts)**:
```cmd
# Use batch file (simplest)
run.bat setup

# Or PowerShell script
.\run.ps1 setup
```

**macOS**:
```bash
brew install make
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt-get install make
```

**Linux (CentOS/RHEL)**:
```bash
sudo yum install make
```

---

## One-Liners for Common Tasks

### Setup & Validation
```bash
# Setup everything
make setup                    # or: run.bat setup

# Install dependencies only
make install-deps             # or: run.bat install-deps

# Validate configuration
make validate-config          # or: run.bat validate-config

# List all functions
make list-functions           # or: run.bat list-functions

# Check runtime versions
make check-runtime-version    # or: run.bat check-runtime-version
```

### Testing
```bash
# Run all tests
make test                     # or: run.bat test

# Quick tests (skip SAM)
make test-fast                # or: run.bat test-fast

# Specific test
pytest tests/test_lambda_functions.py::TestAllFunctions -v
```

### Runtime & Build
```bash
# Upgrade to latest Python
make upgrade                  # or: run.bat upgrade

# Build all functions
make build                    # or: run.bat build
```

### Deployment
```bash
# Initialize Terraform
make init-terraform           # or: run.bat init-terraform

# Plan changes
make plan-deploy              # or: run.bat plan-deploy

# Deploy everything
make deploy                   # or: run.bat deploy

# View outputs
make terraform-output         # or: run.bat terraform-output

# Complete pipeline
make full-pipeline            # or: run.bat full-pipeline
```

### Cleanup
```bash
# Remove build artifacts
make clean                    # or: run.bat clean

# Destroy AWS resources
make destroy-infra            # or: run.bat destroy-infra
```

### Comparison
```bash
# Compare two functions
make compare FUNC1=myTestFunction1 FUNC2=myTestFunction2  # or: run.bat compare myTestFunction1 myTestFunction2

# Compare from config file
make compare-config           # or: run.bat compare-config

# Direct Python usage
python compare_lambda_functions.py myTestFunction1 myTestFunction2
python compare_lambda_functions.py comparison.config.yaml
python compare_lambda_functions.py func1 func2 --no-pdf
```

---

## Configuration Quick Edit

**Add function to `functions.config.yaml`:**

```yaml
- name: myNewFunction
  path: ./myNewFunction
  runtime: python3.14
  memory: 256
  timeout: 60
  description: "My Lambda function"
  enabled: true
```

---

## Workflow Recipes

### Development Iteration
```bash
make test-fast          # Quick test
make build              # Build
make deploy             # Deploy
# Windows: run.bat test-fast && run.bat build && run.bat deploy
```

### Production Deployment
```bash
make validate-config    # Validate
make test               # Full test
make build              # Build
make plan-deploy        # Review plan
make deploy             # Deploy
# Windows: run.bat validate-config && run.bat test && run.bat build && run.bat plan-deploy && run.bat deploy
```

### Runtime Upgrade
```bash
# Edit functions.config.yaml - change runtime to python3.14
make upgrade            # Upgrade templates
make test               # Test
make deploy             # Deploy
# Windows: run.bat upgrade && run.bat test && run.bat deploy
```

---

## File Reference

| File | Purpose |
|------|---------|
| `functions.config.yaml` | Master config (edit this for functions) |
| `comparison.config.yaml` | Function comparison pairs configuration |
| `upgrade_lambda_runtime.py` | Upgrade runtime versions |
| `deploy_lambda_functions.py` | Complete deployment pipeline |
| `check_runtime_versions.py` | Check runtime versions |
| `compare_lambda_functions.py` | Compare Lambda functions side-by-side |
| `tests/test_lambda_functions.py` | Test suite |
| `terraform.tf` | Terraform setup |
| `terraform_lambda.tf` | Lambda infrastructure |
| `Makefile` | All automation commands |
| `run.bat` / `run.ps1` | Windows automation scripts |
| `comparisons/` | Generated comparison reports (TXT & PDF) |

---

## Environment Variables

```bash
# AWS credentials
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1

# Development
export SKIP_SAM_TESTS=true  # Skip SAM in tests
```

---

## Terraform Commands

```bash
# Initialize
terraform init

# Plan changes
terraform plan -out=tfplan

# Apply
terraform apply tfplan

# View outputs
terraform output -json

# Destroy
terraform destroy
```

---

## AWS CLI Shortcuts

```bash
# List Lambda functions
aws lambda list-functions --region us-east-1

# Invoke function
aws lambda invoke --function-name myTestFunction1 response.json
```

---

## Troubleshooting Checklist

- [ ] Configuration valid: `make validate-config` or `run.bat validate-config`
- [ ] Dependencies installed: `make setup` or `run.bat setup`
- [ ] Tests pass: `make test-fast` or `run.bat test-fast`
- [ ] AWS credentials set: `echo $AWS_ACCESS_KEY_ID`
- [ ] Terraform initialized: `terraform init`
- [ ] Plan reviewed: `make plan-deploy` or `run.bat plan-deploy`

---

## Key Files to Edit

1. **Add/change functions**: Edit `functions.config.yaml`
2. **Change runtime**: Edit `functions.config.yaml` (runtime field)
3. **Change memory/timeout**: Edit `functions.config.yaml`
4. **Add code**: Edit `myFunction/src/lambda_function.py`
5. **Add dependencies**: Edit `myFunction/src/requirements.txt`
6. **Add tests**: Edit `tests/test_lambda_functions.py`

---

## Common Errors & Solutions

| Error | Solution |
|-------|----------|
| `SAM not found` | `pip install aws-sam-cli` |
| `Terraform not found` | `brew install terraform` or download |
| `AWS credentials error` | Run `aws configure` |
| `pytest not found` | `make setup` or `run.bat setup` |
| `Config invalid` | Run `make validate-config` or `run.bat validate-config` |
| `Tests fail` | Run `make test-fast` or `run.bat test-fast` with output |

---

## Performance Tips

- Use `make test-fast` or `run.bat test-fast` during development (skip SAM tests)
- Use `make deploy` or `run.bat deploy` for deployments
- Run `make clean` or `run.bat clean` before full deployments
- Use `make plan-deploy` or `run.bat plan-deploy` to review before `make deploy`

---

## Best Practices

✅ **DO:**
- Edit `functions.config.yaml` for configuration
- Run tests before deployment
- Review terraform plans
- Commit configuration to git
- Use environment variables for secrets

❌ **DON'T:**
- Hardcode credentials
- Skip tests in production
- Deploy without planning
- Commit terraform state
- Modify scripts for new functions (use config)

---

## Platform-Specific Commands

### Windows Users (3 Options)

**Option 1: Batch (Simplest)**
```cmd
run.bat setup
run.bat upgrade
run.bat test-fast
run.bat deploy
```

**Option 2: PowerShell**
```powershell
.\run.ps1 setup
.\run.ps1 upgrade
.\run.ps1 test-fast
.\run.ps1 deploy
```

**Option 3: Make (requires choco install make)**
```bash
make setup
make upgrade
make test-fast
make deploy
```

### macOS/Linux Users

```bash
make setup
make upgrade
make test-fast
make deploy
```

---

**See AUTOMATION_GUIDE.md for detailed documentation**
**See README.md for overview and examples**