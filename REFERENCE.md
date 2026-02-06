# Command Reference

## Platform Commands

### Windows (Batch)
```cmd
run.bat <command>
```

### Windows (PowerShell)
```powershell
.\run.ps1 <command>
```

### macOS/Linux (Make)
```bash
make <command>
```

## Available Commands

### Setup & Information
| Command | Description |
|---------|-------------|
| `setup` | Install dependencies and setup environment |
| `help` | Show all available commands |
| `install-deps` | Install Python dependencies only |
| `validate-config` | Validate functions.config.yaml |
| `list-functions` | List all configured functions |
| `check-runtime-version` | Check Python runtime versions |

### Development
| Command | Description |
|---------|-------------|
| `upgrade` | Upgrade all functions to latest Python runtime |
| `build` | Build all Lambda functions with SAM |
| `test` | Run full test suite (includes SAM builds) |
| `test-fast` | Run quick tests (skip SAM builds) |

### Deployment
| Command | Description |
|---------|-------------|
| `init-terraform` | Initialize Terraform |
| `terraform-output` | Show Terraform outputs |
| `plan-deploy` | Generate terraform.tfvars.json and plan Terraform changes |
| `deploy` | Complete pipeline: test → build → deploy |
| `destroy-infra` | Destroy all AWS resources |

### Comparison
| Command | Description |
|---------|-------------|
| `compare` | Compare two Lambda functions (usage: `run.bat compare func1 func2`) |
| `compare-config` | Compare multiple function pairs from comparison.config.yaml |

### Maintenance
| Command | Description |
|---------|-------------|
| `clean` | Remove build artifacts and temporary files |
| `full-pipeline` | Execute complete pipeline from setup to deployment planning |

## Command Examples

### Setup Workflow
```bash
# Windows
run.bat setup
run.bat validate-config
run.bat list-functions

# macOS/Linux
make setup
make validate-config
make list-functions
```

### Development Workflow
```bash
# Quick iteration
run.bat test-fast
run.bat build
run.bat deploy

# Full validation
run.bat test
run.bat deploy
```

### Deployment Workflow
```bash
# Plan first (recommended)
run.bat plan-deploy
# Review output, then:
run.bat deploy
```

### Runtime Upgrade Workflow
```bash
# Check current versions
run.bat check-runtime-version

# Upgrade to latest
run.bat upgrade

# Verify and deploy
run.bat test-fast
run.bat deploy
```

## Direct Script Usage

### Python Scripts
```bash
# Upgrade runtime
python upgrade_lambda_runtime.py

# Deploy with options
python deploy_lambda_functions.py

# Check runtime versions
python check_runtime_versions.py

# Compare functions
python compare_lambda_functions.py func1 func2
python compare_lambda_functions.py comparison.config.yaml
python compare_lambda_functions.py func1 func2 --no-pdf
```

### Terraform Commands
```bash
# Initialize
terraform init

# Plan changes
terraform plan -out=tfplan

# Apply changes
terraform apply tfplan

# View outputs
terraform output -json
terraform output lambda_function_arns

# Destroy resources
terraform destroy
```

### Testing Commands
```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_lambda_functions.py::TestMyTestFunction1 -v

# Skip SAM tests (faster)
SKIP_SAM_TESTS=true pytest tests/ -v
```

## Configuration Management

### Edit Configuration
```bash
# Edit main config
code functions.config.yaml

# Validate after changes
run.bat validate-config
```

### Add New Function
```bash
# Manual method
# 1. Create directory: mkdir myNewFunc/src
# 2. Add to functions.config.yaml
# 3. Create template.yml and lambda_function.py
# 4. Validate: run.bat validate-config
```

### Update Function Settings
Edit `functions.config.yaml`:
```yaml
functions:
  - name: myFunction
    runtime: python3.14    # Update runtime
    memory: 512           # Update memory
    timeout: 120          # Update timeout
    enabled: false        # Disable function
```

## Environment Variables

