"""
S3 Trigger Lambda Functions Test Suite
Comprehensive tests for Lambda functions with S3 trigger, processing, and storage.
Reusable test cases for any function with similar functionality.
"""

import pytest
import json
import os
from pathlib import Path
from moto import mock_aws
import boto3
import yaml
import importlib.util

CONFIG_PATH = Path(__file__).parent.parent / 'functions.config.yaml'
MOCK_DATA_DIR = Path(__file__).parent / 'mock_data'

with open(CONFIG_PATH, 'r') as f:
    CONFIG = yaml.safe_load(f)


class S3TriggerTestHelper:
    """Helper for S3 trigger Lambda function testing."""

    @staticmethod
    def get_source_folder(func_config: dict) -> Path:
        """Return the source folder path for a function, defaulting to 'src'."""
        src_folder = func_config.get('src_folder') or func_config.get('source_folder') or 'src'
        return Path(func_config['path']) / src_folder
    
    @staticmethod
    def load_handler(function_name):
        """Load Lambda handler dynamically."""
        func_config = next((f for f in CONFIG['functions'] if f['name'] == function_name), None)
        if not func_config:
            raise ValueError(f"Function {function_name} not found")
        
        lambda_file = S3TriggerTestHelper.get_source_folder(func_config) / 'lambda_function.py'
        spec = importlib.util.spec_from_file_location(function_name, lambda_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.lambda_handler, func_config
    
    @staticmethod
    def create_s3_event(bucket, key, event_name='ObjectCreated:Put'):
        """Create mock S3 trigger event."""
        return {
            'Records': [{
                'eventVersion': '2.1',
                'eventSource': 'aws:s3',
                'eventName': event_name,
                's3': {
                    'bucket': {'name': bucket},
                    'object': {'key': key, 'size': 1024}
                }
            }]
        }
    
    @staticmethod
    def load_mock_files():
        """Load mock files from mock_data directory."""
        mock_files = {}
        for file_path in MOCK_DATA_DIR.glob('*'):
            if file_path.is_file() and file_path.name != 'README.md':
                with open(file_path, 'rb') as f:
                    mock_files[file_path.name] = f.read()
        return mock_files


@pytest.fixture
def lambda_context():
    """Mock Lambda context."""
    class Context:
        function_name = 'test-function'
        memory_limit_in_mb = 128
        aws_request_id = 'test-request-id'
        def get_remaining_time_in_millis(self): return 30000
    return Context()


@pytest.fixture(autouse=True)
def clean_environment():
    """Clean environment variables before and after each test."""
    original_env = os.environ.get('S3_DESTINATION_BUCKET_NAME')
    yield
    if original_env is None:
        os.environ.pop('S3_DESTINATION_BUCKET_NAME', None)
    else:
        os.environ['S3_DESTINATION_BUCKET_NAME'] = original_env


@pytest.fixture
def s3_setup():
    """Setup S3 buckets and mock files."""
    with mock_aws():
        s3 = boto3.client('s3', region_name='us-east-1')
        source_bucket = 'test-source-bucket'
        dest_bucket = 'test-dest-bucket'
        
        s3.create_bucket(Bucket=source_bucket)
        s3.create_bucket(Bucket=dest_bucket)
        
        # Upload mock files from mock_data directory
        mock_files = S3TriggerTestHelper.load_mock_files()
        for filename, content in mock_files.items():
            s3.put_object(Bucket=source_bucket, Key=filename, Body=content)
        
        yield {'s3': s3, 'source': source_bucket, 'dest': dest_bucket}


class TestS3TriggerProcessingStorage:
    """Test S3 trigger, processing, and storage workflow."""
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and 's3_trigger' in f
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_successful_trigger_and_processing(self, func_config, lambda_context):
        """Test complete workflow: trigger -> process -> store."""
        handler, config = S3TriggerTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        source, dest = 'src-bucket', 'dest-bucket'
        s3.create_bucket(Bucket=source)
        s3.create_bucket(Bucket=dest)
        
        test_content = b'test data'
        s3.put_object(Bucket=source, Key='file.txt', Body=test_content)
        
        os.environ['S3_DESTINATION_BUCKET_NAME'] = dest
        event = S3TriggerTestHelper.create_s3_event(source, 'file.txt')
        
        response = handler(event, lambda_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'message' in body
        
        # Verify processed file stored in destination
        result = s3.get_object(Bucket=dest, Key='file.txt')
        processed = result['Body'].read().decode('utf-8')
        assert processed == test_content.decode('utf-8').upper()
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and 's3_trigger' in f
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_multiple_file_types(self, func_config, lambda_context):
        """Test processing different file types."""
        handler, config = S3TriggerTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        source, dest = 'src-bucket', 'dest-bucket'
        s3.create_bucket(Bucket=source)
        s3.create_bucket(Bucket=dest)
        
        os.environ['S3_DESTINATION_BUCKET_NAME'] = dest
        
        mock_files = S3TriggerTestHelper.load_mock_files()
        for filename, content in mock_files.items():
            if filename == 'empty.txt':
                continue
            s3.put_object(Bucket=source, Key=filename, Body=content)
            event = S3TriggerTestHelper.create_s3_event(source, filename)
            response = handler(event, lambda_context)
            assert response['statusCode'] in [200, 400]
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and 's3_trigger' in f
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_large_file_processing(self, func_config, lambda_context):
        """Test processing large files."""
        handler, config = S3TriggerTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        source, dest = 'src-bucket', 'dest-bucket'
        s3.create_bucket(Bucket=source)
        s3.create_bucket(Bucket=dest)
        
        large_content = b'x' * 100000
        s3.put_object(Bucket=source, Key='large.txt', Body=large_content)
        
        os.environ['S3_DESTINATION_BUCKET_NAME'] = dest
        event = S3TriggerTestHelper.create_s3_event(source, 'large.txt')
        
        response = handler(event, lambda_context)
        assert response['statusCode'] == 200
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and 's3_trigger' in f
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_unicode_content_processing(self, func_config, lambda_context):
        """Test processing files with unicode characters."""
        handler, config = S3TriggerTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        source, dest = 'src-bucket', 'dest-bucket'
        s3.create_bucket(Bucket=source)
        s3.create_bucket(Bucket=dest)
        
        unicode_content = 'Hello 世界 🌍 Test'.encode('utf-8')
        s3.put_object(Bucket=source, Key='unicode.txt', Body=unicode_content)
        
        os.environ['S3_DESTINATION_BUCKET_NAME'] = dest
        event = S3TriggerTestHelper.create_s3_event(source, 'unicode.txt')
        
        response = handler(event, lambda_context)
        assert response['statusCode'] == 200
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and 's3_trigger' in f
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_empty_file_handling(self, func_config, lambda_context):
        """Test handling empty files."""
        handler, config = S3TriggerTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        source, dest = 'src-bucket', 'dest-bucket'
        s3.create_bucket(Bucket=source)
        s3.create_bucket(Bucket=dest)
        
        s3.put_object(Bucket=source, Key='empty.txt', Body=b'')
        
        os.environ['S3_DESTINATION_BUCKET_NAME'] = dest
        event = S3TriggerTestHelper.create_s3_event(source, 'empty.txt')
        
        response = handler(event, lambda_context)
        assert response['statusCode'] in [200, 400]


class TestS3TriggerErrorHandling:
    """Test error scenarios for S3 trigger functions."""
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and 's3_trigger' in f
    ], ids=lambda x: x['name'])
    def test_invalid_event_structure(self, func_config, lambda_context):
        """Test handling of malformed events."""
        handler, config = S3TriggerTestHelper.load_handler(func_config['name'])
        
        invalid_events = [
            {},
            {'Records': []},
            {'Records': [{}]},
            {'Records': [{'s3': {}}]},
            None,
        ]
        
        for event in invalid_events:
            response = handler(event, lambda_context)
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert 'error' in body
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and 's3_trigger' in f
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_missing_source_bucket(self, func_config, lambda_context):
        """Test error when source bucket doesn't exist."""
        handler, config = S3TriggerTestHelper.load_handler(func_config['name'])
        
        os.environ['S3_DESTINATION_BUCKET_NAME'] = 'dest-bucket'
        event = S3TriggerTestHelper.create_s3_event('nonexistent-bucket', 'file.txt')
        
        response = handler(event, lambda_context)
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'NoSuchBucket' in body.get('error', '')
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and 's3_trigger' in f
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_missing_object_key(self, func_config, lambda_context):
        """Test error when object doesn't exist."""
        handler, config = S3TriggerTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket = 'test-bucket'
        s3.create_bucket(Bucket=bucket)
        
        os.environ['S3_DESTINATION_BUCKET_NAME'] = 'dest-bucket'
        event = S3TriggerTestHelper.create_s3_event(bucket, 'missing.txt')
        
        response = handler(event, lambda_context)
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'error' in body
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and 's3_trigger' in f
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_missing_destination_bucket(self, func_config, lambda_context):
        """Test error when destination bucket doesn't exist."""
        handler, config = S3TriggerTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        source = 'src-bucket'
        s3.create_bucket(Bucket=source)
        s3.put_object(Bucket=source, Key='file.txt', Body=b'test')
        
        os.environ['S3_DESTINATION_BUCKET_NAME'] = 'nonexistent-dest'
        event = S3TriggerTestHelper.create_s3_event(source, 'file.txt')
        
        response = handler(event, lambda_context)
        assert response['statusCode'] == 500
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and 's3_trigger' in f
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_binary_file_handling(self, func_config, lambda_context):
        """Test handling of binary files (non-UTF-8)."""
        handler, config = S3TriggerTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        source, dest = 'src-bucket', 'dest-bucket'
        s3.create_bucket(Bucket=source)
        s3.create_bucket(Bucket=dest)
        
        binary_content = bytes([0xFF, 0xFE, 0xFD, 0xFC])
        s3.put_object(Bucket=source, Key='binary.bin', Body=binary_content)
        
        os.environ['S3_DESTINATION_BUCKET_NAME'] = dest
        event = S3TriggerTestHelper.create_s3_event(source, 'binary.bin')
        
        response = handler(event, lambda_context)
        assert response['statusCode'] in [400, 500]


