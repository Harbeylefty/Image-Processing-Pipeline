# src/store-results-lambda/app.py
import json
import os
import boto3
import time
import decimal # To handle float/int to Decimal conversion for DynamoDB
import urllib.parse

# Helper class to convert Python floats/ints to DynamoDB Decimals,
# and handle pre-existing Decimals correctly for JSON serialization.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, float):
            # Handle NaN, Infinity, -Infinity for floats
            if o != o: return 'NaN' # Not a Number
            if o == float('inf'): return 'Infinity'
            if o == float('-inf'): return '-Infinity'
            # Otherwise, convert float to Decimal via string for precision
            return decimal.Decimal(str(o))
        if isinstance(o, int): # Optionally convert top-level integers if your schema needs it
            return decimal.Decimal(o)
        if isinstance(o, decimal.Decimal):
             # Handle NaN, Infinity, -Infinity for Decimals already
            if o.is_nan(): return 'NaN' # Represent as string "NaN"
            if o.is_infinite():
                return 'Infinity' if o > 0 else '-Infinity' # Represent as string "Infinity"
        return super(DecimalEncoder, self).default(o)

dynamodb_resource = boto3.resource('dynamodb')
DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')

if not DYNAMODB_TABLE_NAME:
    # This print is for deployment-time check; handler has a stricter check.
    print("CRITICAL WARNING: DYNAMODB_TABLE_NAME environment variable not set at global scope!")

def lambda_handler(event, context):
    # Use default=str for logging events that might contain Decimals not yet ready for JSON
    print(f"Received event for DynamoDB storage: {json.dumps(event, default=str)}")

    if not DYNAMODB_TABLE_NAME:
        # This will cause a hard failure if the env var isn't set during runtime
        raise EnvironmentError("DYNAMODB_TABLE_NAME environment variable is not configured for the function.")

    try:
        table = dynamodb_resource.Table(DYNAMODB_TABLE_NAME)

        # imageId will be the primary key, using the unquoted S3 object key
        # Ensure 's3_key' is present in the event
        if 's3_key' not in event:
            raise KeyError("'s3_key' not found in the input event.")
        image_id = urllib.parse.unquote_plus(event['s3_key'])
        timestamp_now = int(time.time()) # Unix epoch timestamp

        # Explicitly pick and structure the item to be stored.
        # Using .get() with defaults for robustness.
        item_to_store = {
            'ImageKey': image_id, # Primary Key
            's3_bucket_original': event.get('s3_bucket'),
            's3_key_original': event.get('s3_key'), # Store the original key, might be URL encoded
            'image_type': event.get('image_type'),
            'validation_status': event.get('validation_status'),
            'thumbnails': event.get('thumbnails', {}), 
            'thumbnail_generation_status': event.get('thumbnail_generation_status'),
            'extracted_metadata': event.get('extracted_metadata', {}), 
            'metadata_extraction_status': event.get('metadata_extraction_status'),
            'overall_processing_status': 'COMPLETED', # Final status
            'created_at': timestamp_now, # Storing as number
            'updated_at': timestamp_now  # Storing as number
        }
        
        # Convert the Python dict to a JSON string using the DecimalEncoder (which makes floats/ints into Decimals),
        # then load it back into a Python dict where numeric strings that were floats/ints are now Decimals.
        # This handles nested structures containing numbers that need to be Decimals for DynamoDB.
        item_json_string_with_decimals = json.dumps(item_to_store, cls=DecimalEncoder)
        item_cleaned_for_dynamodb = json.loads(item_json_string_with_decimals, parse_float=decimal.Decimal, parse_int=decimal.Decimal)

        print(f"Attempting to store item in DynamoDB: {json.dumps(item_cleaned_for_dynamodb, default=str)}") # Use default=str for logging Decimals
        
        table.put_item(Item=item_cleaned_for_dynamodb)
        
        print(f"Successfully stored item for imageId: {image_id} in table {DYNAMODB_TABLE_NAME}")

        # Prepare the final output - pass through all previous data and add current status
        final_output = event.copy() 
        final_output['dynamodb_storage_status'] = 'SUCCESS'
        final_output['overall_processing_status'] = 'COMPLETED' 
        return final_output

    except KeyError as ke:
        print(f"KeyError: Missing expected key in input event - {str(ke)}")
        print(f"Problematic event data for DynamoDB: {json.dumps(event, default=str)}")
        raise
    except Exception as e:
        print(f"Error storing data to DynamoDB for imageId {event.get('s3_key', 'UNKNOWN')}: {str(e)}")
        print(f"Problematic event data for DynamoDB: {json.dumps(event, default=str)}") 
        raise





















