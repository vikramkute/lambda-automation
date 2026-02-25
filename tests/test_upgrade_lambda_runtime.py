"""Test suite for upgrade_lambda_runtime.py"""

import pytest
import yaml
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import sys
import subprocess

sys.path.insert(0, str(Path(__file__).parent.parent))
from upgrade_lambda_runtime import LambdaUpgrader, sanitize_error


class TestSanitizeError:
    """Test sanitize_error function"""

    def test_sanitize_aws_access_key(self):
        """Test sanitizing AWS access keys"""
        text = "Error: AKIAIOSFODNN7EXAMPLE failed"
        result = sanitize_error(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert "***REDACTED***" in result

    def test_sanitize_aws_secret(self):
        """Test sanitizing AWS secrets"""
        text = "aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        result = sanitize_error(text)
        assert "wJalrXUtnFEMI" not in result
        assert "***REDACTED***" in result

    def test_sanitize_no_credentials(self):
        """Test text without credentials remains unchanged"""
        text = "Normal error message"
        result = sanitize_error(text)
        assert result == text


class TestLambdaUpgraderInit:
    """Test LambdaUpgrader initialization"""

    @pytest.fixture
    def sample_config(self):
        """Sample configuration"""
        return {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.12', 'memory': 128, 'timeout': 30, 'enabled': True}
            ]
        }

    def test_init_with_valid_config(self, tmp_path, sample_config):
        """Test initialization with valid config"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(sample_config))
        
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            upgrader = LambdaUpgrader(str(config_file))
            assert upgrader.config == sample_config

    def test_init_with_missing_config(self):
        """Test initialization with missing config file"""
        with pytest.raises(SystemExit):
            LambdaUpgrader("/nonexistent/config.yaml")

    def test_init_with_invalid_yaml(self, tmp_path):
        """Test initialization with invalid YAML"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: content:")
        
        with pytest.raises(SystemExit):
            LambdaUpgrader(str(config_file))


class TestValidateConfig:
    """Test _validate_config method"""

    def test_validate_missing_functions_field(self, tmp_path):
        """Test validation with missing functions field"""
        config = {}
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with pytest.raises((SystemExit, ValueError)):
            LambdaUpgrader(str(config_file))

    def test_validate_missing_function_fields(self, tmp_path):
        """Test validation with missing required function fields"""
        config = {
            'functions': [
                {'name': 'func1'}  # Missing required fields
            ]
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with pytest.raises((SystemExit, ValueError)):
            LambdaUpgrader(str(config_file))

    def test_validate_valid_config(self, tmp_path):
        """Test validation with valid config"""
        config = {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 128, 'timeout': 30}
            ]
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            upgrader = LambdaUpgrader(str(config_file))
            assert upgrader.config == config


class TestUpdateTemplateYaml:
    """Test _update_template_yaml method"""

    @pytest.fixture
    def upgrader(self, tmp_path):
        """Create upgrader instance"""
        config = {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 256, 'timeout': 60, 'description': 'Test function'}
            ]
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            return LambdaUpgrader(str(config_file))

    def test_update_template_runtime(self, upgrader, tmp_path):
        """Test updating template runtime"""
        func_dir = tmp_path / "func1"
        func_dir.mkdir()
        template = func_dir / "template.yml"
        template.write_text("Runtime: python3.12\nMemorySize: 128\nTimeout: 30\nDescription: 'Old'")
        
        func_config = {
            'name': 'func1',
            'path': str(func_dir),
            'runtime': 'python3.14',
            'memory': 256,
            'timeout': 60,
            'description': 'Test function'
        }
        
        result = upgrader._update_template_yaml(func_config)
        assert result
        
        content = template.read_text()
        assert 'python3.14' in content
        assert '256' in content
        assert '60' in content

    def test_update_template_missing_file(self, upgrader, tmp_path):
        """Test updating non-existent template"""
        func_config = {
            'name': 'func1',
            'path': str(tmp_path / "nonexistent"),
            'runtime': 'python3.14',
            'memory': 128,
            'timeout': 30
        }
        
        result = upgrader._update_template_yaml(func_config)
        assert not result


class TestUpdateRequirements:
    """Test _update_requirements method"""

    @pytest.fixture
    def upgrader(self, tmp_path):
        """Create upgrader instance"""
        config = {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 128, 'timeout': 30}
            ]
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            return LambdaUpgrader(str(config_file))

    def test_update_existing_requirements(self, upgrader, tmp_path):
        """Test updating existing requirements.txt"""
        func_dir = tmp_path / "func1" / "src"
        func_dir.mkdir(parents=True)
        req_file = func_dir / "requirements.txt"
        req_file.write_text("boto3==1.20.0\n")
        
        func_config = {'name': 'func1', 'path': str(tmp_path / "func1")}
        
        with patch.object(upgrader, '_run_command') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = upgrader._update_requirements(func_config)
            assert result

    def test_create_missing_requirements(self, upgrader, tmp_path):
        """Test creating requirements.txt when missing"""
        func_dir = tmp_path / "func1" / "src"
        func_dir.mkdir(parents=True)
        
        func_config = {'name': 'func1', 'path': str(tmp_path / "func1")}
        result = upgrader._update_requirements(func_config)
        
        assert result
        req_file = func_dir / "requirements.txt"
        assert req_file.exists()