class TestS3TriggerConfiguration:
    """Test configuration and environment variables."""
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and 's3_trigger' in f
    ], ids=lambda x: x['name'])
    def test_function_has_s3_trigger_config(self, func_config):
        """Test function has S3 trigger configuration."""
        assert 's3_trigger' in func_config
        assert 'bucket' in func_config['s3_trigger']
        assert 'events' in func_config['s3_trigger']
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and 's3_trigger' in f
    ], ids=lambda x: x['name'])
    def test_function_has_environment_variables(self, func_config):
        """Test function has required environment variables."""
        assert 'environment' in func_config
        assert 'S3_DESTINATION_BUCKET_NAME' in func_config['environment']
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and 's3_trigger' in f
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_environment_variable_override(self, func_config, lambda_context):
        """Test destination bucket from environment variable."""
        handler, config = S3TriggerTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        source, dest = 'src-bucket', 'custom-dest-bucket'
        s3.create_bucket(Bucket=source)
        s3.create_bucket(Bucket=dest)
        s3.put_object(Bucket=source, Key='file.txt', Body=b'test')
        
        os.environ['S3_DESTINATION_BUCKET_NAME'] = dest
        event = S3TriggerTestHelper.create_s3_event(source, 'file.txt')
        
        response = handler(event, lambda_context)
        assert response['statusCode'] == 200
        
        # Verify file in custom destination
        result = s3.get_object(Bucket=dest, Key='file.txt')
        assert result is not None