# # src/store-results-lambda/app.py
# import json
# import os
# import boto3
# import time
# import decimal # To handle float to Decimal conversion for DynamoDB
# import urllib.parse

# # Helper class to convert floats to Decimals for DynamoDB
# class DecimalEncoder(json.JSONEncoder):
#     def default(self, o):
#         if isinstance(o, float):
#             # Ensure finite values for Decimal conversion
#             if o != o or o == float('inf') or o == float('-inf'):
#                  return str(o) # Convert NaN/inf to string or handle as error
#             return decimal.Decimal(str(o))
#         return super(DecimalEncoder, self).default(o)

# dynamodb_resource = boto3.resource('dynamodb')
# DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')

# if not DYNAMODB_TABLE_NAME:
#     print("Error: DYNAMODB_TABLE_NAME environment variable not set!")

# def lambda_handler(event, context):
#     print(f"Received event for DynamoDB storage: {json.dumps(event)}")

#     if not DYNAMODB_TABLE_NAME:
#         raise EnvironmentError("DYNAMODB_TABLE_NAME environment variable is not configured.")

#     try:
#         table = dynamodb_resource.Table(DYNAMODB_TABLE_NAME)

#         # Assuming the primary key for DynamoDB is 'imageId' which is the S3 object key
#         image_id = urllib.parse.unquote_plus(event['s3_key']) # Use unquoted key as ID
#         timestamp = int(time.time())

#         item_to_store = {
#             'imageId': image_id, # Primary Key
#             's3_bucket': event.get('s3_bucket'),
#             's3_key_original': event.get('s3_key'), # Store the potentially quoted key if needed
#             'image_type': event.get('image_type'),
#             'validation_status': event.get('validation_status'),
#             'thumbnails': event.get('thumbnails', {}), # Dictionary of thumbnail URLs
#             'thumbnail_generation_status': event.get('thumbnail_generation_status'),
#             'extracted_metadata': event.get('extracted_metadata', {}),
#             'metadata_extraction_status': event.get('metadata_extraction_status'),
#             'overall_processing_status': 'COMPLETED', # Or set based on logic
#             'created_at': timestamp,
#             'updated_at': timestamp
#         }
        
#         # DynamoDB does not like float types, convert them to Decimal.
#         # A more robust way is to ensure your metadata dict is properly formatted.
#         # This is a common pattern for cleaning up data before DynamoDB storage.
#         item_cleaned = json.loads(json.dumps(item_to_store), parse_float=decimal.Decimal)

#         print(f"Attempting to store item in DynamoDB: {json.dumps(item_cleaned, cls=DecimalEncoder)}")
        
#         table.put_item(Item=item_cleaned)
        
#         print(f"Successfully stored metadata for imageId: {image_id} in table {DYNAMODB_TABLE_NAME}")

#         # This function's output might be the final output of the Step Function
#         # or just a confirmation.
#         return {
#             'message': 'Data stored successfully in DynamoDB',
#             'imageId': image_id,
#             'dynamodb_table': DYNAMODB_TABLE_NAME
#         }

#     except Exception as e:
#         print(f"Error storing data to DynamoDB: {str(e)}")
#         # Log the problematic event data for easier debugging
#         print(f"Problematic event data: {json.dumps(event)}")
#         raise

# Example Test Event:
# {
#   "s3_bucket": "your-original-image-uploads-bucket",
#   "s3_key": "test-image.jpg",
#   "image_type": ".jpg",
#   "validation_status": "SUCCESS",
#   "thumbnails": {
#     "128x128": "s3://your-processed-thumbnails-bucket/thumbnails/test-image_128x128.jpg",
#     "256x256": "s3://your-processed-thumbnails-bucket/thumbnails/test-image_256x256.jpg"
#   },
#   "thumbnail_generation_status": "SUCCESS",
#   "extracted_metadata": {
#     "filename": "test-image.jpg",
#     "filesize_bytes": 12345,
#     "format": "JPEG",
#     "width_pixels": 800,
#     "height_pixels": 600,
#     "mode": "RGB",
#     "rekognition_labels": [
#       {"Name": "Nature", "Confidence": 95.0},
#       {"Name": "Landscape", "Confidence": 90.0}
#     ]
#   },
#   "metadata_extraction_status": "SUCCESS"
# }