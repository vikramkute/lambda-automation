.PHONY: help setup install-deps validate-config list-functions check-runtime-version upgrade build compare compare-config test test-fast init-terraform create-log-groups terraform-output plan-deploy deploy delete-function destroy-infra clean full-pipeline

# Variables
PYTHON := python3
PIP := pip3
TERRAFORM := terraform
SAM := sam
CONFIG := functions.config.yaml

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Display this help message
	@echo "$(BLUE)AWS Lambda Automation Makefile$(NC)"
	@echo "======================================"
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

setup: ## Setup project environment and dependencies
	@echo "$(BLUE)Setting up project environment...$(NC)"
	$(PYTHON) -m venv venv
	. venv/Scripts/activate && $(PIP) install -r requirements.txt
	@echo "$(BLUE)Initializing Terraform...$(NC)"
	$(TERRAFORM) init
	@echo "$(GREEN)[OK] Environment setup complete$(NC)"

install-deps: ## Install Python dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)[OK] Dependencies installed$(NC)"

validate-config: ## Validate functions configuration file
	@echo "$(BLUE)Validating configuration...$(NC)"
	$(PYTHON) -c "import yaml; yaml.safe_load(open('$(CONFIG)')); print('[OK] Configuration is valid')"

upgrade: validate-config ## Upgrade all Lambda functions to latest Python runtime
	@echo "$(BLUE)Upgrading Lambda functions...$(NC)"
	$(PYTHON) upgrade_lambda_runtime.py
	@echo "$(GREEN)[OK] Lambda functions upgraded successfully$(NC)"

test: ## Run pytest test suite for all functions
	@echo "$(BLUE)Running tests...$(NC)"
	@TEST_DIR=$$($(PYTHON) -c "import yaml; c=yaml.safe_load(open('$(CONFIG)')); print(c.get('build',{}).get('test_dir','tests'))"); \
	$(PYTHON) -m pytest $$TEST_DIR/test_lambda_functions.py $$TEST_DIR/test_s3_trigger_functions.py -v --tb=short --cov=. --cov-report=html
	@echo "$(GREEN)[OK] Tests passed$(NC)"

test-fast: ## Run tests without SAM CLI tests
	@echo "$(BLUE)Running tests (fast mode)...$(NC)"
	@TEST_DIR=$$($(PYTHON) -c "import yaml; c=yaml.safe_load(open('$(CONFIG)')); print(c.get('build',{}).get('test_dir','tests'))"); \
	SKIP_SAM_TESTS=true $(PYTHON) -m pytest $$TEST_DIR/test_lambda_functions.py $$TEST_DIR/test_s3_trigger_functions.py -v --tb=short --cov=. --cov-report=html
	@echo "$(GREEN)[OK] Tests passed$(NC)"

build: ## Build all Lambda functions with SAM CLI and create ZIP packages
	@echo "$(BLUE)Building functions...$(NC)"
	$(PYTHON) upgrade_lambda_runtime.py --build-only
	@echo "$(BLUE)Creating ZIP packages...$(NC)"
	@mkdir -p .packages
	@for func in $$($(PYTHON) -c "import yaml; c=yaml.safe_load(open('$(CONFIG)')); print(' '.join([f['name'] for f in c.get('functions', []) if f.get('enabled', True)]))"); do \
		if [ -d "$$func/src" ]; then \
			echo "  Creating ZIP for $$func..."; \
			cd "$$func/src" && zip -r "../../.packages/$$func.zip" . && cd ../..; \
		fi; \
	done
	@echo "$(GREEN) Build and packaging complete$(NC)"

compare: ## Compare two Lambda functions (Usage: make compare FUNC1=function1 FUNC2=function2)
	@if [ -z "$(FUNC1)" ] || [ -z "$(FUNC2)" ]; then \
		echo "$(RED)ERROR: Two function names required. Usage: make compare FUNC1=function1 FUNC2=function2$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Comparing $(FUNC1) vs $(FUNC2)...$(NC)"
	@$(PYTHON) compare_lambda_functions.py $(FUNC1) $(FUNC2)
	@echo "$(GREEN)[OK] Comparison complete$(NC)"

compare-config: ## Compare multiple function pairs from comparison.config.yaml
	@echo "$(BLUE)Comparing functions from comparison.config.yaml...$(NC)"
	@if [ ! -f "comparison.config.yaml" ]; then \
		echo "$(RED)ERROR: comparison.config.yaml not found!$(NC)"; \
		exit 1; \
	fi
	@$(PYTHON) compare_lambda_functions.py comparison.config.yaml
	@echo "$(GREEN)[OK] All comparisons complete$(NC)"

init-terraform: ## Initialize Terraform configuration
	@echo "$(BLUE)Initializing Terraform...$(NC)"
	$(TERRAFORM) init
	@echo "$(GREEN) Terraform initialized$(NC)"