class TestS3TriggerPerformance:
    """Test performance and resource usage."""
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and 's3_trigger' in f
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_execution_time_within_timeout(self, func_config, lambda_context):
        """Test execution completes within configured timeout."""
        import time
        handler, config = S3TriggerTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        source, dest = 'src-bucket', 'dest-bucket'
        s3.create_bucket(Bucket=source)
        s3.create_bucket(Bucket=dest)
        s3.put_object(Bucket=source, Key='file.txt', Body=b'test')
        
        os.environ['S3_DESTINATION_BUCKET_NAME'] = dest
        event = S3TriggerTestHelper.create_s3_event(source, 'file.txt')
        
        start = time.time()
        response = handler(event, lambda_context)
        duration = time.time() - start
        
        assert response['statusCode'] == 200
        assert duration < config['timeout']
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and 's3_trigger' in f
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_multiple_sequential_invocations(self, func_config, lambda_context):
        """Test multiple sequential invocations."""
        handler, config = S3TriggerTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        source, dest = 'src-bucket', 'dest-bucket'
        s3.create_bucket(Bucket=source)
        s3.create_bucket(Bucket=dest)
        
        os.environ['S3_DESTINATION_BUCKET_NAME'] = dest
        
        for i in range(5):
            key = f'file{i}.txt'
            s3.put_object(Bucket=source, Key=key, Body=f'test{i}'.encode())
            event = S3TriggerTestHelper.create_s3_event(source, key)
            response = handler(event, lambda_context)
            assert response['statusCode'] == 200


class TestGenericS3TriggerFunction:
    """Generic reusable tests for any S3 trigger function."""
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and 's3_trigger' in f
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_s3_trigger_basic_workflow(self, func_config, lambda_context):
        """Generic test for S3 trigger workflow."""
        handler, config = S3TriggerTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        source = 'test-source'
        dest = 'test-dest'
        s3.create_bucket(Bucket=source)
        s3.create_bucket(Bucket=dest)
        s3.put_object(Bucket=source, Key='test.txt', Body=b'test')
        
        if 'environment' in config and 'S3_DESTINATION_BUCKET_NAME' in config['environment']:
            os.environ['S3_DESTINATION_BUCKET_NAME'] = dest
        
        event = S3TriggerTestHelper.create_s3_event(source, 'test.txt')
        response = handler(event, lambda_context)
        
        assert 'statusCode' in response
        assert response['statusCode'] in [200, 400, 500]
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and 's3_trigger' in f
    ], ids=lambda x: x['name'])
    def test_s3_trigger_config_valid(self, func_config):
        """Test S3 trigger configuration is valid."""
        trigger = func_config['s3_trigger']
        assert 'bucket' in trigger
        assert 'events' in trigger
        assert isinstance(trigger['events'], list)
        assert len(trigger['events']) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
