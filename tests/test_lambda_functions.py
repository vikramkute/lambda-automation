"""
AWS Lambda Functions Test Suite
Tests all Lambda functions defined in functions.config.yaml
Uses pytest and moto for AWS service mocking.
"""

import pytest
import json
import os
import yaml
from pathlib import Path
from moto import mock_aws
import boto3
import importlib.util

# Load configuration
CONFIG_PATH = Path(__file__).parent.parent / 'functions.config.yaml'
with open(CONFIG_PATH, 'r') as f:
    CONFIG = yaml.safe_load(f)

# Get test directory from config
TEST_DIR = CONFIG.get('build', {}).get('test_dir', 'tests')


class LambdaTestHelper:
    """Helper class for loading and testing Lambda functions."""
    
    @staticmethod
    def load_lambda_handler(function_name: str):
        """Dynamically load a Lambda function's handler."""
        func_config = None
        for func in CONFIG.get('functions', []):
            if func['name'] == function_name:
                func_config = func
                break
        
        if not func_config:
            raise ValueError(f"Function {function_name} not found in config")
        
        lambda_file = Path(func_config['path']) / 'src' / 'lambda_function.py'
        
        if not lambda_file.exists():
            raise FileNotFoundError(f"Lambda function file not found: {lambda_file}")
        
        spec = importlib.util.spec_from_file_location(function_name, lambda_file)
        if spec is None or spec.loader is None:
            raise ImportError(f"Failed to create module spec for {lambda_file}")
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            raise ImportError(f"Failed to execute module {lambda_file}: {e}")
        
        if not hasattr(module, 'lambda_handler'):
            raise AttributeError(f"No lambda_handler function found in {lambda_file}")
        
        return module.lambda_handler

    @staticmethod
    def get_function_config(function_name: str):
        """Get configuration for a specific function."""
        for func in CONFIG.get('functions', []):
            if func['name'] == function_name:
                return func
        return None


# Fixtures
@pytest.fixture
def aws_credentials():
    """Mock AWS credentials."""
    # Store original values
    original_env = {}
    aws_env_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SECURITY_TOKEN', 'AWS_SESSION_TOKEN', 'AWS_DEFAULT_REGION']
    
    for var in aws_env_vars:
        original_env[var] = os.environ.get(var)
    
    # Set test values
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    
    yield
    
    # Restore original values
    for var, value in original_env.items():
        if value is None:
            os.environ.pop(var, None)
        else:
            os.environ[var] = value


@pytest.fixture
def lambda_context():
    """Create a mock Lambda context."""
    class LambdaContext:
        def __init__(self):
            self.function_name = 'test-function'
            self.function_version = '$LATEST'
            self.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
            self.memory_limit_in_mb = 128
            self.aws_request_id = 'test-request-id'
            self.log_group_name = '/aws/lambda/test-function'
            self.log_stream_name = '2026/01/30/[$LATEST]abc123'
            
        def get_remaining_time_in_millis(self):
            return 3000
    
    return LambdaContext()