class TestFixPython314Syntax:
    """Test _fix_python314_syntax method"""

    @pytest.fixture
    def upgrader(self, tmp_path):
        """Create upgrader instance"""
        config = {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 128, 'timeout': 30}
            ]
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            return LambdaUpgrader(str(config_file))

    def test_fix_deprecated_imp_module(self, upgrader, tmp_path):
        """Test fixing deprecated imp module"""
        func_dir = tmp_path / "func1" / "src"
        func_dir.mkdir(parents=True)
        lambda_file = func_dir / "lambda_function.py"
        lambda_file.write_text("import imp\ndef handler(event, context): pass")
        
        func_config = {'name': 'func1', 'path': str(tmp_path / "func1")}
        result = upgrader._fix_python314_syntax(func_config)
        
        assert result
        content = lambda_file.read_text()
        assert 'importlib' in content

    def test_fix_deprecated_collections(self, upgrader, tmp_path):
        """Test fixing deprecated collections imports"""
        func_dir = tmp_path / "func1" / "src"
        func_dir.mkdir(parents=True)
        lambda_file = func_dir / "lambda_function.py"
        lambda_file.write_text("from collections import Mapping\ndef handler(event, context): pass")
        
        func_config = {'name': 'func1', 'path': str(tmp_path / "func1")}
        result = upgrader._fix_python314_syntax(func_config)
        
        assert result
        content = lambda_file.read_text()
        assert 'from collections.abc import Mapping' in content

    def test_fix_syntax_with_valid_code(self, upgrader, tmp_path):
        """Test syntax fixing with already valid code"""
        func_dir = tmp_path / "func1" / "src"
        func_dir.mkdir(parents=True)
        lambda_file = func_dir / "lambda_function.py"
        lambda_file.write_text("def handler(event, context):\n    return {'statusCode': 200}")
        
        func_config = {'name': 'func1', 'path': str(tmp_path / "func1")}
        result = upgrader._fix_python314_syntax(func_config)
        
        assert result

    def test_fix_syntax_with_invalid_code(self, upgrader, tmp_path):
        """Test syntax fixing with invalid Python code"""
        func_dir = tmp_path / "func1" / "src"
        func_dir.mkdir(parents=True)
        lambda_file = func_dir / "lambda_function.py"
        lambda_file.write_text("def handler(event, context\n    return")  # Invalid syntax
        
        func_config = {'name': 'func1', 'path': str(tmp_path / "func1")}
        result = upgrader._fix_python314_syntax(func_config)
        
        assert not result

    def test_fix_syntax_missing_file(self, upgrader, tmp_path):
        """Test syntax fixing with missing lambda file"""
        func_config = {'name': 'func1', 'path': str(tmp_path / "func1")}
        result = upgrader._fix_python314_syntax(func_config)
        
        assert result  # Returns True when file doesn't exist


class TestUpgradeFunction:
    """Test upgrade_function method"""

    @pytest.fixture
    def upgrader(self, tmp_path):
        """Create upgrader instance"""
        config = {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 128, 'timeout': 30, 'description': 'Test'}
            ]
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            return LambdaUpgrader(str(config_file))

    def test_upgrade_function_success(self, upgrader, tmp_path):
        """Test successful function upgrade"""
        func_dir = tmp_path / "func1"
        func_dir.mkdir()
        (func_dir / "src").mkdir()
        (func_dir / "src" / "lambda_function.py").write_text("def handler(event, context): pass")
        (func_dir / "template.yml").write_text("Runtime: python3.12\nMemorySize: 128\nTimeout: 30\nDescription: 'Test'")
        
        func_config = {
            'name': 'func1',
            'path': str(func_dir),
            'runtime': 'python3.14',
            'memory': 128,
            'timeout': 30,
            'description': 'Test'
        }
        
        with patch.object(upgrader, '_run_command') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = upgrader.upgrade_function(func_config)
            assert result

    def test_upgrade_function_syntax_fix_failure(self, upgrader, tmp_path):
        """Test upgrade when syntax fixing fails"""
        func_dir = tmp_path / "func1"
        func_dir.mkdir()
        (func_dir / "src").mkdir()
        (func_dir / "src" / "lambda_function.py").write_text("invalid syntax")
        
        func_config = {
            'name': 'func1',
            'path': str(func_dir),
            'runtime': 'python3.14',
            'memory': 128,
            'timeout': 30
        }
        
        result = upgrader.upgrade_function(func_config)
        assert not result

    def test_upgrade_function_sam_not_available(self, upgrader, tmp_path):
        """Test upgrade when SAM CLI is not available"""
        func_dir = tmp_path / "func1"
        func_dir.mkdir()
        (func_dir / "src").mkdir()
        (func_dir / "src" / "lambda_function.py").write_text("def handler(event, context): pass")
        (func_dir / "template.yml").write_text("Runtime: python3.12\nMemorySize: 128\nTimeout: 30\nDescription: 'Test'")
        
        func_config = {
            'name': 'func1',
            'path': str(func_dir),
            'runtime': 'python3.14',
            'memory': 128,
            'timeout': 30,
            'description': 'Test'
        }
        
        with patch.object(upgrader, '_run_command') as mock_run:
            mock_run.side_effect = FileNotFoundError("SAM not found")
            result = upgrader.upgrade_function(func_config)
            assert result  # Should return True and skip SAM build


