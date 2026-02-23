import json
import boto3
import os
from datetime import datetime

s3 = boto3.client('s3')

def save_to_s3(bucket, data):
    file_key = f"{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
    s3.put_object(Bucket=bucket, Key=file_key, Body=json.dumps(data))
    return file_key

def lambda_handler(event, context):
    try:
        destination_bucket = os.environ.get('S3_DESTINATION_BUCKET_NAME', 'mytestaccesspoint-eofhh939oq6rwhiwq1fbszumm8n5euse1a-s3alias')
        
        # Handle EventBridge Scheduler events
        if 'source' in event and event['source'] == 'aws.scheduler':
            data = {'timestamp': datetime.utcnow().isoformat(), 'source': 'eventbridge', 'event': event}
            file_key = save_to_s3(destination_bucket, data)
            return {'statusCode': 200, 'body': json.dumps({'message': 'EventBridge event processed', 's3File': file_key})}
        
        if 'detail-type' in event:
            data = {'timestamp': datetime.utcnow().isoformat(), 'source': 'eventbridge', 'event': event}
            file_key = save_to_s3(destination_bucket, data)
            return {'statusCode': 200, 'body': json.dumps({'message': 'EventBridge event processed', 's3File': file_key})}
        
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '/')
        query_params = event.get('queryStringParameters')
        if query_params is None:
            query_params = {}
        body = event.get('body')
        
        if http_method == 'GET':
            data = {'timestamp': datetime.utcnow().isoformat(), 'path': path, 'queryParams': query_params, 'message': 'GET request successful'}
            file_key = save_to_s3(destination_bucket, data)
            return {'statusCode': 200, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps({'message': 'GET request successful', 'path': path, 'queryParams': query_params, 's3File': file_key})}
        
        elif http_method == 'POST':
            payload = json.loads(body) if body else {}
            data = {'timestamp': datetime.utcnow().isoformat(), 'path': path, 'payload': payload, 'message': 'POST request successful'}
            file_key = save_to_s3(destination_bucket, data)
            return {'statusCode': 201, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps({'message': 'POST request successful', 'received': payload, 's3File': file_key})}
        
        else:
            return {
                'statusCode': 405,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Method not allowed'})
            }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }
