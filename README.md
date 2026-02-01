# AWS Lambda Automation Framework

Configuration-driven framework for managing AWS Lambda functions with Python, SAM CLI, Terraform, and pytest. Manage unlimited Lambda functions with a single YAML configuration file.

## 🔧 Tool Stack

- **SAM**: Local development and building
- **Pytest**: Quality assurance and validation before deployment
- **Terraform**: Cloud infrastructure management
- **Boto3**: Runtime AWS API calls and testing

## 🎯 Features

- **Configuration-Driven**: Single `functions.config.yaml` for all functions
- **Runtime Upgrades**: Update all functions to latest Python runtime (3.14)
- **Testing**: Comprehensive pytest suite with moto AWS mocking
- **Infrastructure-as-Code**: Terraform automation with tfvars.json
- **Multi-Platform**: Windows (batch/PowerShell), macOS/Linux (make)
- **Function Initialization**: Automated function scaffolding

## 🚀 Quick Start

**Windows:**
```cmd
run.bat setup && run.bat validate-config && run.bat test-fast && run.bat deploy
```

**macOS/Linux:**
```bash
make setup && make validate-config && make test-fast && make deploy
```

**See [SETUP.md](SETUP.md) for detailed installation and [REFERENCE.md](REFERENCE.md) for all commands.**

## 📁 Project Structure

```
├── functions.config.yaml       # Master configuration file
├── terraform.tfvars.json      # Terraform variables (auto-generated)
├── run.bat / run.ps1          # Windows automation scripts
├── Makefile                   # macOS/Linux automation
├── terraform.tf               # Terraform provider config
├── terraform_lambda.tf        # Lambda infrastructure
├── upgrade_lambda_runtime.py  # Runtime upgrade script
├── deploy_lambda_functions.py # Deployment script
├── check_runtime_versions.py  # Runtime version checker
├── requirements.txt           # Python dependencies
├── pytest.ini                # Test configuration
├── LICENSE                    # Project license
├── .gitignore                 # Git ignore rules
├── .gitattributes            # Git attributes
├── AUTOMATION_GUIDE.md       # Automation documentation
├── PREREQUISITES.md          # Prerequisites guide
├── QUICK_REFERENCE.md        # Quick command reference
├── tests/                     # Pytest test suite
│   └── test_lambda_functions.py
├── myTestFunction1/           # Lambda function directories
│   ├── src/
│   │   ├── lambda_function.py
│   │   └── requirements.txt
│   └── template.yml
├── myTestFunction2/
│   ├── src/
│   │   ├── lambda_function.py
│   │   └── requirements.txt
│   └── template.yml
├── myTestFunction3/
│   ├── src/
│   │   ├── lambda_function.py
│   │   └── requirements.txt
│   └── template.yml
├── myTestFunction4/
│   ├── src/
│   │   ├── lambda_function.py
│   │   └── requirements.txt
│   └── template.yml
├── myTestFunction5/
│   ├── src/
│   │   ├── lambda_function.py
│   │   └── requirements.txt
│   └── template.yml
├── .build/                    # Build artifacts
├── .packages/                 # ZIP packages
└── .terraform/                # Terraform state
```

## ⚙️ Configuration

Edit `functions.config.yaml` to manage functions:

```yaml
functions:
  - name: myTestFunction1
    path: ./myTestFunction1
    runtime: python3.14
    description: "Test function 1 - S3 read operations"
    enabled: true
    memory: 128
    timeout: 30

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

**Add new function:** Manually create directory structure and update configuration

## 🛠️ Available Commands

| Task | Windows | macOS/Linux | Description |
|------|---------|-------------|-------------|
| Setup | `run.bat setup` | `make setup` | Initialize environment |
| Help | `run.bat help` | `make help` | Show all commands |
| Install Deps | `run.bat install-deps` | `make install-deps` | Install Python dependencies |
| Validate | `run.bat validate-config` | `make validate-config` | Check YAML syntax |
| List | `run.bat list-functions` | `make list-functions` | Show configured functions |
| Check Runtime | `run.bat check-runtime-version` | `make check-runtime-version` | Check Python versions |
| Upgrade | `run.bat upgrade` | `make upgrade` | Update to Python 3.14 |
| Build | `run.bat build` | `make build` | Build functions with SAM |
| Test | `run.bat test-fast` | `make test-fast` | Quick tests (no SAM) |
| Test Full | `run.bat test` | `make test` | Full test suite |
| Init Terraform | `run.bat init-terraform` | `make init-terraform` | Initialize Terraform |
| Terraform Output | `run.bat terraform-output` | `make terraform-output` | Show Terraform outputs |
| Plan | `run.bat plan-deploy` | `make plan-deploy` | Generate tfvars.json and plan Terraform changes |
| Deploy | `run.bat deploy` | `make deploy` | Complete deployment |
| Destroy | `run.bat destroy-infra` | `make destroy-infra` | Destroy AWS resources |
| Clean | `run.bat clean` | `make clean` | Remove artifacts |
| Full Pipeline | `run.bat full-pipeline` | `make full-pipeline` | Complete setup to deploy |

**See [REFERENCE.md](REFERENCE.md) for complete command reference.**

## 🧪 Testing & Infrastructure

**Testing Framework:**
- Pytest with moto for AWS service mocking
- Parameterized tests for all configured functions
- S3, Lambda, and IAM service testing
- SAM CLI integration tests (optional)

**Infrastructure:**
- Terraform manages Lambda functions, IAM roles, CloudWatch logs
- Requires existing `LambdaFullAccessForS3Role` IAM role (must be created beforehand)
- Automatic tfvars.json generation from YAML config
- Support for environment variables and function descriptions

## 🔄 Common Workflows

**Development Cycle:**
```bash
# Windows
run.bat validate-config && run.bat test-fast && run.bat build && run.bat deploy

# macOS/Linux  
make validate-config && make test-fast && make build && make deploy
```

**Production Deployment:**
```bash
# Windows
run.bat validate-config && run.bat test && run.bat build && run.bat plan-deploy && run.bat deploy

# macOS/Linux
make validate-config && make test && make build && make plan-deploy && make deploy
```

**Runtime Upgrade:**
```bash
# Windows
run.bat upgrade && run.bat test && run.bat deploy

# macOS/Linux
make upgrade && make test && make deploy
```

## 🐛 Troubleshooting

- **Missing dependencies:** Run `run.bat setup` or `make setup`
- **AWS credentials:** Configure with `aws configure`
- **Configuration errors:** Run `validate-config` first
- **Terraform issues:** Use `clean` then `init-terraform`
- **Test failures:** Check function paths and YAML syntax
- **Build failures:** Ensure SAM CLI is installed and accessible

## 📋 Current Functions

The framework currently manages 5 test functions:
- `myTestFunction1`: S3 read operations demo
- `myTestFunction2-4`: Template functions for testing
- `myTestFunction5`: Additional test function (disabled by default)

All functions use Python 3.14 runtime with 128MB memory and 30s timeout.

---

**📚 Documentation:** [SETUP.md](SETUP.md) • [REFERENCE.md](REFERENCE.md) • [AUTOMATION_GUIDE.md](AUTOMATION_GUIDE.md)