class TestUpgradeAllFunctions:
    """Test upgrade_all_functions method"""

    @pytest.fixture
    def upgrader(self, tmp_path):
        """Create upgrader instance"""
        config = {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 128, 'timeout': 30, 'enabled': True, 'description': 'Test1'},
                {'name': 'func2', 'path': './func2', 'runtime': 'python3.14', 'memory': 128, 'timeout': 30, 'enabled': True, 'description': 'Test2'},
                {'name': 'func3', 'path': './func3', 'runtime': 'python3.14', 'memory': 128, 'timeout': 30, 'enabled': False, 'description': 'Test3'}
            ]
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            return LambdaUpgrader(str(config_file))

    def test_upgrade_all_enabled_functions(self, upgrader):
        """Test upgrading all enabled functions"""
        with patch.object(upgrader, 'upgrade_function') as mock_upgrade:
            mock_upgrade.return_value = True
            results = upgrader.upgrade_all_functions()
            
            assert 'func1' in results
            assert 'func2' in results
            assert 'func3' not in results
            assert mock_upgrade.call_count == 2

    def test_upgrade_all_with_failures(self, upgrader):
        """Test upgrading when some functions fail"""
        with patch.object(upgrader, 'upgrade_function') as mock_upgrade:
            mock_upgrade.side_effect = [True, False]
            results = upgrader.upgrade_all_functions()
            
            assert results['func1'] == True
            assert results['func2'] == False


class TestGenerateTerraformVariables:
    """Test generate_terraform_variables method"""

    def test_generate_terraform_vars(self, tmp_path):
        """Test generating Terraform variables"""
        config = {
            'functions': [
                {
                    'name': 'func1',
                    'path': './func1',
                    'runtime': 'python3.14',
                    'memory': 128,
                    'timeout': 30,
                    'description': 'Test function',
                    'enabled': True,
                    'environment_variables': {'KEY': 'value'}
                }
            ]
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            upgrader = LambdaUpgrader(str(config_file))
            tf_vars = upgrader.generate_terraform_variables()
            
            assert 'lambda_functions' in tf_vars
            assert 'func1' in tf_vars


class TestReportResults:
    """Test report_results method"""

    @pytest.fixture
    def upgrader(self, tmp_path):
        """Create upgrader instance"""
        config = {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 128, 'timeout': 30}
            ]
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            return LambdaUpgrader(str(config_file))

    def test_report_all_success(self, upgrader):
        """Test reporting when all functions succeed"""
        results = {'func1': True, 'func2': True}
        exit_code = upgrader.report_results(results)
        
        assert exit_code == 0

    def test_report_with_failures(self, upgrader):
        """Test reporting when some functions fail"""
        results = {'func1': True, 'func2': False}
        exit_code = upgrader.report_results(results)
        
        assert exit_code == 1


class TestRunCommand:
    """Test _run_command method"""

    @pytest.fixture
    def upgrader(self, tmp_path):
        """Create upgrader instance"""
        config = {
            'functions': [
                {'name': 'func1', 'path': './func1', 'runtime': 'python3.14', 'memory': 128, 'timeout': 30}
            ]
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))
        
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            return LambdaUpgrader(str(config_file))

    def test_run_command_success(self, upgrader):
        """Test successful command execution"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
            result = upgrader._run_command(['echo', 'test'])
            assert result.returncode == 0

    def test_run_command_failure(self, upgrader):
        """Test command failure"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout='', stderr='error')
            with pytest.raises(subprocess.CalledProcessError):
                upgrader._run_command(['false'], check=True)

    def test_run_command_timeout(self, upgrader):
        """Test command timeout"""
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('cmd', 1)):
            with pytest.raises(subprocess.TimeoutExpired):
                upgrader._run_command(['sleep', '10'], timeout=1)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
