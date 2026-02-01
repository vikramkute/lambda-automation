# Prerequisites

## Required Software

### 1. Python 3.14
**Windows:**
```cmd
# Download from python.org or use winget
winget install Python.Python.3.14
```

**macOS:**
```bash
brew install python@3.14
```

**Linux:**
```bash
sudo apt update && sudo apt install python3 python3-pip
```

### 2. AWS CLI
**Windows:**
```cmd
# Download MSI installer from aws.amazon.com/cli
# Or use winget
winget install Amazon.AWSCLI
```

**macOS:**
```bash
brew install awscli
```

**Linux:**
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

### 3. Terraform
**Windows:**
```cmd
# Download from terraform.io or use chocolatey
choco install terraform
```

**macOS:**
```bash
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
```

**Linux:**
```bash
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform
```

### 4. Make (Optional - Windows only)
**Windows:**
```cmd
choco install make
```

## Required Python Packages

Install all packages:
```bash
pip install pyyaml pytest boto3 moto aws-sam-cli
```

Individual packages:
- **pyyaml**: Configuration file parsing
- **pytest**: Testing framework
- **boto3**: AWS SDK for Python
- **moto**: AWS service mocking for tests
- **aws-sam-cli**: SAM CLI for Lambda builds

## AWS Configuration

### 1. AWS Credentials
```bash
aws configure
```
Or set environment variables:
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

### 2. Required IAM Permissions
Your AWS user/role needs:
- Lambda: CreateFunction, UpdateFunctionCode, GetFunction, ListFunctions
- IAM: GetRole, PassRole
- S3: CreateBucket, PutObject, GetObject (if using S3)
- CloudWatch: GetMetricStatistics (optional)

## Verification Commands

### Check Installations
```bash
# Python
python --version

# AWS CLI
aws --version

# Terraform
terraform --version

# Python packages
python -c "import yaml, pytest, boto3, moto; print('All packages installed')"

# SAM CLI
sam --version
```

### Test AWS Access
```bash
# Test AWS credentials
aws sts get-caller-identity

# List Lambda functions
aws lambda list-functions --region us-east-1
```