### AWS Configuration
```bash
# Windows
set AWS_ACCESS_KEY_ID=your_access_key
set AWS_SECRET_ACCESS_KEY=your_secret_key
set AWS_DEFAULT_REGION=us-east-1

# macOS/Linux
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

### Development Options
```bash
# Skip SAM tests for faster execution
set SKIP_SAM_TESTS=true        # Windows
export SKIP_SAM_TESTS=true     # macOS/Linux
```

## Common Workflows

### First-Time Setup
```bash
1. run.bat setup
2. aws configure
3. run.bat validate-config
4. run.bat test-fast
5. run.bat plan-deploy
6. run.bat deploy
```

### Daily Development
```bash
1. Edit code in myFunction/src/lambda_function.py
2. run.bat test-fast
3. run.bat deploy
4. Check function output in AWS console
```

### Production Deployment
```bash
1. run.bat validate-config
2. run.bat test
3. run.bat clean
4. run.bat plan-deploy
5. Review plan output
6. run.bat deploy
```

### Runtime Upgrade
```bash
1. run.bat check-runtime-version
2. Edit functions.config.yaml (update runtime versions)
3. run.bat upgrade
4. run.bat test
5. run.bat deploy
```

### Adding New Function
```bash
1. mkdir myNewFunc/src
2. Edit myNewFunc/src/lambda_function.py
3. Add to functions.config.yaml
4. run.bat validate-config
5. run.bat test-fast
6. run.bat deploy
```

### Comparing Functions
```bash
# Compare two functions directly
run.bat compare myTestFunction1 myTestFunction2

# Compare multiple pairs from config
run.bat compare-config

# Compare without PDF generation
python compare_lambda_functions.py myTestFunction1 myTestFunction2 --no-pdf
```

### Troubleshooting
```bash
1. run.bat validate-config
2. run.bat clean
3. run.bat setup
4. run.bat test-fast
```

## Output Examples



### List Functions Command
```
Configured Lambda Functions:
   myTestFunction1 (python3.14, 128MB)
   myTestFunction2 (python3.14, 128MB)
   myTestFunction3 (python3.14, 128MB)
   myTestFunction4 (python3.14, 128MB)
   myTestFunction5 (python3.14, 128MB) - DISABLED
```

### Terraform Output
```json
{
  "lambda_function_arns": {
    "myTestFunction1": "arn:aws:lambda:us-east-1:123456789:function:myTestFunction1",
    "myTestFunction2": "arn:aws:lambda:us-east-1:123456789:function:myTestFunction2"
  },
  "lambda_function_names": {
    "myTestFunction1": "myTestFunction1",
    "myTestFunction2": "myTestFunction2"
  }
}
```

## Error Handling

### Common Errors and Solutions

| Error | Solution |
|-------|----------|
| `Command not found` | Check you're in correct directory |
| `Python not found` | Install Python, add to PATH |
| `AWS credentials not configured` | Run `aws configure` |
| `Terraform not initialized` | Run `terraform init` |
| `SAM CLI not found` | Run `pip install aws-sam-cli` |
| `Config validation failed` | Check YAML syntax in functions.config.yaml |
| `Tests failed` | Check function code and dependencies |
| `Deployment failed` | Check AWS permissions and region |

### Debug Mode
```bash
# Windows
run.bat test-fast > debug.log 2>&1

# macOS/Linux
make test-fast 2>&1 | tee debug.log
```

## Performance Tips

- Use `test-fast` during development (skips SAM builds)
- Use `deploy` for deployments
- Run `clean` before major operations
- Use `plan-deploy` to review changes before applying
- Keep `functions.config.yaml` as single source of truth

## Best Practices

✅ **DO:**
- Always validate config before deployment
- Run tests before production deployment
- Review terraform plans before applying
- Use environment variables for secrets
- Commit configuration to version control

❌ **DON'T:**
- Hardcode credentials in code
- Skip tests in production
- Deploy without planning
- Commit terraform state files
- Modify infrastructure manually in AWS console