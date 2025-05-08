# src/store-results-lambda/app.py
import json
import os
import boto3
import time
import decimal # To handle float to Decimal conversion for DynamoDB
import urllib.parse

# Helper class to convert floats to Decimals for DynamoDB
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, float):
            # Ensure finite values for Decimal conversion
            if o != o or o == float('inf') or o == float('-inf'):
                 return str(o) # Convert NaN/inf to string or handle as error
            return decimal.Decimal(str(o))
        return super(DecimalEncoder, self).default(o)

dynamodb_resource = boto3.resource('dynamodb')
DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')

if not DYNAMODB_TABLE_NAME:
    print("Error: DYNAMODB_TABLE_NAME environment variable not set!")

def lambda_handler(event, context):
    print(f"Received event for DynamoDB storage: {json.dumps(event)}")

    if not DYNAMODB_TABLE_NAME:
        raise EnvironmentError("DYNAMODB_TABLE_NAME environment variable is not configured.")

    try:
        table = dynamodb_resource.Table(DYNAMODB_TABLE_NAME)

        # Assuming the primary key for DynamoDB is 'imageId' which is the S3 object key
        image_id = urllib.parse.unquote_plus(event['s3_key']) # Use unquoted key as ID
        timestamp = int(time.time())

        item_to_store = {
            'imageId': image_id, # Primary Key
            's3_bucket': event.get('s3_bucket'),
            's3_key_original': event.get('s3_key'), # Store the potentially quoted key if needed
            'image_type': event.get('image_type'),
            'validation_status': event.get('validation_status'),
            'thumbnails': event.get('thumbnails', {}), # Dictionary of thumbnail URLs
            'thumbnail_generation_status': event.get('thumbnail_generation_status'),
            'extracted_metadata': event.get('extracted_metadata', {}),
            'metadata_extraction_status': event.get('metadata_extraction_status'),
            'overall_processing_status': 'COMPLETED', # Or set based on logic
            'created_at': timestamp,
            'updated_at': timestamp
        }
        
        # DynamoDB does not like float types, convert them to Decimal.
        # A more robust way is to ensure your metadata dict is properly formatted.
        # This is a common pattern for cleaning up data before DynamoDB storage.
        item_cleaned = json.loads(json.dumps(item_to_store), parse_float=decimal.Decimal)

        print(f"Attempting to store item in DynamoDB: {json.dumps(item_cleaned, cls=DecimalEncoder)}")
        
        table.put_item(Item=item_cleaned)
        
        print(f"Successfully stored metadata for imageId: {image_id} in table {DYNAMODB_TABLE_NAME}")

        # This function's output might be the final output of the Step Function
        # or just a confirmation.
        return {
            'message': 'Data stored successfully in DynamoDB',
            'imageId': image_id,
            'dynamodb_table': DYNAMODB_TABLE_NAME
        }

    except Exception as e:
        print(f"Error storing data to DynamoDB: {str(e)}")
        # Log the problematic event data for easier debugging
        print(f"Problematic event data: {json.dumps(event)}")
        raise

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