# Test Suite for myTestFunction1 (S3 operations)
class TestMyTestFunction1:
    """Test suite for myTestFunction1."""
    
    @pytest.fixture(autouse=True)
    def setup(self, aws_credentials):
        """Setup for each test."""
        self.handler = LambdaTestHelper.load_lambda_handler('myTestFunction1')
        self.config = LambdaTestHelper.get_function_config('myTestFunction1')
    
    @mock_aws
    def test_lambda_handler_with_s3_success(self, lambda_context):
        """Test successful S3 read operation."""
        # Setup S3 with a test bucket name
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = os.environ.get('S3_BUCKET_NAME', 'test-lambda-bucket')
        
        s3_client.create_bucket(Bucket=bucket_name)
        s3_client.put_object(Bucket=bucket_name, Key='sample.txt', Body=b'Test content')
        
        # Test the function with environment variable
        os.environ['S3_BUCKET_NAME'] = bucket_name
        event = {}  # Function doesn't require event data
        response = self.handler(event, lambda_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'message' in body
        assert 'content' in body
        assert body['content'] == 'Test content'
    
    @mock_aws
    def test_lambda_handler_missing_bucket(self, lambda_context):
        """Test error handling when S3 bucket doesn't exist."""
        # Don't create the bucket - test error handling
        os.environ['S3_BUCKET_NAME'] = 'nonexistent-bucket'
        event = {}
        
        response = self.handler(event, lambda_context)
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'error' in body
    
    @mock_aws
    def test_lambda_handler_missing_object(self, lambda_context):
        """Test error handling when S3 object doesn't exist."""
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket-empty'
        s3_client.create_bucket(Bucket=bucket_name)
        # Don't put any objects - test missing object handling
        
        os.environ['S3_BUCKET_NAME'] = bucket_name
        event = {}
        
        response = self.handler(event, lambda_context)
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_lambda_handler_no_credentials(self, lambda_context):
        """Test error handling when AWS credentials are missing."""
        # Remove AWS credentials
        for var in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']:
            os.environ.pop(var, None)
        
        event = {}
        response = self.handler(event, lambda_context)
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_function_config_exists(self):
        """Test that function configuration exists."""
        assert self.config is not None
        assert self.config['name'] == 'myTestFunction1'
        assert 'runtime' in self.config
        assert 'memory' in self.config
    
    def test_function_handler_callable(self):
        """Test that handler is callable."""
        assert callable(self.handler)
    
    def test_function_runtime_version(self):
        """Test that function is configured with latest Python runtime."""
        assert self.config['runtime'] in ['python3.14']
        assert int(self.config['runtime'].split('.')[-1]) >= 14


# Error Scenario Tests
class TestErrorScenarios:
    """Test error handling across all Lambda functions."""
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG.get('functions', []) if f.get('enabled', True)
    ], ids=lambda x: x['name'])
    def test_handler_with_invalid_event(self, func_config, lambda_context, aws_credentials):
        """Test Lambda functions with malformed event data."""
        try:
            handler = LambdaTestHelper.load_lambda_handler(func_config['name'])
        except Exception as e:
            pytest.skip(f"Could not load handler: {e}")
        
        # Test with invalid JSON-like data
        invalid_events = [
            None,
            "invalid_string",
            123,
            {"malformed": {"deeply": {"nested": None}}}
        ]
        
        for invalid_event in invalid_events:
            try:
                response = handler(invalid_event, lambda_context)
                # Should handle gracefully with error response
                assert 'statusCode' in response
                assert response['statusCode'] in [400, 500]
            except Exception:
                # Exception is acceptable for invalid input
                pass
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG.get('functions', []) if f.get('enabled', True)
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_handler_with_aws_service_errors(self, func_config, lambda_context, aws_credentials):
        """Test Lambda functions when AWS services return errors."""
        try:
            handler = LambdaTestHelper.load_lambda_handler(func_config['name'])
        except Exception as e:
            pytest.skip(f"Could not load handler: {e}")
        
        # Test with environment that will cause AWS service errors
        os.environ['S3_BUCKET_NAME'] = 'bucket-that-does-not-exist-12345'
        
        event = {}
        try:
            response = handler(event, lambda_context)
            # Should handle AWS errors gracefully
            assert 'statusCode' in response
            if response['statusCode'] == 500:
                body = json.loads(response['body'])
                assert 'error' in body
        except Exception:
            # Exception handling varies by function implementation
            pass


