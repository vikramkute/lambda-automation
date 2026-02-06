# AWS Lambda Function Automation Script (Windows)
# PowerShell version - provides same functionality as Makefile
# Usage: .\run.ps1 <command>

param(
    [Parameter(Position = 0)]
    [string]$Command = "help",
    [Parameter(Position = 1)]
    [string]$FunctionList,
    [Parameter(Position = 2)]
    [string]$Function2,
    [Parameter(Position = 3)]
    [string]$ScriptName = ".\run.ps1"
)

$PYTHON = "python"

# Helper function to write colored output
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    
    $validColors = @("Black", "DarkBlue", "DarkGreen", "DarkCyan", "DarkRed", "DarkMagenta", "DarkYellow", "Gray", "DarkGray", "Blue", "Green", "Cyan", "Red", "Magenta", "Yellow", "White")
    
    if ($validColors -contains $Color) {
        Write-Host $Message -ForegroundColor $Color
    } else {
        Write-Host $Message
    }
}

# Helper function to test if command exists
function Test-CommandExists {
    param([string]$Command)
    try {
        $null = & $Command --version 2>$null
        return $true
    } catch {
        return $false
    }
}

# Cmd-Setup: Initialize environment
function Cmd-Setup {
    Write-ColorOutput "Setting up environment..." "Blue"
    
    # Check Python
    if (-not (Test-CommandExists $PYTHON)) {
        Write-ColorOutput "ERROR: Python is not installed or not in PATH" "Red"
        exit 1
    }
    Write-ColorOutput "  [OK] Python found" "Green"
    
    # Check required packages
    Write-ColorOutput "Checking Python packages..." "Blue"
    try {
        & $PYTHON -c "import yaml, pytest, boto3, moto; print('All packages found')"
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "  [OK] All required packages found" "Green"
        } else {
            throw "Package check failed"
        }
    } catch {
        Write-ColorOutput "Installing required packages..." "Yellow"
        & pip install pyyaml pytest boto3==1.42.1 moto pytest-moto
    }
    
    # Check SAM CLI
    if (-not (Test-CommandExists "sam")) {
        Write-ColorOutput "ERROR: AWS SAM CLI not found. Install with: pip install aws-sam-cli" "Red"
        exit 1
    }
    Write-ColorOutput "  [OK] AWS SAM CLI found" "Green"
    
    # Check Terraform
    if (-not (Test-CommandExists "terraform")) {
        Write-ColorOutput "ERROR: Terraform not found. Download from: https://www.terraform.io/downloads.html" "Red"
        exit 1
    }
    Write-ColorOutput "  [OK] Terraform found" "Green"
    
    # Initialize Terraform
    Write-ColorOutput "Initializing Terraform..." "Blue"
    & terraform init
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "ERROR: Terraform init failed!" "Red"
        exit 1
    }
    Write-ColorOutput "  [OK] Terraform initialized" "Green"
    
    Write-ColorOutput "Setup complete!" "Green"
}

