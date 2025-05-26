# src/image-validation-lambda/lambda_function.py
import json
import os
import urllib.parse

# Supported image types (you can expand this list)
SUPPORTED_IMAGE_TYPES = ['.jpg', '.jpeg', '.png']

def lambda_handler(event, context):
    print(f"Received event: {json.dumps(event)}")

    try:
        bucket_name = None
        object_key = None

        if 'bucket' in event and isinstance(event.get('bucket'), dict) and 'name' in event.get('bucket', {}):
            bucket_name = event['bucket']['name']
        
        if 'object' in event and isinstance(event.get('object'), dict) and 'key' in event.get('object', {}):
            object_key = event['object']['key']

        # Check if we successfully extracted the needed information
        if not bucket_name or not object_key:
            # Log the event if parsing fails, to help debug what was actually received
            print(f"CRITICAL_ERROR: Failed to extract bucket_name or object_key from event. Event received: {json.dumps(event)}")
            raise ValueError("S3 bucket name or object key not found in the expected event structure.")

        # Unquote the object key if it's URL-encoded (S3 keys can have spaces, etc.)
        object_key = urllib.parse.unquote_plus(object_key)
        
        print(f"Validating image: s3://{bucket_name}/{object_key}")

        # Simple validation based on file extension
        _, file_extension = os.path.splitext(object_key.lower())

        if file_extension in SUPPORTED_IMAGE_TYPES:
            print(f"Image type '{file_extension}' is supported.")
            # Prepare output for the next Step Functions state
            output = {
                's3_bucket': bucket_name,
                's3_key': object_key,
                'image_type': file_extension,
                'validation_status': 'SUCCESS'
            }
            return output
        else:
            error_message = f"Unsupported image type: '{file_extension}'. Supported types are: {SUPPORTED_IMAGE_TYPES}"
            print(error_message) # Print the error before raising
            # This will cause the Lambda to fail, and Step Functions can catch this error
            raise ValueError(error_message)

    except Exception as e:
        # Log the original event along with the error if an unexpected exception occurs
        print(f"Error during image validation. Event was: {json.dumps(event)}")
        print(f"Error details: {str(e)}")
        # Re-raise the exception so Step Functions can handle it as a failure
        raise

# Example Test Event for the AWS Lambda Console
# Test Event 1: Simulating the actual input for a valid image
# {
#   "bucket": {
#     "name": "image-uploads-bucket"
#   },
#   "object": {
#     "key": "uploads/test-image.jpg"
#   }
# }

# Test Event 2: Simulating an unsupported file type (using the actual input structure)
# {
#   "bucket": {
#     "name": "image-uploads-bucket"
#   },
#   "object": {
#     "key": "uploads/test-image.pdf"
#   }
# }