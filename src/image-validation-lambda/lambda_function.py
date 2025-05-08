# src/image-validation-lambda/app.py
import json
import os
import urllib.parse

# Define supported image types (you can expand this list)
SUPPORTED_IMAGE_TYPES = ['.jpg', '.jpeg', '.png']

def lambda_handler(event, context):
    print(f"Received event: {json.dumps(event)}")

    try:
        # Extract bucket name and object key from the S3 event
        # This structure can vary depending on how Step Functions passes the event.
        # If S3 triggers Step Functions directly, the event might be nested.
        # Let's assume the event directly contains S3 object details or is passed
        # by a previous Step Functions state.

        # Example if Step Functions passes something like:
        # { "s3_bucket": "your-bucket", "s3_key": "path/to/image.jpg" }
        # Adjust based on your actual Step Functions input to this state.
        
        # If the input is directly from an S3 trigger (passed through Step Functions):
        record = event.get('Records', [{}])[0]
        s3_event = record.get('s3', {})
        bucket_name = s3_event.get('bucket', {}).get('name')
        object_key = s3_event.get('object', {}).get('key')

        if not bucket_name or not object_key:
            # Fallback if Step Functions provides a different input structure
            bucket_name = event.get('s3_bucket')
            object_key = event.get('s3_key')
            if not bucket_name or not object_key:
                raise ValueError("Bucket name or object key not found in the event.")

        # Unquote the object key if it's URL-encoded (S3 keys can have spaces, etc.)
        object_key = urllib.parse.unquote_plus(object_key)
        
        print(f"Validating image: s3://{bucket_name}/{object_key}")

        # Simple validation based on file extension
        _, file_extension = os.path.splitext(object_key.lower())

        if file_extension in SUPPORTED_IMAGE_TYPES:
            print(f"Image type {file_extension} is supported.")
            # Prepare output for the next Step Functions state
            output = {
                's3_bucket': bucket_name,
                's3_key': object_key,
                'image_type': file_extension,
                'validation_status': 'SUCCESS'
            }
            return output
        else:
            print(f"Image type {file_extension} is NOT supported.")
            # This will cause the Lambda to fail, and Step Functions can catch this error
            raise ValueError(f"Unsupported image type: {file_extension}. Supported types are: {SUPPORTED_IMAGE_TYPES}")

    except Exception as e:
        print(f"Error during image validation: {str(e)}")
        # Re-raise the exception so Step Functions can handle it as a failure
        raise

# Example Test Event for this Lambda (configure in Lambda console "Test" tab):
# {
#   "Records": [
#     {
#       "s3": {
#         "bucket": {
#           "name": "your-original-image-uploads-bucket"
#         },
#         "object": {
#           "key": "test-image.jpg"
#         }
#       }
#     }
#   ]
# }
# OR if Step Functions passes a custom input:
# {
#   "s3_bucket": "your-original-image-uploads-bucket",
#   "s3_key": "test-image.png"
# }