# Show-Help: Show help
function Show-Help {
    param([string]$ScriptName = ".\run.ps1")
    
    Write-ColorOutput "`n=== AWS Lambda Automation Commands ===" "Cyan"
    Write-ColorOutput "`nUsage: $ScriptName <command>" "White"
    Write-ColorOutput "`nAvailable Commands:" "Yellow"
    
    Write-Host "  setup                  Initialize environment and check dependencies"
    Write-Host "  help                   Show this help message"
    Write-Host "  install-deps           Install Python dependencies only"
    Write-Host "  validate-config        Validate configuration file"
    Write-Host "  list-functions         List all configured Lambda functions"
    Write-Host "  check-runtime-version  Check runtime versions of all functions"
    Write-Host "  upgrade                Upgrade all Lambda functions to latest Python version"
    Write-Host "  build                  Build all Lambda functions"
    Write-Host "  compare [func1] [func2] Compare two Lambda functions"
    Write-Host "  compare-config         Compare functions from comparison.config.yaml"
    Write-Host "  test                   Run full test suite with SAM"
    Write-Host "  test-fast              Run fast test suite (no SAM build)"
    Write-Host "  init-terraform         Initialize Terraform"
    Write-Host "  create-log-groups      Create CloudWatch log groups for Lambda functions"
    Write-Host "  terraform-output       Display Terraform outputs"
    Write-Host "  plan-deploy            Generate tfvars and plan Terraform changes"
    Write-Host "  deploy                 Deploy all Lambda functions to AWS"
    Write-Host "  delete-function [name] Delete specific Lambda function from AWS"
    Write-Host "  destroy-infra          Destroy AWS resources (Terraform destroy)"
    Write-Host "  clean                  Remove build artifacts"
    Write-Host "  full-pipeline          Execute complete pipeline from setup to deployment planning"
    
    Write-ColorOutput "`nExamples:" "Yellow"
    Write-Host "  $ScriptName setup"
    Write-Host "  $ScriptName validate-config"
    Write-Host "  $ScriptName upgrade"
    Write-Host "  $ScriptName compare myTestFunction1 myTestFunction2"
    Write-Host "  $ScriptName compare-config"
    Write-Host "  $ScriptName test"
    Write-Host "  $ScriptName deploy"
    Write-Host ""
}

# Cmd-ValidateConfig: Validate configuration
function Cmd-ValidateConfig {
    Write-ColorOutput "Validating configuration..." "Blue"
    if (-not (Test-Path "functions.config.yaml")) {
        Write-ColorOutput "ERROR: functions.config.yaml not found!" "Red"
        exit 1
    }
    & $PYTHON -c 'import yaml; yaml.safe_load(open(\"functions.config.yaml\")); print(\"Configuration is valid\")'
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "Configuration validation failed!" "Red"
        exit 1
    }
    Write-ColorOutput "[OK] Configuration is valid" "Green"
}

# Cmd-ListFunctions: List configured functions
function Cmd-ListFunctions {
    Write-ColorOutput "Configured Lambda Functions:" "Blue"
    Cmd-ValidateConfig
    & $PYTHON check_runtime_versions.py
}

# Cmd-CheckRuntimeVersion: Check runtime versions
function Cmd-CheckRuntimeVersion {
    Write-ColorOutput "Lambda Function Runtime Versions (enabled only):" "Blue"
    & $PYTHON check_runtime_versions.py
}

# Cmd-InstallDeps: Install Python dependencies
function Cmd-InstallDeps {
    Write-ColorOutput "Installing dependencies..." "Blue"
    & pip install pyyaml pytest boto3==1.42.1 moto pytest-moto
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "Failed to install dependencies!" "Red"
        exit 1
    }
    Write-ColorOutput "[OK] Dependencies installed" "Green"
}

# Cmd-TerraformOutput: Display Terraform outputs
function Cmd-TerraformOutput {
    Write-ColorOutput "Terraform Outputs:" "Blue"
    & terraform output -json
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "Failed to get Terraform outputs!" "Red"
        exit 1
    }
}

# Cmd-FullPipeline: Execute complete pipeline
function Cmd-FullPipeline {
    Write-ColorOutput "Executing full pipeline..." "Blue"
    Cmd-Clean
    Cmd-Setup
    Cmd-ValidateConfig
    Cmd-Upgrade
    Cmd-Build
    Cmd-Test
    Cmd-PlanDeploy
    Write-ColorOutput "[OK] Full pipeline complete!" "Green"
    if ($ScriptName -eq "run.bat") {
        Write-ColorOutput "Next step: Run 'run.bat deploy' to deploy to AWS" "Blue"
    } else {
        Write-ColorOutput "Next step: Run '.\run.ps1 deploy' to deploy to AWS" "Blue"
    }
}

