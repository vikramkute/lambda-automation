#!/usr/bin/env python3
"""
AWS Lambda Function Deployment Script
Packages, tests, and deploys Lambda functions using SAM CLI and Terraform.
Configuration-driven to support multiple functions.
"""

import yaml
import json
import subprocess
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple
import logging
from datetime import datetime, timezone
import shutil
import re
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LambdaDeployer:
    def __init__(self, config_path: str = "functions.config.yaml"):
        """Initialize the Lambda deployer."""
        self.config_path = config_path
        self.config = self._load_config()
        self.workspace_root = Path.cwd()
        self.build_dir = Path(self.config.get('build', {}).get('artifact_dir', '.build'))
        self.timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {self.config_path}")
            self._validate_lambda_limits(config)
            self._warn_disabled_functions(config)
            return config
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            sys.exit(1)
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            sys.exit(1)
        except ValueError as e:
            logger.error(f"Configuration validation error: {e}")
            sys.exit(1)

    def _warn_disabled_functions(self, config: Dict[str, Any]) -> None:
        """Warn about disabled functions to prevent configuration mistakes."""
        disabled_funcs = [f['name'] for f in config.get('functions', []) 
                          if not f.get('enabled', True)]
        if disabled_funcs:
            logger.warning(f"Skipped disabled functions: {', '.join(disabled_funcs)}")

    def _validate_lambda_limits(self, config: Dict[str, Any]) -> None:
        """Validate Lambda resource limits to prevent Terraform failures."""
        for func in config.get('functions', []):
            memory = func.get('memory', 128)
            timeout = func.get('timeout', 30)
            
            if not 128 <= memory <= 10240:
                raise ValueError(f"Memory out of range for {func['name']}: {memory} (must be 128-10240 MB)")
            if not 1 <= timeout <= 900:
                raise ValueError(f"Timeout out of range for {func['name']}: {timeout} (must be 1-900 seconds)")

    def _run_command(self, cmd: List[str], cwd: str = None, 
                     check: bool = True, capture: bool = False, timeout: int = 600) -> subprocess.CompletedProcess:
        """Execute a shell command."""
        try:
            logger.debug(f"Running: {' '.join(cmd)}")
            kwargs = {
                'cwd': cwd or str(self.workspace_root),
                'check': False,
                'timeout': timeout,  # Add timeout to prevent hanging
            }
            if capture:
                kwargs['capture_output'] = True
                kwargs['text'] = True
            
            result = subprocess.run(cmd, **kwargs)
            
            if result.returncode != 0 and check:
                logger.error(f"Command failed with exit code {result.returncode}")
                if capture and result.stderr:
                    logger.error(f"STDERR: {result.stderr}")
                raise subprocess.CalledProcessError(
                    result.returncode, cmd, result.stdout if capture else None
                )
            return result
        except subprocess.TimeoutExpired as e:
            logger.error(f"Command timed out after {timeout} seconds: {' '.join(cmd)}")
            raise
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            raise



    def package_function(self, function_config: Dict[str, Any]) -> Tuple[bool, str]:
        """Package a Lambda function into a ZIP file."""
        func_name = function_config['name']
        logger.info(f"Packaging {func_name}...")
        
        try:
            package_dir = self.workspace_root / '.packages'
            package_dir.mkdir(parents=True, exist_ok=True)
            zip_path = package_dir / f"{func_name}.zip"
            
            # Validate and resolve function path to prevent path traversal
            func_path = Path(function_config['path']).resolve()
            if not func_path.is_relative_to(self.workspace_root.resolve()):
                raise ValueError(f"Function path {func_path} is outside workspace root")
            
            func_src = func_path / 'src'
            if not func_src.exists():
                func_src = func_path
            
            # Validate all paths to prevent path traversal
            base = self.workspace_root.resolve()
            for file_path in [func_path, func_src]:
                if not file_path.resolve().is_relative_to(base):
                    raise ValueError(f"Path escapes workspace: {file_path}")
            
            shutil.make_archive(str(zip_path.with_suffix('')), 'zip', str(func_src))
            logger.info(f"Created package {func_name} from {func_src} to {zip_path}")
            return True, str(zip_path)
        except (OSError, ValueError, shutil.Error) as e:
            logger.error(f"Failed to package {func_name}: {e}")
            return False, ""

    def _validate_terraform_vars(self, config: Dict[str, Any]) -> bool:
        """Validate Terraform variables to prevent injection attacks."""
        for func_name in config.keys():
            if not re.match(r'^[a-zA-Z0-9_-]+$', func_name):
                raise ValueError(f"Invalid function name: {func_name}")
            
            # Validate environment variable names
            env_vars = config[func_name].get('environment', {})
            for env_name in env_vars.keys():
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', env_name):
                    raise ValueError(f"Invalid environment variable name: {env_name}")
        return True

    def generate_deployment_config(self) -> Dict[str, Any]:
        """Generate configuration for Terraform deployment."""
        # Get AWS region from config or environment or use default
        aws_region = (
            self.config.get('global', {}).get('aws_region') or 
            os.environ.get('AWS_DEFAULT_REGION') or 
            os.environ.get('AWS_REGION') or 
            'us-east-1'
        )
        
        deployment_config = {
            'aws_region': aws_region,
            'functions': {}
        }
        
        for func_config in self.config.get('functions', []):
            if func_config.get('enabled', True):
                # Get environment variables and filter out AWS reserved keys
                env_vars = func_config.get('environment', {})
                # Remove any AWS reserved environment variables
                filtered_env_vars = {
                    k: v for k, v in env_vars.items() 
                    if not k.startswith('AWS_') or k in ['AWS_LAMBDA_FUNCTION_TIMEOUT']
                }
                
                func_deployment = {
                    'runtime': func_config['runtime'],
                    'memory': func_config['memory'],
                    'timeout': func_config['timeout'],
                    'environment': filtered_env_vars,
                    'description': func_config.get('description', '')
                }
                
                # Add S3 trigger configuration if present
                if 's3_trigger' in func_config:
                    func_deployment['s3_trigger'] = func_config['s3_trigger']
                
                # Add API Gateway configuration if present
                if 'api_gateway' in func_config:
                    api_config = func_config['api_gateway']
                    func_deployment['api_gateway_enabled'] = api_config.get('enabled', False)
                    func_deployment['api_gateway_http_method'] = api_config.get('http_method', 'POST')
                
                deployment_config['functions'][func_config['name']] = func_deployment
        
        return deployment_config

    def rollback_deployment(self) -> bool:
        """Rollback to previous Terraform state."""
        logger.info("Rolling back deployment...")
        
        try:
            # Check if there's a previous state to rollback to
            result = self._run_command(
                ['terraform', 'state', 'list'],
                check=False,
                capture=True,
                timeout=60
            )
            
            if result.returncode != 0 or not result.stdout.strip():
                logger.error("No Terraform state found to rollback")
                return False
            
            # Perform rollback by destroying current resources
            logger.info("Destroying current deployment...")
            destroy_result = self._run_command(
                ['terraform', 'destroy', '-auto-approve'],
                check=False,
                timeout=600
            )
            
            if destroy_result.returncode == 0:
                logger.info("Rollback completed successfully")
                return True
            else:
                logger.error("Rollback failed")
                return False
                
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def _cleanup_successful_deployment(self) -> None:
        """Clean up build artifacts after successful deployment."""
        logger.info("Cleaning up build artifacts...")
        
        cleanup_paths = [
            self.workspace_root / '.packages',
            self.workspace_root / '.build'
        ]
        
        for path in cleanup_paths:
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                    logger.debug(f"Removed directory: {path}")
            except (OSError, PermissionError) as e:
                logger.warning(f"Failed to remove {path}: {e}")
        
        logger.info("Build artifact cleanup completed")

    def _cleanup_failed_deployment(self) -> None:
        """Clean up artifacts after deployment failure."""
        logger.info("Cleaning up failed deployment artifacts...")
        
        cleanup_paths = [
            self.workspace_root / '.packages',
            self.workspace_root / 'terraform.tfvars.json',
            self.workspace_root / 'tfplan'
        ]
        
        for path in cleanup_paths:
            try:
                if path.is_file():
                    path.unlink()
                    logger.debug(f"Removed file: {path}")
                elif path.is_dir():
                    shutil.rmtree(path)
                    logger.debug(f"Removed directory: {path}")
            except (OSError, PermissionError) as e:
                logger.warning(f"Failed to remove {path}: {e}")
        
        logger.info("Cleanup completed")

    def _check_existing_functions(self, functions_to_deploy: List[str]) -> Tuple[List[str], List[str]]:
        """Check which Lambda functions already exist in AWS."""
        try:
            lambda_client = boto3.client('lambda')
            existing_functions = []
            new_functions = []
            
            for func_name in functions_to_deploy:
                try:
                    lambda_client.get_function(FunctionName=func_name)
                    existing_functions.append(func_name)
                    logger.info(f"Function {func_name} already exists - skipping deployment")
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ResourceNotFoundException':
                        new_functions.append(func_name)
                    else:
                        logger.warning(f"Error checking function {func_name}: {e}")
                        new_functions.append(func_name)  # Deploy anyway if unsure
            
            return existing_functions, new_functions
        except (NoCredentialsError, ClientError) as e:
            logger.warning(f"Could not check existing functions: {e}")
            return [], functions_to_deploy  # Deploy all if can't check

    def apply_terraform(self) -> bool:
        """Apply Terraform configuration for deployment."""
        logger.info("\n" + "="*60)
        logger.info("APPLYING TERRAFORM CONFIGURATION")
        logger.info("="*60)
        
        try:
            # Generate terraform variables
            deployment_config = self.generate_deployment_config()
            
            # Validate Terraform variables before writing
            self._validate_terraform_vars(deployment_config['functions'])
            
            tfvars_path = self.workspace_root / 'terraform.tfvars.json'
            
            with open(tfvars_path, 'w') as f:
                try:
                    # Generate tfvars from config to ensure single source of truth
                    tfvars_data = {
                        'lambda_functions': deployment_config['functions'],
                        'aws_region': deployment_config['aws_region']
                    }
                    json.dump(tfvars_data, f, indent=2)
                    logger.info(f"Generated tfvars with {len(deployment_config['functions'])} functions")
                except (IOError, OSError) as e:
                    raise RuntimeError(f"Failed to write Terraform variables file: {e}")
                except (TypeError, ValueError) as e:
                    raise RuntimeError(f"Failed to serialize Terraform variables: {e}")
            
            logger.info(f"Generated Terraform variables: {tfvars_path}")
            
            # Initialize Terraform
            logger.info("Initializing Terraform...")
            init_result = self._run_command(['terraform', 'init'], check=False, timeout=300)
            if init_result.returncode != 0:
                logger.error("Terraform init failed")
                return False
            
            # Plan deployment
            logger.info("Planning Terraform changes...")
            result = self._run_command(
                ['terraform', 'plan', '-out=tfplan'],
                check=False,
                capture=True,
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info("Terraform plan successful")
                
                # Apply changes
                try:
                    apply_input = input("\nDo you want to apply these Terraform changes? (yes/no): ")
                except (EOFError, KeyboardInterrupt):
                    logger.info("\nUser cancelled operation")
                    return False
                
                if apply_input.strip().lower() not in ('yes', 'y'):
                    logger.info("Terraform apply skipped")
                    return True
                
                logger.info("Applying Terraform configuration...")
                apply_result = self._run_command(['terraform', 'apply', 'tfplan'], check=False, timeout=600)
                if apply_result.returncode == 0:
                    logger.info("Terraform applied successfully")
                    return True
                else:
                    logger.error("Terraform apply failed")
                    return False
            else:
                logger.error("Terraform plan failed")
                return False
        except (RuntimeError, subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Terraform deployment failed: {e}")
            return False

    def deploy(self) -> int:
        """Execute the complete deployment pipeline."""
        try:
            logger.info(f"Starting Lambda deployment pipeline at {self.timestamp}")
            
            # Step 1: Build and package functions
            logger.info("\n" + "="*60)
            logger.info("BUILDING AND PACKAGING FUNCTIONS")
            logger.info("="*60)
            
            build_results = {}
            for func_config in self.config.get('functions', []):
                if func_config.get('enabled', True):
                    success, pkg_path = self.package_function(func_config)
                    build_results[func_config['name']] = {
                        'packaged': success,
                        'package_path': pkg_path
                    }
            
            # Validate all functions packaged successfully
            failed_packages = [name for name, result in build_results.items() if not result['packaged']]
            if failed_packages:
                logger.error(f"Packaging failed for functions: {', '.join(failed_packages)}")
                self._cleanup_failed_deployment()
                return 1
            
            # Validate package files exist and are valid before Terraform
            missing_packages = [name for name, result in build_results.items() 
                              if result['packaged'] and not Path(result['package_path']).exists()]
            if missing_packages:
                logger.error(f"Package files missing for functions: {', '.join(missing_packages)}")
                self._cleanup_failed_deployment()
                return 1
            
            # Validate package files are not empty
            empty_packages = [name for name, result in build_results.items() 
                            if result['packaged'] and Path(result['package_path']).stat().st_size == 0]
            if empty_packages:
                logger.error(f"Empty package files for functions: {', '.join(empty_packages)}")
                self._cleanup_failed_deployment()
                return 1
            
            # Validate package files are valid ZIP archives
            import zipfile
            invalid_packages = []
            for name, result in build_results.items():
                if result['packaged']:
                    try:
                        with zipfile.ZipFile(result['package_path'], 'r') as zf:
                            zf.testzip()
                    except (zipfile.BadZipFile, OSError):
                        invalid_packages.append(name)
            if invalid_packages:
                logger.error(f"Invalid ZIP packages for functions: {', '.join(invalid_packages)}")
                self._cleanup_failed_deployment()
                return 1
            
            # Check existing functions before deployment
            functions_to_deploy = list(build_results.keys())
            existing_functions, new_functions = self._check_existing_functions(functions_to_deploy)
            
            # Add deployment status to build_results
            for func_name in build_results:
                if func_name in existing_functions:
                    build_results[func_name]['deployment_status'] = 'skipped'
                else:
                    build_results[func_name]['deployment_status'] = 'deployed'
            
            if existing_functions:
                logger.info(f"Skipping {len(existing_functions)} existing functions: {', '.join(existing_functions)}")
            
            if not new_functions:
                logger.info("All functions already exist - no deployment needed")
                self._cleanup_successful_deployment()
                self._print_deployment_summary(build_results)
                return 0
            
            logger.info(f"Deploying {len(new_functions)} new functions: {', '.join(new_functions)}")
            
            # Step 2: Apply Terraform
            terraform_success = self.apply_terraform()
            if not terraform_success:
                self._cleanup_failed_deployment()
                return 1
            
            # Step 3: Clean up build artifacts after successful deployment
            self._cleanup_successful_deployment()
            
            # Print summary
            self._print_deployment_summary(build_results)
            
            return 0
        except (RuntimeError, subprocess.CalledProcessError, KeyError) as e:
            logger.error(f"Deployment failed: {e}")
            self._cleanup_failed_deployment()
            return 1

    def _print_deployment_summary(self, results: Dict[str, Any]):
        """Print deployment summary."""
        logger.info("\n" + "="*60)
        logger.info("DEPLOYMENT SUMMARY")
        logger.info("="*60)
        
        for func_name, result in results.items():
            pkg_status = "Pass" if result['packaged'] else "Failed"
            deploy_status = result.get('deployment_status', 'unknown')
            logger.info(f"{func_name}: Package {pkg_status}, Deployment {deploy_status}")
            if result['package_path']:
                logger.info(f"  Package: {result['package_path']}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Deploy AWS Lambda functions using SAM CLI and Terraform'
    )

    parser.add_argument('--config', default='functions.config.yaml', help='Configuration file path')
    parser.add_argument('--rollback', action='store_true', help='Rollback previous deployment')
    
    args = parser.parse_args()
    
    try:
        deployer = LambdaDeployer(args.config)
        
        if args.rollback:
            success = deployer.rollback_deployment()
            exit_code = 0 if success else 1
        else:
            exit_code = deployer.deploy()
            
    except (yaml.YAMLError, FileNotFoundError, ValueError, RuntimeError, KeyboardInterrupt) as e:
        logger.error(f"Fatal error: {e}")
        exit_code = 1
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