create-log-groups: ## Create CloudWatch log groups for Lambda functions
	@echo "$(BLUE)Creating CloudWatch log groups...$(NC)"
	@for func in $$($(PYTHON) -c "import yaml; c=yaml.safe_load(open('$(CONFIG)')); print(' '.join([f['name'] for f in c.get('functions', []) if f.get('enabled', True)]))"); do \
		if [ -n "$$func" ]; then \
			log_group="/aws/lambda/$$func"; \
			echo "  Creating log group: $$log_group"; \
			exists=$$(aws logs describe-log-groups --log-group-name-prefix "$$log_group" --query "logGroups[0].logGroupName" --output text 2>/dev/null || echo "None"); \
			if [ "$$exists" = "None" ] || [ -z "$$exists" ]; then \
				aws logs create-log-group --log-group-name "$$log_group" && echo "    [OK] Created $$log_group" || echo "    [ERROR] Failed to create $$log_group"; \
			else \
				echo "    [OK] $$log_group already exists"; \
			fi; \
		fi; \
	done
	@echo "$(GREEN) Log group creation complete$(NC)"

plan-deploy: validate-config ## Generate terraform.tfvars.json and plan Terraform deployment
	@echo "$(BLUE)Planning deployment changes...$(NC)"
	@echo "$(BLUE)Generating Terraform variables...$(NC)"
	@$(PYTHON) -c "import yaml,json; c=yaml.safe_load(open('$(CONFIG)')); json.dump({'aws_region': c.get('global',{}).get('aws_region','us-east-1'), 'lambda_functions': {f['name']: {'runtime': f['runtime'], 'memory': f['memory'], 'timeout': f['timeout'], 'environment': f.get('environment_variables',{}), 'description': f.get('description','')} for f in c.get('functions',[]) if f.get('enabled',True)}}, open('terraform.tfvars.json','w'), indent=2)"
	@$(TERRAFORM) plan -out=tfplan
	@echo "$(GREEN) Deployment plan complete. Review output above.$(NC)"



deploy: ## Deploy all Lambda functions to AWS
	@echo "$(BLUE)Deploying Lambda functions...$(NC)"
	@$(MAKE) create-log-groups
	@if [ ! -f "deploy_lambda_functions.py" ]; then \
		echo "$(RED)ERROR: deploy_lambda_functions.py not found!$(NC)"; \
		exit 1; \
	fi
	@$(PYTHON) deploy_lambda_functions.py
	@echo "$(GREEN)[OK] Deployment complete$(NC)"


terraform-output: ## Display Terraform outputs
	@echo "$(BLUE)Terraform Outputs:$(NC)"
	@$(TERRAFORM) output -json

delete-function: ## Delete specific Lambda function from AWS (Usage: make delete-function FUNC=function-name)
	@if [ -z "$(FUNC)" ]; then \
		echo "$(RED)ERROR: Function name required. Usage: make delete-function FUNC=function-name$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Deleting Lambda function: $(FUNC)$(NC)"
	@exists=$$(aws lambda get-function --function-name "$(FUNC)" --query 'Configuration.FunctionName' --output text 2>/dev/null || echo "None"); \
	if [ "$$exists" = "None" ]; then \
		echo "Function '$(FUNC)' not found in AWS"; \
		exit 0; \
	fi
	@echo "$(RED)WARNING: This will permanently delete '$(FUNC)' from AWS!$(NC)"
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read dummy
	@aws lambda delete-function --function-name "$(FUNC)" && echo "$(GREEN)[OK] Function '$(FUNC)' deleted successfully$(NC)" || (echo "$(RED)Failed to delete function '$(FUNC)'$(NC)" && exit 1)

destroy-infra: ## Destroy Terraform-managed AWS infrastructure
	@echo "$(RED)WARNING: This will destroy AWS resources!$(NC)"
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read dummy
	@echo "Running: terraform destroy"
	@$(TERRAFORM) destroy
	@echo "$(GREEN)[OK] Infrastructure destroyed$(NC)"

clean: ## Clean build artifacts and temporary files
	@clear
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	@rm -rf .aws-sam .terraform terraform.tfstate* terraform.tfvars.json tfplan .packages .build .pytest_cache __pycache__ 2>/dev/null || true
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)[OK] Cleanup complete$(NC)"

list-functions: validate-config ## List all configured Lambda functions
	@echo "$(BLUE)Configured Lambda Functions:$(NC)"
	$(PYTHON) check_runtime_versions.py

check-runtime-version: ## Check Python runtime versions across all functions
	@echo "$(BLUE)Lambda Function Runtime Versions:$(NC)"
	$(PYTHON) check_runtime_versions.py


full-pipeline: clean setup validate-config upgrade build test plan-deploy ## Execute complete pipeline from environment setup through planning deployment
	@echo "$(GREEN) Full pipeline complete!$(NC)"
	@echo "$(BLUE)Next step: Run 'make deploy' to deploy to AWS$(NC)"

.DEFAULT_GOAL := help
