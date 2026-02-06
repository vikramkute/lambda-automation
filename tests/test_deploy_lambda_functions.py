"""Test suite for deploy_lambda_functions.py"""

import pytest
import yaml
import json
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import sys
import subprocess

sys.path.insert(0, str(Path(__file__).parent.parent))
from deploy_lambda_functions import LambdaDeployer


class TestLambdaDeployerInit:
    """Test LambdaDeployer initialization"""

    @pytest.fixture
    def sample_config(self):
        """Sample configuration"""
        return {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 128, 'timeout': 30, 'enabled': True}
            ],
            'build': {'artifact_dir': '.build', 'test_dir': 'tests'}
        }

    def test_init_with_valid_config(self, tmp_path, sample_config):
        """Test initialization with valid config"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(sample_config))
        
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            deployer = LambdaDeployer(str(config_file))
            assert deployer.config == sample_config

    def test_init_with_missing_config(self):
        """Test initialization with missing config file"""
        with pytest.raises(SystemExit):
            LambdaDeployer("/nonexistent/config.yaml")

    def test_init_with_invalid_yaml(self, tmp_path):
        """Test initialization with invalid YAML"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: content:")
        
        with pytest.raises(SystemExit):
            LambdaDeployer(str(config_file))


class TestValidateLambdaLimits:
    """Test _validate_lambda_limits method"""

    def test_valid_memory_and_timeout(self, tmp_path):
        """Test validation with valid memory and timeout"""
        config = {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 512, 'timeout': 60, 'enabled': True}
            ]
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            deployer = LambdaDeployer(str(config_file))
            assert deployer.config['functions'][0]['memory'] == 512

    def test_invalid_memory_too_low(self, tmp_path):
        """Test validation with memory below minimum"""
        config = {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 64, 'timeout': 30, 'enabled': True}
            ]
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with pytest.raises(SystemExit):
            with patch('pathlib.Path.cwd', return_value=tmp_path):
                LambdaDeployer(str(config_file))

    def test_invalid_memory_too_high(self, tmp_path):
        """Test validation with memory above maximum"""
        config = {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 20000, 'timeout': 30, 'enabled': True}
            ]
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with pytest.raises(SystemExit):
            with patch('pathlib.Path.cwd', return_value=tmp_path):
                LambdaDeployer(str(config_file))

    def test_invalid_timeout_too_low(self, tmp_path):
        """Test validation with timeout below minimum"""
        config = {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 128, 'timeout': 0, 'enabled': True}
            ]
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with pytest.raises(SystemExit):
            with patch('pathlib.Path.cwd', return_value=tmp_path):
                LambdaDeployer(str(config_file))

    def test_invalid_timeout_too_high(self, tmp_path):
        """Test validation with timeout above maximum"""
        config = {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 128, 'timeout': 1000, 'enabled': True}
            ]
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with pytest.raises(SystemExit):
            with patch('pathlib.Path.cwd', return_value=tmp_path):
                LambdaDeployer(str(config_file))


class TestPackageFunction:
    """Test package_function method"""

    @pytest.fixture
    def deployer(self, tmp_path):
        """Create deployer instance"""
        config = {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 128, 'timeout': 30, 'enabled': True}
            ],
            'build': {'artifact_dir': '.build'}
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            return LambdaDeployer(str(config_file))

    def test_package_function_success(self, deployer, tmp_path):
        """Test successful function packaging"""
        func_dir = tmp_path / "func1" / "src"
        func_dir.mkdir(parents=True)
        (func_dir / "lambda_function.py").write_text("def handler(event, context): pass")
        
        func_config = {'name': 'func1', 'path': str(tmp_path / "func1")}
        success, pkg_path = deployer.package_function(func_config)
        
        assert success
        assert Path(pkg_path).exists()
        assert Path(pkg_path).suffix == '.zip'

    def test_package_function_missing_directory(self, deployer, tmp_path):
        """Test packaging with missing function directory"""
        func_config = {'name': 'func1', 'path': str(tmp_path / "nonexistent")}
        success, pkg_path = deployer.package_function(func_config)
        
        assert not success

    def test_package_function_creates_zip(self, deployer, tmp_path):
        """Test that packaging creates valid ZIP file"""
        func_dir = tmp_path / "func1" / "src"
        func_dir.mkdir(parents=True)
        (func_dir / "lambda_function.py").write_text("def handler(event, context): pass")
        
        func_config = {'name': 'func1', 'path': str(tmp_path / "func1")}
        success, pkg_path = deployer.package_function(func_config)
        
        assert success
        with zipfile.ZipFile(pkg_path, 'r') as zf:
            assert 'lambda_function.py' in zf.namelist()


