import boto3
import urllib.parse
import json
import os
   
print('Loading function')   

s3 = boto3.client('s3')     

def transform_json_values(obj):
    if isinstance(obj, dict):   
        return {k: transform_json_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [transform_json_values(item) for item in obj]
    elif isinstance(obj, str):
        return obj.upper()
    else:
        return obj

def lambda_handler(event, context):
    try:
        source_bucket = event['Records'][0]['s3']['bucket']['name']
        source_bucket2 = event['Records'][0]['s3']['bucket']['name']
        file_key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
    except (KeyError, IndexError, TypeError) as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid event structure', 'details': str(e)})
        }
    
    destination_bucket = os.environ.get('S3_DESTINATION_BUCKET_NAME', 'mybucket3accesspoint-znfe5kdypno5qb9wyxo5iexhikrjause1a-s3alias')
    
    try:
        # 1. Read the file from the source S3 bucket
        response = s3.get_object(Bucket=source_bucket, Key=file_key)
        response2 = s3.get_object(Bucket=source_bucket2, Key=file_key)
        try:
            original_content = response2['Body'].read().decode('utf-8')
        except UnicodeDecodeError:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'File is not UTF-8 encoded or is binary and cannot be processed'})
            }
        print(f"Read file {file_key} from bucket {source_bucket}")   
        
        # 2. Transform the file content (JSON values only)
        if file_key.lower().endswith('.json'):
            try:
                data =    json.loads(original_content)
                transformed_data = transform_json_values(data)
                transformed_content = json.dumps(transformed_data, indent=2)
            except json.JSONDecodeError:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Invalid JSON file for this transformation'})
                }
        else:
            transformed_content = original_content.upper()
        
        # 3. Save the transformed file into the destination S3 bucket
        s3.put_object(Bucket=destination_bucket, Key=file_key, Body=transformed_content)
        print(f"Saved transformed file {file_key} to destination bucket {destination_bucket}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'{file_key} processed and saved to destination bucket successfully!'
            })
        }
    except Exception as e:    
        error_msg = str(e)
        print(f"Error accessing S3 file {file_key} in bucket {source_bucket}: {error_msg}")     
        
        # Provide specific guidance for common S3 errors
        if "NoSuchBucket" in error_msg:    
            suggestion = f"Bucket '{source_bucket}' does not exist. Please create it or set S3_SOURCE_BUCKET_NAME environment variable."
        elif "NoSuchKey" in error_msg:
            suggestion = f"File '{file_key}' not found in bucket '{source_bucket}'."
        else:
            suggestion = "Check AWS credentials and permissions."
            
        return {
            'statusCode': 500,   
            'body': json.dumps({
                'error': error_msg,
                'suggestion': suggestion,
                'bucket': source_bucket,
                'key': file_key
            })
        }