# Cmd-Upgrade: Upgrade Lambda runtimes
function Cmd-Upgrade {
    Write-ColorOutput "Upgrading Lambda function runtimes..." "Blue"
    
    if (-not (Test-Path "upgrade_lambda_runtime.py")) {
        Write-ColorOutput "ERROR: upgrade_lambda_runtime.py not found!" "Red"
        exit 1
    }
    
    & $PYTHON upgrade_lambda_runtime.py
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "Upgrade failed!" "Red"
        exit 1
    }
    
    Write-ColorOutput "[OK] Lambda functions upgraded successfully" "Green"
}


# Cmd-Build: Build Lambda functions
function Cmd-Build {
    Write-ColorOutput "Building Lambda functions..." "Blue"
    
    if (-not (Test-Path "upgrade_lambda_runtime.py")) {
        Write-ColorOutput "ERROR: upgrade_lambda_runtime.py not found!" "Red"
        exit 1
    }
    
    & $PYTHON upgrade_lambda_runtime.py --build-only
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "Build failed!" "Red"
        exit 1
    }
    
    # Create ZIP packages
    Write-ColorOutput "Creating ZIP packages..." "Blue"
    if (-not (Test-Path ".packages")) {
        New-Item -ItemType Directory -Path ".packages" -Force | Out-Null
    }
    
    # Get functions from config
    $functions = & $PYTHON -c "import yaml; c=yaml.safe_load(open('functions.config.yaml')); print(' '.join([f['name'] for f in c.get('functions', []) if f.get('enabled', True)]))"
    
    foreach ($func in $functions.Split(' ')) {
        if ($func -and (Test-Path "$func\src")) {
            Write-ColorOutput "  Creating ZIP for $func..." "Yellow"
            powershell "Compress-Archive -Path '$func\src\*' -DestinationPath '.packages\$func.zip' -Force"
        }
    }
    
    Write-ColorOutput "[OK] Build and packaging complete" "Green"
}

# Cmd-TestFast: Fast test without SAM
function Cmd-TestFast {
    Write-ColorOutput "Running fast tests (no SAM)..." "Blue"
    $env:SKIP_SAM_TESTS = 'true'
    
    $testDir = & $PYTHON -c "import yaml; c=yaml.safe_load(open('functions.config.yaml')); print(c.get('build',{}).get('test_dir','tests'))"
    
    & $PYTHON -m pytest $testDir/test_lambda_functions.py $testDir/test_s3_trigger_functions.py -v --tb=short --cov=. --cov-report=html
    
    Remove-Item env:SKIP_SAM_TESTS -ErrorAction SilentlyContinue
    
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "Tests failed!" "Red"
        exit 1
    }
    Write-ColorOutput "[OK] Tests passed" "Green"
}

# Cmd-Test: Run full test suite
function Cmd-Test {
    Write-ColorOutput "Running full test suite..." "Blue"
    
    $testDir = & $PYTHON -c "import yaml; c=yaml.safe_load(open('functions.config.yaml')); print(c.get('build',{}).get('test_dir','tests'))"
    
    & $PYTHON -m pytest $testDir/test_lambda_functions.py $testDir/test_s3_trigger_functions.py -v --tb=short --cov=. --cov-report=html
    
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "Tests failed!" "Red"
        exit 1
    }
    Write-ColorOutput "[OK] Tests passed" "Green"
}

# Cmd-InitTerraform: Initialize Terraform
function Cmd-InitTerraform {
    Write-ColorOutput "Initializing Terraform..." "Blue"
    & terraform init
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "Terraform init failed!" "Red"
        exit 1
    }
    Write-ColorOutput "[OK] Terraform initialized" "Green"
}