class TestGenerateDeploymentConfig:
    """Test generate_deployment_config method"""

    def test_generate_config_basic(self, tmp_path):
        """Test basic deployment config generation"""
        config = {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 128, 'timeout': 30, 'enabled': True, 'description': 'Test function'}
            ],
            'global': {'aws_region': 'us-east-1'}
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            deployer = LambdaDeployer(str(config_file))
            deployment_config = deployer.generate_deployment_config()
            
            assert 'aws_region' in deployment_config
            assert 'functions' in deployment_config
            assert 'func1' in deployment_config['functions']

    def test_generate_config_filters_disabled_functions(self, tmp_path):
        """Test that disabled functions are excluded"""
        config = {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 128, 'timeout': 30, 'enabled': True},
                {'name': 'func2', 'path': './func2', 'runtime': 'python3.14', 'memory': 128, 'timeout': 30, 'enabled': False}
            ]
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            deployer = LambdaDeployer(str(config_file))
            deployment_config = deployer.generate_deployment_config()
            
            assert 'func1' in deployment_config['functions']
            assert 'func2' not in deployment_config['functions']

    def test_generate_config_filters_aws_env_vars(self, tmp_path):
        """Test that AWS reserved environment variables are filtered"""
        config = {
            'functions': [
                {
                    'name': 'func1', 
                    'path': './func1', 
                    'runtime': 'python3.14', 
                    'memory': 128, 
                    'timeout': 30, 
                    'enabled': True,
                    'environment': {
                        'MY_VAR': 'value',
                        'AWS_SECRET_KEY': 'should_be_filtered'
                    }
                }
            ]
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            deployer = LambdaDeployer(str(config_file))
            deployment_config = deployer.generate_deployment_config()
            
            env_vars = deployment_config['functions']['func1']['environment']
            assert 'MY_VAR' in env_vars
            assert 'AWS_SECRET_KEY' not in env_vars


class TestApplyTerraform:
    """Test apply_terraform method"""

    @pytest.fixture
    def deployer(self, tmp_path):
        """Create deployer instance"""
        config = {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 128, 'timeout': 30, 'enabled': True}
            ]
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            return LambdaDeployer(str(config_file))

    def test_apply_terraform_init_failure(self, deployer):
        """Test terraform apply when init fails"""
        with patch.object(deployer, '_run_command') as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            result = deployer.apply_terraform()
            assert not result

    def test_apply_terraform_plan_failure(self, deployer):
        """Test terraform apply when plan fails"""
        with patch.object(deployer, '_run_command') as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # init success
                MagicMock(returncode=1)   # plan failure
            ]
            result = deployer.apply_terraform()
            assert not result

    def test_apply_terraform_user_cancels(self, deployer):
        """Test terraform apply when user cancels"""
        with patch.object(deployer, '_run_command') as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # init success
                MagicMock(returncode=0, stdout='', stderr='')  # plan success
            ]
            with patch('builtins.input', return_value='no'):
                result = deployer.apply_terraform()
                assert result  # Returns True but doesn't apply


