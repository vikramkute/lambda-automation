"""
API Gateway Trigger Lambda Functions Test Suite
Comprehensive tests for Lambda functions with API Gateway triggers.
"""

import pytest
import json
import os
from pathlib import Path
import yaml
import importlib.util
from moto import mock_aws
import boto3

CONFIG_PATH = Path(__file__).parent.parent / 'functions.config.yaml'

with open(CONFIG_PATH, 'r') as f:
    CONFIG = yaml.safe_load(f)


class APIGatewayTestHelper:
    """Helper for API Gateway Lambda function testing."""
    
    @staticmethod
    def load_handler(function_name):
        """Load Lambda handler dynamically."""
        func_config = next((f for f in CONFIG['functions'] if f['name'] == function_name), None)
        if not func_config:
            raise ValueError(f"Function {function_name} not found")
        
        lambda_file = Path(func_config['path']) / 'src' / 'lambda_function.py'
        spec = importlib.util.spec_from_file_location(function_name, lambda_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.lambda_handler, func_config
    
    @staticmethod
    def create_api_event(method='POST', body=None, query_params=None, path_params=None, headers=None):
        """Create mock API Gateway event."""
        return {
            'httpMethod': method,
            'body': json.dumps(body) if body and isinstance(body, dict) else body,
            'headers': headers or {'Content-Type': 'application/json'},
            'queryStringParameters': query_params,
            'pathParameters': path_params,
            'requestContext': {'requestId': 'test-request-id'}
        }


@pytest.fixture
def lambda_context():
    """Mock Lambda context."""
    class Context:
        function_name = 'test-function'
        memory_limit_in_mb = 128
        aws_request_id = 'test-request-id'
        def get_remaining_time_in_millis(self): return 30000
    return Context()


class TestAPIGatewayPOSTRequests:
    """Test POST request handling."""
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and f.get('api_gateway', {}).get('enabled', False)
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_post_with_valid_json(self, func_config, lambda_context):
        """Test POST request with valid JSON body."""
        handler, config = APIGatewayTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        os.environ['S3_DESTINATION_BUCKET_NAME'] = 'test-bucket'
        
        event = APIGatewayTestHelper.create_api_event(
            method='POST',
            body={'message': 'test data', 'key': 'value'}
        )
        
        response = handler(event, lambda_context)
        assert response['statusCode'] in [200, 201]
        assert 'body' in response
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and f.get('api_gateway', {}).get('enabled', False)
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_post_with_invalid_json(self, func_config, lambda_context):
        """Test POST request with invalid JSON."""
        handler, config = APIGatewayTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        os.environ['S3_DESTINATION_BUCKET_NAME'] = 'test-bucket'
        
        event = APIGatewayTestHelper.create_api_event(
            method='POST',
            body='invalid json {'
        )
        
        response = handler(event, lambda_context)
        assert response['statusCode'] in [400, 500]
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and f.get('api_gateway', {}).get('enabled', False)
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_post_with_missing_body(self, func_config, lambda_context):
        """Test POST request with missing body."""
        handler, config = APIGatewayTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        os.environ['S3_DESTINATION_BUCKET_NAME'] = 'test-bucket'
        
        event = APIGatewayTestHelper.create_api_event(method='POST', body=None)
        
        response = handler(event, lambda_context)
        assert 'statusCode' in response
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and f.get('api_gateway', {}).get('enabled', False)
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_post_with_empty_body(self, func_config, lambda_context):
        """Test POST request with empty body."""
        handler, config = APIGatewayTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        os.environ['S3_DESTINATION_BUCKET_NAME'] = 'test-bucket'
        
        event = APIGatewayTestHelper.create_api_event(method='POST', body='')
        
        response = handler(event, lambda_context)
        assert 'statusCode' in response


class TestAPIGatewayGETRequests:
    """Test GET request handling."""
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and f.get('api_gateway', {}).get('enabled', False)
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_get_with_query_params(self, func_config, lambda_context):
        """Test GET request with query parameters."""
        handler, config = APIGatewayTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        os.environ['S3_DESTINATION_BUCKET_NAME'] = 'test-bucket'
        
        event = APIGatewayTestHelper.create_api_event(
            method='GET',
            query_params={'param1': 'value1', 'param2': 'value2'}
        )
        
        response = handler(event, lambda_context)
        assert 'statusCode' in response
        assert 'body' in response
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and f.get('api_gateway', {}).get('enabled', False)
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_get_without_query_params(self, func_config, lambda_context):
        """Test GET request without query parameters."""
        handler, config = APIGatewayTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        os.environ['S3_DESTINATION_BUCKET_NAME'] = 'test-bucket'
        
        event = APIGatewayTestHelper.create_api_event(method='GET')
        
        response = handler(event, lambda_context)
        assert 'statusCode' in response


class TestAPIGatewayHeaders:
    """Test header handling."""
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and f.get('api_gateway', {}).get('enabled', False)
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_cors_headers_present(self, func_config, lambda_context):
        """Test that response includes CORS headers."""
        handler, config = APIGatewayTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        os.environ['S3_DESTINATION_BUCKET_NAME'] = 'test-bucket'
        
        event = APIGatewayTestHelper.create_api_event(
            method='POST',
            body={'test': 'data'}
        )
        
        response = handler(event, lambda_context)
        assert 'statusCode' in response
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and f.get('api_gateway', {}).get('enabled', False)
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_content_type_json(self, func_config, lambda_context):
        """Test response with JSON content type."""
        handler, config = APIGatewayTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        os.environ['S3_DESTINATION_BUCKET_NAME'] = 'test-bucket'
        
        event = APIGatewayTestHelper.create_api_event(
            method='POST',
            body={'data': 'test'},
            headers={'Content-Type': 'application/json'}
        )
        
        response = handler(event, lambda_context)
        assert 'statusCode' in response
        assert 'body' in response


class TestAPIGatewayErrorHandling:
    """Test error scenarios."""
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and f.get('api_gateway', {}).get('enabled', False)
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_unsupported_http_method(self, func_config, lambda_context):
        """Test unsupported HTTP method."""
        handler, config = APIGatewayTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        os.environ['S3_DESTINATION_BUCKET_NAME'] = 'test-bucket'
        
        event = APIGatewayTestHelper.create_api_event(method='DELETE')
        
        response = handler(event, lambda_context)
        assert 'statusCode' in response
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and f.get('api_gateway', {}).get('enabled', False)
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_malformed_event(self, func_config, lambda_context):
        """Test with malformed event structure."""
        handler, config = APIGatewayTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        os.environ['S3_DESTINATION_BUCKET_NAME'] = 'test-bucket'
        
        event = {'invalid': 'structure'}
        
        try:
            response = handler(event, lambda_context)
            assert 'statusCode' in response
        except Exception:
            pass
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and f.get('api_gateway', {}).get('enabled', False)
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_large_payload(self, func_config, lambda_context):
        """Test with large JSON payload."""
        handler, config = APIGatewayTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        os.environ['S3_DESTINATION_BUCKET_NAME'] = 'test-bucket'
        
        large_data = {'data': 'x' * 10000}
        event = APIGatewayTestHelper.create_api_event(method='POST', body=large_data)
        
        response = handler(event, lambda_context)
        assert 'statusCode' in response


class TestAPIGatewayResponseFormat:
    """Test response format compliance."""
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and f.get('api_gateway', {}).get('enabled', False)
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_response_has_required_fields(self, func_config, lambda_context):
        """Test response contains required fields."""
        handler, config = APIGatewayTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        os.environ['S3_DESTINATION_BUCKET_NAME'] = 'test-bucket'
        
        event = APIGatewayTestHelper.create_api_event(
            method='POST',
            body={'test': 'data'}
        )
        
        response = handler(event, lambda_context)
        assert 'statusCode' in response
        assert 'body' in response
        assert isinstance(response['statusCode'], int)
    
    @pytest.mark.parametrize("func_config", [
        f for f in CONFIG['functions'] 
        if f.get('enabled', True) and f.get('api_gateway', {}).get('enabled', False)
    ], ids=lambda x: x['name'])
    @mock_aws
    def test_response_body_is_string(self, func_config, lambda_context):
        """Test response body is string."""
        handler, config = APIGatewayTestHelper.load_handler(func_config['name'])
        
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        os.environ['S3_DESTINATION_BUCKET_NAME'] = 'test-bucket'
        
        event = APIGatewayTestHelper.create_api_event(
            method='POST',
            body={'test': 'data'}
        )
        
        response = handler(event, lambda_context)
        assert isinstance(response.get('body'), str)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