# Cmd-PlanDeploy: Plan deployment changes
function Cmd-PlanDeploy {
    Write-ColorOutput "Planning deployment changes..." "Blue"
    
    # Generate terraform.tfvars.json first
    Write-ColorOutput "Generating Terraform variables..." "Yellow"
    & $PYTHON -c "import yaml,json; c=yaml.safe_load(open('functions.config.yaml')); json.dump({'aws_region': c.get('global',{}).get('aws_region','us-east-1'), 'lambda_functions': {f['name']: {'runtime': f['runtime'], 'memory': f['memory'], 'timeout': f['timeout'], 'environment': f.get('environment_variables',{}), 'description': f.get('description','')} for f in c.get('functions',[]) if f.get('enabled',True)}}, open('terraform.tfvars.json','w'), indent=2)"
    
    & terraform plan -out=tfplan
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "Terraform plan failed!" "Red"
        exit 1
    }
    Write-ColorOutput "[OK] Deployment plan complete. Review output above." "Green"
}





# Cmd-CreateLogGroups: Create CloudWatch log groups for Lambda functions
function Cmd-CreateLogGroups {
    Write-ColorOutput "Creating CloudWatch log groups..." "Blue"
    
    # Get functions from config
    $functions = & $PYTHON -c "import yaml; c=yaml.safe_load(open('functions.config.yaml')); print(' '.join([f['name'] for f in c.get('functions', []) if f.get('enabled', True)]))"
    
    foreach ($func in $functions.Split(' ')) {
        if ($func) {
            $logGroupName = "/aws/lambda/$func"
            Write-ColorOutput "  Creating log group: $logGroupName" "Yellow"
            
            # Check if log group exists
            $exists = & aws logs describe-log-groups --log-group-name-prefix $logGroupName --query "logGroups[0].logGroupName" --output text 2>$null
            
            if ($exists -eq "None" -or $exists -eq "") {
                & aws logs create-log-group --log-group-name $logGroupName
                if ($LASTEXITCODE -eq 0) {
                    Write-ColorOutput "    [OK] Created $logGroupName" "Green"
                } else {
                    Write-ColorOutput "    [ERROR] Failed to create $logGroupName" "Red"
                }
            } else {
                Write-ColorOutput "    [OK] $logGroupName already exists" "Green"
            }
        }
    }
    
    Write-ColorOutput "[OK] Log group creation complete" "Green"
}

# Cmd-DeleteFunction: Delete specific Lambda function
function Cmd-DeleteFunction {
    param([string]$FunctionName)
    
    if (-not $FunctionName) {
        Write-ColorOutput "ERROR: Function name required. Usage: delete-function <function-name>" "Red"
        exit 1
    }
    
    Write-ColorOutput "Deleting Lambda function: $FunctionName" "Blue"
    
    # Check if function exists
    $exists = & aws lambda get-function --function-name $FunctionName --query 'Configuration.FunctionName' --output text 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "Function '$FunctionName' not found in AWS" "Yellow"
        exit 0
    }
    
    # Confirm deletion
    Write-ColorOutput "WARNING: This will permanently delete '$FunctionName' from AWS!" "Red"
    Write-Host "Press Ctrl+C to cancel, or Enter to continue..."
    $null = Read-Host
    
    # Delete the function
    & aws lambda delete-function --function-name $FunctionName
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "[OK] Function '$FunctionName' deleted successfully" "Green"
    } else {
        Write-ColorOutput "Failed to delete function '$FunctionName'" "Red"
        exit 1
    }
}

# Cmd-Compare: Compare two Lambda functions
function Cmd-Compare {
    param([string]$Func1, [string]$Func2)
    
    if (-not $Func1 -or -not $Func2) {
        Write-ColorOutput "ERROR: Two function names required. Usage: compare <function1> <function2>" "Red"
        exit 1
    }
    
    Write-ColorOutput "Comparing $Func1 vs $Func2..." "Blue"
    
    if (-not (Test-Path "compare_lambda_functions.py")) {
        Write-ColorOutput "ERROR: compare_lambda_functions.py not found!" "Red"
        exit 1
    }
    
    & $PYTHON compare_lambda_functions.py $Func1 $Func2
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "Comparison failed!" "Red"
        exit 1
    }
    
    Write-ColorOutput "[OK] Comparison complete" "Green"
}