class TestRollbackDeployment:
    """Test rollback_deployment method"""

    @pytest.fixture
    def deployer(self, tmp_path):
        """Create deployer instance"""
        config = {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 128, 'timeout': 30, 'enabled': True}
            ]
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            return LambdaDeployer(str(config_file))

    def test_rollback_with_no_state(self, deployer):
        """Test rollback when no Terraform state exists"""
        with patch.object(deployer, '_run_command') as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout='')
            result = deployer.rollback_deployment()
            assert not result

    def test_rollback_success(self, deployer):
        """Test successful rollback"""
        with patch.object(deployer, '_run_command') as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout='resource1\nresource2'),  # state list
                MagicMock(returncode=0)  # destroy
            ]
            result = deployer.rollback_deployment()
            assert result


class TestCheckExistingFunctions:
    """Test _check_existing_functions method"""

    @pytest.fixture
    def deployer(self, tmp_path):
        """Create deployer instance"""
        config = {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 128, 'timeout': 30, 'enabled': True}
            ]
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            return LambdaDeployer(str(config_file))

    def test_check_existing_functions_found(self, deployer):
        """Test checking when functions exist"""
        with patch('boto3.client') as mock_boto:
            mock_lambda = MagicMock()
            mock_lambda.get_function.return_value = {}
            mock_boto.return_value = mock_lambda
            
            existing, new = deployer._check_existing_functions(['func1'])
            assert 'func1' in existing
            assert len(new) == 0

    def test_check_existing_functions_not_found(self, deployer):
        """Test checking when functions don't exist"""
        from botocore.exceptions import ClientError
        
        with patch('boto3.client') as mock_boto:
            mock_lambda = MagicMock()
            error_response = {'Error': {'Code': 'ResourceNotFoundException'}}
            mock_lambda.get_function.side_effect = ClientError(error_response, 'GetFunction')
            mock_boto.return_value = mock_lambda
            
            existing, new = deployer._check_existing_functions(['func1'])
            assert len(existing) == 0
            assert 'func1' in new


class TestValidateTerraformVars:
    """Test _validate_terraform_vars method"""

    @pytest.fixture
    def deployer(self, tmp_path):
        """Create deployer instance"""
        config = {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 128, 'timeout': 30, 'enabled': True}
            ]
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            return LambdaDeployer(str(config_file))

    def test_validate_valid_function_names(self, deployer):
        """Test validation with valid function names"""
        config = {'func1': {}, 'my-func-2': {}, 'test_func_3': {}}
        assert deployer._validate_terraform_vars(config)

    def test_validate_invalid_function_name(self, deployer):
        """Test validation with invalid function name"""
        config = {'func@invalid': {}}
        with pytest.raises(ValueError, match="Invalid function name"):
            deployer._validate_terraform_vars(config)

    def test_validate_invalid_env_var_name(self, deployer):
        """Test validation with invalid environment variable name"""
        config = {'func1': {'environment': {'123invalid': 'value'}}}
        with pytest.raises(ValueError, match="Invalid environment variable name"):
            deployer._validate_terraform_vars(config)


class TestRunCommand:
    """Test _run_command method"""

    @pytest.fixture
    def deployer(self, tmp_path):
        """Create deployer instance"""
        config = {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 128, 'timeout': 30, 'enabled': True}
            ]
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            return LambdaDeployer(str(config_file))

    def test_run_command_success(self, deployer):
        """Test successful command execution"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = deployer._run_command(['echo', 'test'])
            assert result.returncode == 0

    def test_run_command_failure_with_check(self, deployer):
        """Test command failure with check=True"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            with pytest.raises(subprocess.CalledProcessError):
                deployer._run_command(['false'], check=True)

    def test_run_command_timeout(self, deployer):
        """Test command timeout"""
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('cmd', 1)):
            with pytest.raises(subprocess.TimeoutExpired):
                deployer._run_command(['sleep', '10'], timeout=1)
