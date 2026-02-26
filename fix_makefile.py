#!/usr/bin/env python3
"""Fix Makefile build target to use build_packages.py helper script."""

import re

# Read the Makefile
with open('Makefile', 'r') as f:
    content = f.read()

# Replace the complex build target
old_build = r'''build: ## Build all Lambda functions with SAM CLI and create ZIP packages
	@echo "\$\(BLUE\)Building functions\.\.\..*?\$\(NC\)"
	\$\(PYTHON\) upgrade_lambda_runtime\.py --build-only
	@echo "\$\(BLUE\)Creating ZIP packages\.\.\..*?\$\(NC\)"
	@mkdir -p \.packages
	@\$\(PYTHON\) -c "import yaml.*?for f in funcs\]"
	@echo "\$\(GREEN\) Build and packaging complete\$\(NC\)"'''

new_build = '''build: ## Build all Lambda functions with SAM CLI and create ZIP packages
	@echo "$(BLUE)Building functions...$(NC)"
	$(PYTHON) upgrade_lambda_runtime.py --build-only
	@echo "$(BLUE)Creating ZIP packages...$(NC)"
	$(PYTHON) build_packages.py
	@echo "$(GREEN)[OK] Build and packaging complete$(NC)"'''

# Find and replace the build section more carefully
lines = content.split('\n')
new_lines = []
i = 0
while i < len(lines):
    if lines[i].startswith('build: ## Build all Lambda'):
        # Add the new build section
        new_lines.append('build: ## Build all Lambda functions with SAM CLI and create ZIP packages')
        new_lines.append('\t@echo "$(BLUE)Building functions...$(NC)"')
        new_lines.append('\t$(PYTHON) upgrade_lambda_runtime.py --build-only')
        new_lines.append('\t@echo "$(BLUE)Creating ZIP packages...$(NC)"')
        new_lines.append('\t$(PYTHON) build_packages.py')
        new_lines.append('\t@echo "$(GREEN)[OK] Build and packaging complete$(NC)"')
        
        # Skip the old complex build section
        i += 1
        while i < len(lines) and not lines[i].startswith('compare: ##'):
            i += 1
        i -= 1  # Back up one line so the loop increment doesn't skip compare
    else:
        new_lines.append(lines[i])
    i += 1

# Write back
with open('Makefile', 'w') as f:
    f.write('\n'.join(new_lines))

print("Makefile updated successfully!")
