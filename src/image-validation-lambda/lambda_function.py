# src/image-validation-lambda/lambda_function.py
import json
import os
import urllib.parse

# Define supported image types (you can expand this list)
SUPPORTED_IMAGE_TYPES = ['.jpg', '.jpeg', '.png']

def lambda_handler(event, context):
    print(f"Received event: {json.dumps(event)}")

    try:
        # --- 1. Extract S3 Bucket and Key from the Event (Corrected Parsing) ---
        # This parsing directly matches the structure received from S3 via EventBridge/StepFunctions
        # (as observed in your input from turn 94).
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

        # --- 2. Simple validation based on file extension (This part remains the same) ---
        _, file_extension = os.path.splitext(object_key.lower())

        if file_extension in SUPPORTED_IMAGE_TYPES:
            print(f"Image type '{file_extension}' is supported.") # Updated log message slightly
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

# --- Example Test Event for the AWS Lambda Console ---
# This test event NOW matches the structure your Lambda is likely receiving 
# end-to-end from S3 via EventBridge (the 'detail' part of an EventBridge event).
#
# Test Event 1: Simulating the actual input for a valid image
# {
#   "version": "0",
#   "bucket": {
#     "name": "your-original-image-uploads-bucket" ## REPLACE with your actual bucket name
#   },
#   "object": {
#     "key": "uploads/test-image.jpg", ## REPLACE with a test key, in 'uploads/'
#     "size": 12345,
#     "etag": "some-etag",
#     "sequencer": "some-sequencer" 
#     // You can add other fields from your actual event from turn 94 if needed for completeness,
#     // but 'bucket.name' and 'object.key' are the essential ones for this Lambda.
#   },
#   "request-id": "EXAMPLE_REQUEST_ID", // These fields below are illustrative
#   "requester": "EXAMPLE_REQUESTER",
#   "source-ip-address": "127.0.0.1",
#   "reason": "PutObject"
# }

# Test Event 2: Simulating an unsupported file type (using the actual input structure)
# {
#   "version": "0",
#   "bucket": {
#     "name": "your-original-image-uploads-bucket" ## REPLACE
#   },
#   "object": {
#     "key": "uploads/document.pdf", ## REPLACE
#     "size": 6789,
#     "etag": "another-etag",
#     "sequencer": "another-sequencer"
#   },
#   "request-id": "EXAMPLE_REQUEST_ID_2",
#   "requester": "EXAMPLE_REQUESTER_2",
#   "source-ip-address": "127.0.0.1",
#   "reason": "PutObject"
# }






















# # src/image-validation-lambda/app.py
# import json
# import os
# import urllib.parse

# # Define supported image types (you can expand this list)
# SUPPORTED_IMAGE_TYPES = ['.jpg', '.jpeg', '.png']

# def lambda_handler(event, context):
#     print(f"Received event: {json.dumps(event)}")

#     try:
#         # Extract bucket name and object key from the S3 event
#         # This structure can vary depending on how Step Functions passes the event.
#         # If S3 triggers Step Functions directly, the event might be nested.
#         # Let's assume the event directly contains S3 object details or is passed
#         # by a previous Step Functions state.

#         # Example if Step Functions passes something like:
#         # { "s3_bucket": "your-bucket", "s3_key": "path/to/image.jpg" }
#         # Adjust based on your actual Step Functions input to this state.
        
#         # If the input is directly from an S3 trigger (passed through Step Functions):
#         record = event.get('Records', [{}])[0]
#         s3_event = record.get('s3', {})
#         bucket_name = s3_event.get('bucket', {}).get('name')
#         object_key = s3_event.get('object', {}).get('key')

#         if not bucket_name or not object_key:
#             # Fallback if Step Functions provides a different input structure
#             bucket_name = event.get('s3_bucket')
#             object_key = event.get('s3_key')
#             if not bucket_name or not object_key:
#                 raise ValueError("Bucket name or object key not found in the event.")

#         # Unquote the object key if it's URL-encoded (S3 keys can have spaces, etc.)
#         object_key = urllib.parse.unquote_plus(object_key)
        
#         print(f"Validating image: s3://{bucket_name}/{object_key}")

#         # Simple validation based on file extension
#         _, file_extension = os.path.splitext(object_key.lower())

#         if file_extension in SUPPORTED_IMAGE_TYPES:
#             print(f"Image type {file_extension} is supported.")
#             # Prepare output for the next Step Functions state
#             output = {
#                 's3_bucket': bucket_name,
#                 's3_key': object_key,
#                 'image_type': file_extension,
#                 'validation_status': 'SUCCESS'
#             }
#             return output
#         else:
#             print(f"Image type {file_extension} is NOT supported.")
#             # This will cause the Lambda to fail, and Step Functions can catch this error
#             raise ValueError(f"Unsupported image type: {file_extension}. Supported types are: {SUPPORTED_IMAGE_TYPES}")

#     except Exception as e:
#         print(f"Error during image validation: {str(e)}")
#         # Re-raise the exception so Step Functions can handle it as a failure
#         raise

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