# Cmd-CompareConfig: Compare functions from config file
function Cmd-CompareConfig {
    Write-ColorOutput "Comparing functions from comparison.config.yaml..." "Blue"
    
    if (-not (Test-Path "compare_lambda_functions.py")) {
        Write-ColorOutput "ERROR: compare_lambda_functions.py not found!" "Red"
        exit 1
    }
    
    if (-not (Test-Path "comparison.config.yaml")) {
        Write-ColorOutput "ERROR: comparison.config.yaml not found!" "Red"
        exit 1
    }
    
    & $PYTHON compare_lambda_functions.py comparison.config.yaml
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "Comparison failed!" "Red"
        exit 1
    }
    
    Write-ColorOutput "[OK] All comparisons complete" "Green"
}

# Cmd-Deploy: Deploy Lambda functions
function Cmd-Deploy {
    Write-ColorOutput "Deploying Lambda functions..." "Blue"
    
    # Create log groups first
    Cmd-CreateLogGroups
    
    if (-not (Test-Path "deploy_lambda_functions.py")) {
        Write-ColorOutput "ERROR: deploy_lambda_functions.py not found!" "Red"
        exit 1
    }
    
    & $PYTHON deploy_lambda_functions.py
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "Deployment failed!" "Red"
        exit 1
    }
    
    Write-ColorOutput "[OK] Deployment complete" "Green"
}



# Cmd-Clean: Clean build artifacts
function Cmd-Clean {
    Clear-Host
    Write-ColorOutput "Cleaning build artifacts..." "Blue"
    
    Get-ChildItem -Path ".aws-sam" -Recurse -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
    Remove-Item -Path ".terraform" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "terraform.tfstate*" -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "terraform.tfvars.json" -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "tfplan" -Force -ErrorAction SilentlyContinue
    Remove-Item -Path ".packages" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path ".build" -Recurse -Force -ErrorAction SilentlyContinue
    
    Write-ColorOutput "[OK] Cleanup complete" "Green"
}

# Cmd-DestroyInfra: Destroy AWS resources
function Cmd-DestroyInfra {
    Write-ColorOutput "WARNING: This will destroy AWS resources!" "Red"
    Write-Host "Press Ctrl+C to cancel, or Enter to continue..."
    $null = Read-Host
    
    Write-ColorOutput "Running: terraform destroy" "Yellow"
    & terraform destroy
    
    Write-ColorOutput "[OK] Infrastructure destroyed" "Green"
}

# Main command dispatcher
switch ($Command.ToLower()) {
    "setup" { Cmd-Setup }
    "help" { Show-Help $ScriptName }
    "install-deps" { Cmd-InstallDeps }
    "validate-config" { Cmd-ValidateConfig }
    "list-functions" { Cmd-ListFunctions }
    "check-runtime-version" { Cmd-CheckRuntimeVersion }
    "upgrade" { Cmd-Upgrade }
    "build" { Cmd-Build }
    "compare" { Cmd-Compare $FunctionList $Function2 }
    "compare-config" { Cmd-CompareConfig }
    "test" { Cmd-Test }
    "test-fast" { Cmd-TestFast }
    "init-terraform" { Cmd-InitTerraform }
    "create-log-groups" { Cmd-CreateLogGroups }
    "terraform-output" { Cmd-TerraformOutput }
    "plan-deploy" { Cmd-PlanDeploy }
    "deploy" { Cmd-Deploy }
    "delete-function" { Cmd-DeleteFunction $FunctionList }
    "destroy-infra" { Cmd-DestroyInfra }
    "clean" { Cmd-Clean }
    "full-pipeline" { Cmd-FullPipeline }
    default {
        Write-ColorOutput "Unknown command: $Command" "Red"
        Show-Help $ScriptName
        exit 1
    }
}
