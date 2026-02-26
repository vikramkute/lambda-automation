# Setup Guide

## Prerequisites

- **Python 3.8+** (download from https://www.python.org)
- **AWS CLI** configured with credentials
- **SAM CLI** for local development and building
- **Terraform** for infrastructure management
- **Make** (Windows: via Chocolatey, macOS/Linux: system package)
- **Git** (optional)

## Installation

### Windows

**Option 1: Batch File (Simplest)**
```cmd
run.bat setup
```

**Option 2: PowerShell**
```powershell
.\run.ps1 setup
```

**Option 3: Make (requires Chocolatey)**
```powershell
choco install make
make setup
```

### macOS
```bash
brew install make
make setup
```

### Linux
```bash
sudo apt-get install make  # Ubuntu/Debian
sudo yum install make      # CentOS/RHEL
make setup
```

## SAM CLI Setup

**Windows:**
```powershell
pip install aws-sam-cli
```

**macOS:**
```bash
brew install aws-sam-cli
```

**Linux:**
```bash
pip install aws-sam-cli
```

## AWS Configuration

```bash
# Install AWS CLI
pip install awscli

# Configure credentials
aws configure
# Enter: Access Key ID, Secret Key, Region (e.g., us-east-1)

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

## Terraform Setup

**Windows:**
```powershell
choco install terraform
```

**macOS:**
```bash
brew install terraform
```

**Linux:**
Download from https://www.terraform.io/downloads.html

## Configuration

### functions.config.yaml

Central configuration file:

```yaml
functions:
  - name: myTestFunction1
    path: ./myTestFunction1
    runtime: python3.13
    memory: 128
    timeout: 30
    description: "Test function 1 - S3 read operations"
    enabled: true

  - name: myTestFunction2
    path: ./myTestFunction2
    runtime: python3.13
    memory: 128
    timeout: 30
    description: "Test function 2"
    enabled: true

global:
  aws_region: "us-east-1"
  deployment_bucket: "lambda-deployments"
  test_timeout: 60
  local_testing_port: 3001
  architecture: "x86_64"

build:
  artifact_dir: ".build"
  test_dir: "tests"
```

### Key Configuration Fields

- **name**: Lambda function name (must be unique)
- **path**: Directory containing function code
- **runtime**: Python version (python3.13 recommended)
- **memory**: RAM allocation in MB (128-10240)
- **timeout**: Execution timeout in seconds (1-900)
- **enabled**: true/false to enable/disable function
- **description**: Function description for AWS console

## Validation

```bash
# Windows
run.bat validate-config

# macOS/Linux
make validate-config
```

## First Deployment

```bash
# Windows
run.bat setup
run.bat validate-config
run.bat test-fast
run.bat plan-deploy  # Generates terraform.tfvars.json and plans changes
run.bat deploy

# macOS/Linux
make setup
make validate-config
make test-fast
make plan-deploy  # Generates terraform.tfvars.json and plans changes
make deploy
```

## Troubleshooting

### Python Issues
- **Python not found:** Install from https://www.python.org, check "Add to PATH"
- **Module not found:** Run setup command to install dependencies

### AWS Issues
- **Credentials error:** Run `aws configure` or set environment variables
- **Region error:** Set AWS_DEFAULT_REGION environment variable

### Terraform Issues
- **Command not found:** Install Terraform from official website
- **Init fails:** Run `terraform init` in project directory

### SAM CLI Issues
- **Command not found:** Run `pip install aws-sam-cli`
- **Build fails:** Check Python version compatibility

### Windows-Specific Issues
- **PowerShell execution policy:** Run `Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser`
- **Batch file not found:** Ensure you're in the correct directory

## File Structure After Setup

```
lambda-automation/
├── functions.config.yaml        # Master configuration
├── terraform.tfvars.json        # Auto-generated Terraform variables
├── run.bat                      # Windows batch automation
├── run.ps1                      # Windows PowerShell automation
├── Makefile                     # macOS/Linux automation
├── terraform.tf                 # Terraform provider
├── terraform_lambda.tf          # Lambda infrastructure
├── upgrade_lambda_runtime.py    # Runtime upgrade script
├── deploy_lambda_functions.py   # Deployment script
├── check_runtime_versions.py    # Runtime version checker
├── requirements.txt             # Python dependencies
├── pytest.ini                  # Test configuration
├── LICENSE                      # Project license
├── .gitignore                   # Git ignore rules
├── .gitattributes              # Git attributes
├── AUTOMATION_GUIDE.md         # Automation documentation
├── PREREQUISITES.md            # Prerequisites guide
├── QUICK_REFERENCE.md          # Quick command reference
├── .terraform.lock.hcl         # Terraform lock file
├── .build/                     # Build artifacts (created during build)
├── .packages/                  # ZIP packages (created during package)
├── .terraform/                 # Terraform state (created during init)
├── tests/
│   └── test_lambda_functions.py # Test suite
├── myTestFunction1/
│   ├── template.yml
│   └── src/
│       ├── lambda_function.py
│       └── requirements.txt
├── myTestFunction2/
│   ├── template.yml
│   └── src/
│       ├── lambda_function.py
│       └── requirements.txt
├── myTestFunction3/
│   ├── template.yml
│   └── src/
│       ├── lambda_function.py
│       └── requirements.txt
├── myTestFunction4/
│   ├── template.yml
│   └── src/
│       ├── lambda_function.py
│       └── requirements.txt
└── myTestFunction5/
    ├── template.yml
    └── src/
        ├── lambda_function.py
        └── requirements.txt
```

## Next Steps

1. **Validate setup:** Run validation command
2. **Check functions:** Run list-functions command  
3. **Run tests:** Run test-fast command
4. **Deploy:** Run deploy command when ready

See [REFERENCE.md](REFERENCE.md) for all available commands and workflows.