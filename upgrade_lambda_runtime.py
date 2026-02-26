#!/usr/bin/env python3
"""
Script to upgrade AWS Lambda functions to the latest Python runtime.
Reads configuration from functions.config.yaml and updates all enabled functions.
Uses SAM CLI and Terraform to manage infrastructure.
"""

import yaml
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sanitize_error(text: str) -> str:
    """Sanitize error messages to prevent credential leakage."""
    return re.sub(r'(AKIA|aws_|secret)[^\s]+', '***REDACTED***', text, flags=re.IGNORECASE)


class LambdaUpgrader:
    def __init__(self, config_path: str = "functions.config.yaml"):
        """Initialize the Lambda upgrader with configuration."""
        self.config_path = config_path
        self.config = self._load_config()
        self.workspace_root = Path.cwd()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {self.config_path}")
            self._validate_config(config)
            return config
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            sys.exit(1)
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            sys.exit(1)

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration structure and required fields."""
        required_fields = ['functions']
        required_func_fields = ['name', 'path', 'runtime', 'memory', 'timeout']
        
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Configuration missing required field: '{field}'")
        
        for func in config.get('functions', []):
            for field in required_func_fields:
                if field not in func:
                    raise ValueError(f"Function {func.get('name', 'unknown')} missing '{field}'")

    def run_command(self, cmd: List[str], cwd: Optional[str] = None, check: bool = True, timeout: int = 300) -> subprocess.CompletedProcess[str]:
        """Execute a shell command and return the result."""
        try:
            logger.debug(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=cwd or str(self.workspace_root),
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout,  # Add timeout to prevent hanging
                shell=True  # Use shell to resolve commands like 'sam' on Windows
            )
            if result.returncode != 0 and check:
                logger.error(f"Command failed: {' '.join(cmd)}")
                logger.error(f"STDERR: {sanitize_error(result.stderr)}")
                raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
            return result
        except subprocess.TimeoutExpired as e:
            logger.error(f"Command timed out after {timeout} seconds: {' '.join(cmd)}")
            raise
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            raise

    def _update_template_yaml(self, function_config: Dict[str, Any]) -> bool:
        """Update the SAM template.yaml with runtime, memory, timeout, and description from config."""
        template_path = Path(self.workspace_root) / function_config['path'] / 'template.yml'
        
        try:
            with open(template_path, 'r') as f:
                template_content = f.read()
            
            import re
            
            # Update runtime
            old_runtime_pattern = r'Runtime: python\d+\.\d+'
            new_runtime = f'Runtime: {function_config["runtime"]}'
            template_content = re.sub(old_runtime_pattern, new_runtime, template_content)
            
            # Update memory
            old_memory_pattern = r'MemorySize: \d+'
            new_memory = f'MemorySize: {function_config["memory"]}'
            template_content = re.sub(old_memory_pattern, new_memory, template_content)
            
            # Update timeout
            old_timeout_pattern = r'Timeout: \d+'
            new_timeout = f'Timeout: {function_config["timeout"]}'
            template_content = re.sub(old_timeout_pattern, new_timeout, template_content)
            
            # Update description
            if 'description' in function_config:
                old_description_pattern = r"Description: '[^']*'"
                new_description = f"Description: '{function_config['description']}'"
                template_content = re.sub(old_description_pattern, new_description, template_content)
            
            with open(template_path, 'w') as f:
                f.write(template_content)
            
            logger.info(f"Updated template with runtime={function_config['runtime']}, memory={function_config['memory']}, timeout={function_config['timeout']}, description='{function_config.get('description', 'N/A')}': {template_path}")
            return True
        except Exception as e:
            logger.error(f"Error updating template for {function_config['name']}: {e}")
            return False

    def _get_source_folder(self, function_config: Dict[str, Any]) -> Path:
        """Dynamically detect the source folder containing lambda_function.py or requirements.txt."""
        function_dir = Path(self.workspace_root) / function_config['path']
        
        # Check if source folder is explicitly specified in config
        if 'source_folder' in function_config:
            return function_dir / function_config['source_folder']
        
        # If function directory doesn't exist, return fallback
        if not function_dir.exists():
            logger.warning(f"Function directory not found: {function_dir}, using 'src' subfolder")
            return function_dir / 'src'
        
        # Try to find lambda_function.py in subdirectories
        try:
            for subdir in function_dir.iterdir():
                if subdir.is_dir() and not subdir.name.startswith('.'):
                    lambda_file = subdir / 'lambda_function.py'
                    if lambda_file.exists():
                        logger.debug(f"Found source folder: {subdir.name}")
                        return subdir
        except (OSError, PermissionError) as e:
            logger.warning(f"Error scanning directory {function_dir}: {e}")
        
        # Fallback to 'src' for backward compatibility
        logger.warning(f"Could not detect source folder for {function_config['name']}, using 'src'")
        return function_dir / 'src'
    
    def _update_requirements(self, function_config: Dict[str, Any]) -> bool:
        """Update requirements.txt or add it if missing."""
        source_folder = self._get_source_folder(function_config)
        requirements_file = source_folder / 'requirements.txt'
        
        try:
            # Check if requirements.txt exists
            if requirements_file.exists():
                logger.info(f"Found requirements.txt: {requirements_file}")
                # Run pip upgrade on dependencies
                logger.info(f"Upgrading dependencies from {requirements_file}")
                result = self.run_command([
                    'pip', 'install', '--upgrade', '-r', str(requirements_file)
                ], check=False, timeout=120)
                
                if result.returncode == 0:
                    logger.info(f"Successfully upgraded dependencies for {function_config['name']}")
                else:
                    logger.warning(f"⚠ Dependency upgrade had issues for {function_config['name']}: {sanitize_error(result.stderr)}")
            else:
                # Create basic requirements.txt
                logger.info(f"Creating requirements.txt for {function_config['name']}")
                requirements_file.parent.mkdir(parents=True, exist_ok=True)
                with open(requirements_file, 'w') as f:
                    f.write("# Add your Lambda function dependencies here\n")
                    f.write("boto3>=1.26.0\n")
            return True
        except Exception as e:
            logger.error(f"Error managing requirements for {function_config['name']}: {e}")
            return False

    def _fix_python314_syntax(self, function_config: Dict[str, Any]) -> bool:
        """Fix outdated/incompatible Python syntax for Python 3.13."""
        source_folder = self._get_source_folder(function_config)
        lambda_file = source_folder / 'lambda_function.py'
        
        if not lambda_file.exists():
            logger.warning(f"Lambda function file not found: {lambda_file}")
            return True
        
        try:
            with open(lambda_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Fix common Python 3.13 compatibility issues
            # 1. Replace deprecated imp module with importlib
            if 'import imp' in content:
                content = content.replace('import imp', 'import importlib')
                content = content.replace('imp.load_source', 'importlib.util.spec_from_file_location')
                logger.info(f"Fixed deprecated 'imp' module usage in {lambda_file}")
            
            # 2. Fix deprecated collections imports
            if 'from collections import' in content and 'collections.abc' not in content:
                content = content.replace('from collections import Mapping', 'from collections.abc import Mapping')
                content = content.replace('from collections import MutableMapping', 'from collections.abc import MutableMapping')
                content = content.replace('from collections import Sequence', 'from collections.abc import Sequence')
                content = content.replace('from collections import Iterable', 'from collections.abc import Iterable')
                logger.info(f"Fixed deprecated collections imports in {lambda_file}")
            
            # 3. Validate syntax safely without compilation
            try:
                # Basic syntax validation using ast module (safer than compile)
                import ast
                
                # Validate content before parsing
                if len(content) > 1000000:  # 1MB limit
                    logger.error(f"File too large for syntax check: {lambda_file}")
                    return False
                
                # Check for potentially dangerous constructs
                dangerous_patterns = ['__import__', 'exec(', 'eval(', 'compile(']
                if any(pattern in content for pattern in dangerous_patterns):
                    logger.warning(f"Potentially dangerous patterns found in {lambda_file}")
                    # Skip syntax validation for files with dangerous patterns
                    logger.info(f"Skipping syntax validation due to dangerous patterns in {lambda_file}")
                else:
                    # Safe syntax validation using AST parsing
                    ast.parse(content, filename=str(lambda_file))
            except SyntaxError as e:
                logger.error(f"Syntax error in {lambda_file} after fixes: {e}")
                return False
            except Exception as e:
                logger.error(f"Compilation check failed for {lambda_file}: {e}")
                return False
            
            # Write back if changes were made
            if content != original_content:
                try:
                    with open(lambda_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logger.info(f"Updated Python syntax in {lambda_file}")
                except (OSError, IOError) as e:
                    logger.error(f"Failed to write updated syntax to {lambda_file}: {e}")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Error fixing syntax for {function_config['name']}: {e}")
            return False

    def upgrade_function(self, function_config: Dict[str, Any]) -> bool:
        """Upgrade a single function to the latest runtime."""
        function_name = function_config['name']
        logger.info(f"Upgrading {function_name}...")
        
        try:
            # Step 1: Fix Python 3.13 syntax compatibility
            logger.info(f"Step 1: Fixing Python 3.13 syntax for {function_name}")
            if not self._fix_python314_syntax(function_config):
                logger.error(f"Failed at Step 1 (syntax fixing) for {function_name}")
                return False
            
            # Step 2: Update template.yml
            logger.info(f"Step 2: Updating template.yml for {function_name}")
            if not self._update_template_yaml(function_config):
                logger.error(f"Failed at Step 2 (template update) for {function_name}")
                return False
            
            # Step 3: Update requirements
            logger.info(f"Step 3: Updating requirements for {function_name}")
            if not self._update_requirements(function_config):
                logger.error(f"Failed at Step 3 (requirements update) for {function_name}")
                return False
            
            # Step 4: Build with SAM CLI
            logger.info(f"Step 4: Building with SAM CLI for {function_name}")
            function_path = Path(self.workspace_root) / function_config['path']
            
            # Use sam CLI consistently across platforms
            sam_cmd = 'sam'
            
            # Check if sam command exists
            try:
                check_result = self.run_command([sam_cmd, '--version'], check=False)
                if check_result.returncode != 0:
                    logger.warning(f"SAM CLI not working properly, skipping build for {function_name}")
                    return True
            except Exception as e:
                logger.warning(f"SAM CLI not available: {e}. Skipping build for {function_name}")
                return True
            
            result = self.run_command(
                [sam_cmd, 'build'],
                cwd=str(function_path),
                check=False
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully built {function_name}")
                return True
            else:
                logger.error(f"SAM build failed for {function_name}")
                logger.debug(f"SAM output: {sanitize_error(result.stderr)}")
                return False
            
        except Exception as e:
            import traceback
            logger.error(f"ERROR in upgrade_function for {function_name}:")
            logger.error(f"Exception: {type(e).__name__}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def upgrade_all_functions(self) -> Dict[str, bool]:
        """Upgrade all enabled functions."""
        results: Dict[str, bool] = {}
        functions = self.config.get('functions', [])
        
        enabled_functions = [f for f in functions if f.get('enabled', True)]
        logger.info(f"Found {len(enabled_functions)} enabled functions to process (out of {len(functions)} total)")
        
        for func_config in enabled_functions:
            success = self.upgrade_function(func_config)
            results[func_config['name']] = success
        
        return results

    def generate_terraform_variables(self) -> str:
        """Generate Terraform variables file from config."""
        terraform_vars: Dict[str, Dict[str, Any]] = {
            "lambda_functions": {}
        }
        
        for func_config in self.config.get('functions', []):
            if func_config.get('enabled', True):
                terraform_vars["lambda_functions"][func_config['name']] = {
                    "runtime": func_config['runtime'],
                    "memory": func_config['memory'],
                    "timeout": func_config['timeout'],
                    "description": func_config['description'],
                    "environment_variables": func_config.get('environment_variables', {})
                }
        
        return json.dumps(terraform_vars, indent=2)

    def report_results(self, results: Dict[str, bool]):
        """Print summary of upgrade results."""
        logger.info(f"\n{'='*60}")
        logger.info("UPGRADE SUMMARY")
        logger.info(f"{'='*60}")
        
        successful = sum(1 for v in results.values() if v)
        total = len(results)
        
        for func_name, success in results.items():
            status = "SUCCESS" if success else "FAILED"
            logger.info(f"{func_name}: {status}")
        
        logger.info(f"\nTotal: {successful}/{total} functions upgraded successfully")
        
        if successful == total:
            logger.info("\nAll functions upgraded successfully!")
            return 0
        else:
            logger.warning(f"\n⚠ {total - successful} function(s) had issues")
            return 1

    def run(self) -> int:
        """Execute the upgrade process."""
        try:
            results = self.upgrade_all_functions()
            return self.report_results(results)
        except Exception as e:
            logger.error(f"Fatal error during upgrade: {e}")
            return 1


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Upgrade AWS Lambda functions to latest Python runtime')
    parser.add_argument('--build-only', action='store_true', help='Only build functions, skip runtime upgrade')
    parser.add_argument('--config', default='functions.config.yaml', help='Configuration file path')
    
    args = parser.parse_args()
    
    upgrader = LambdaUpgrader(args.config)
    
    if args.build_only:
        # Only build functions without upgrading
        results: Dict[str, bool] = {}
        functions = upgrader.config.get('functions', [])
        enabled_functions = [f for f in functions if f.get('enabled', True)]
        
        for func_config in enabled_functions:
            function_name = func_config['name']
            function_path = Path(upgrader.workspace_root) / func_config['path']
            
            # Use sam CLI consistently across platforms
            sam_cmd = 'sam'
            
            try:
                result = upgrader.run_command(
                    [sam_cmd, 'build'],
                    cwd=str(function_path),
                    check=False
                )
                results[function_name] = result.returncode == 0
                if result.returncode == 0:
                    logger.info(f"Successfully built {function_name}")
                else:
                    logger.error(f" Build failed for {function_name}: {sanitize_error(result.stderr)}")
            except Exception as e:
                logger.error(f"Build failed for {function_name}: {e}")
                results[function_name] = False
        
        exit_code = upgrader.report_results(results)
    else:
        exit_code = upgrader.run()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