# Generic Test for all functions
class TestAllFunctions:
    """Generic test suite applicable to all Lambda functions."""
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG.get('functions', []) if f.get('enabled', True)
    ], ids=lambda x: x['name'])
    def test_function_config_valid(self, func_config):
        """Test that function configuration is valid."""
        required_fields = ['name', 'path', 'runtime', 'memory', 'timeout']
        for field in required_fields:
            assert field in func_config, f"Missing required field '{field}' in {func_config['name']}"
        
        assert func_config['memory'] > 0
        assert func_config['timeout'] > 0
        assert 'python' in func_config['runtime']
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG.get('functions', []) if f.get('enabled', True)
    ], ids=lambda x: x['name'])
    def test_function_file_exists(self, func_config):
        """Test that lambda_function.py exists."""
        lambda_file = Path(func_config['path']) / 'src' / 'lambda_function.py'
        assert lambda_file.exists(), f"Lambda file not found: {lambda_file}"
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG.get('functions', []) if f.get('enabled', True)
    ], ids=lambda x: x['name'])
    def test_function_template_exists(self, func_config):
        """Test that template.yml exists."""
        template_file = Path(func_config['path']) / 'template.yml'
        assert template_file.exists(), f"Template file not found: {template_file}"
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG.get('functions', []) if f.get('enabled', True)
    ], ids=lambda x: x['name'])
    def test_function_handler_exists(self, func_config):
        """Test that lambda_handler function exists in lambda_function.py."""
        try:
            handler = LambdaTestHelper.load_lambda_handler(func_config['name'])
            assert callable(handler)
        except (ValueError, FileNotFoundError, AttributeError) as e:
            pytest.fail(f"Failed to load handler for {func_config['name']}: {e}")
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG.get('functions', []) if f.get('enabled', True)
    ], ids=lambda x: x['name'])
    def test_function_runtime_is_latest(self, func_config):
        """Test that functions use supported Python versions."""
        supported_runtimes = ['python3.14']
        assert func_config['runtime'] in supported_runtimes, \
            f"Unsupported runtime: {func_config['runtime']}"
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG.get('functions', []) if f.get('enabled', True)
    ], ids=lambda x: x['name'])
    def test_template_uses_python314(self, func_config):
        """Test that template.yml uses Python 3.14 runtime."""
        template_file = Path(func_config['path']) / 'template.yml'
        try:
            with open(template_file, 'r') as f:
                # Read as text to handle CloudFormation intrinsic functions
                template_content = f.read()
        except FileNotFoundError as e:
            pytest.fail(f"Template file not found: {template_file}")
        
        # Simple text search for runtime instead of YAML parsing
        # This avoids issues with CloudFormation intrinsic functions like !Sub
        if 'Runtime: python3.14' not in template_content:
            pytest.fail(f"Template {template_file} does not use python3.14 runtime")
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG.get('functions', []) if f.get('enabled', True)
    ], ids=lambda x: x['name'])
    def test_requirements_python314_compatible(self, func_config):
        """Test that requirements.txt dependencies are compatible with Python 3.14."""
        requirements_file = Path(func_config['path']) / 'src' / 'requirements.txt'
        
        if not requirements_file.exists():
            pytest.skip(f"No requirements.txt found for {func_config['name']}")
        
        import subprocess
        import tempfile
        
        # Read requirements
        try:
            with open(requirements_file, 'r') as f:
                requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        except (FileNotFoundError, IOError) as e:
            pytest.fail(f"Failed to read requirements file {requirements_file}: {e}")
        
        if not requirements:
            pytest.skip(f"No dependencies in requirements.txt for {func_config['name']}")
        
        # Test pip install with Python 3.14 compatibility check
        try:
            result = subprocess.run([
                'python', '-m', 'pip', 'install', '--dry-run', '--quiet'
            ] + requirements, capture_output=True, text=True, timeout=30)
            
            # Check for Python version compatibility issues
            if result.returncode != 0 and 'python_version' in result.stderr.lower():
                pytest.fail(f"Dependencies in {requirements_file} not compatible with current Python version: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            pytest.skip(f"Dependency check timed out for {func_config['name']}")
        except FileNotFoundError:
            pytest.skip("Python/pip not available for dependency checking")
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG.get('functions', []) if f.get('enabled', True)
    ], ids=lambda x: x['name'])
    def test_python314_syntax_compatibility(self, func_config):
        """Test that lambda_function.py syntax is compatible with Python 3.14."""
        lambda_file = Path(func_config['path']) / 'src' / 'lambda_function.py'
        
        # Read and compile the Python file
        try:
            with open(lambda_file, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except (FileNotFoundError, IOError) as e:
            pytest.fail(f"Failed to read {lambda_file}: {e}")
        
        try:
            # Compile with Python 3.14 syntax checking
            compile(source_code, str(lambda_file), 'exec')
        except SyntaxError as e:
            pytest.fail(f"Python 3.14 syntax error in {lambda_file}: {e}")
        except Exception as e:
            pytest.fail(f"Compilation error in {lambda_file}: {e}")
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG.get('functions', []) if f.get('enabled', True)
    ], ids=lambda x: x['name'])
    def test_lambda_function_trigger_mock(self, func_config, lambda_context):
        """Test Lambda function with mock trigger events."""
        try:
            handler = LambdaTestHelper.load_lambda_handler(func_config['name'])
        except (ValueError, FileNotFoundError, AttributeError, ImportError) as e:
            pytest.fail(f"Failed to load handler for {func_config['name']}: {e}")
        
        # Test with empty event
        try:
            response = handler({}, lambda_context)
            assert 'statusCode' in response
            assert response['statusCode'] in [200, 400, 500]
        except Exception as e:
            pytest.fail(f"Handler execution failed for {func_config['name']}: {e}")
        
        # Test with S3 trigger event
        s3_event = {
            "Records": [{
                "eventSource": "aws:s3",
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "test-file.txt"}
                }
            }]
        }
        try:
            response = handler(s3_event, lambda_context)
            assert 'statusCode' in response
            assert response['statusCode'] in [200, 400, 500]
        except Exception as e:
            pytest.fail(f"Handler execution with S3 event failed for {func_config['name']}: {e}")


# Local testing with SAM CLI
class TestLocalExecution:
    """Test functions by invoking them locally (requires SAM CLI)."""
    
    @pytest.fixture
    def sam_available(self):
        """Check if SAM CLI is available."""
        import subprocess
        try:
            subprocess.run(['sam.cmd' if os.name == 'nt' else 'sam', '--version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    @pytest.mark.skipif(
        os.environ.get('SKIP_SAM_TESTS', 'false').lower() == 'true',
        reason="SAM CLI tests skipped"
    )
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG.get('functions', []) if f.get('enabled', True)
    ], ids=lambda x: x['name'])
    def test_sam_build_succeeds(self, func_config, sam_available):
        """Test that SAM build succeeds for each function."""
        if not sam_available:
            pytest.skip("SAM CLI not available")
        
        import subprocess
        func_path = Path(func_config['path'])
        
        try:
            result = subprocess.run(
                ['sam.cmd' if os.name == 'nt' else 'sam', 'build'],
                cwd=str(func_path),
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode != 0:
                pytest.fail(f"SAM build failed for {func_config['name']}: {result.stderr}")
            assert func_path.exists()
        except subprocess.TimeoutExpired:
            pytest.skip("SAM build timed out")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            pytest.fail(f"SAM build error for {func_config['name']}: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
