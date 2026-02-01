import boto3
import json
import os

# Initialize the S3 client
s3_client = boto3.client('s3', region_name='us-east-1')

def lambda_handler(event, context):
    # Get bucket name from environment variable or use a simple default
    bucket_name = os.environ.get('S3_BUCKET_NAME', 'mytestaccesspoint-eofhh939oq6rwhiwq1fbszumm8n5euse1a-s3alias')
    file_key = "sample.txt" 

    try:
        # Get the object from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        
        # Read the file content from the response body
        file_content = response['Body'].read().decode('utf-8')
        print(f"File content: {file_content}") # Logs to CloudWatch

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully read {file_key} from S3',
                'content': file_content
            })
        }
    except Exception as e:
        error_msg = str(e)
        print(f"Error accessing S3 file: {error_msg}")
        
        # Provide specific guidance for common S3 errors
        if "NoSuchBucket" in error_msg:
            suggestion = f"Bucket '{bucket_name}' does not exist. Please create it or set S3_BUCKET_NAME environment variable."
        elif "NoSuchKey" in error_msg:
            suggestion = f"File '{file_key}' not found in bucket '{bucket_name}'."
        else:
            suggestion = "Check AWS credentials and permissions."
            
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': error_msg,
                'suggestion': suggestion,
                'bucket': bucket_name,
                'key': file_key
            })
        }
