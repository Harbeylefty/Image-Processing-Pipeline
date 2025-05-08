# src/extract-metadata-lambda/app.py
import json
import os
import boto3
from PIL import Image
import io
import urllib.parse

s3_client = boto3.client('s3')
# Initialize Rekognition client only if used, to avoid unnecessary setup
rekognition_client = None
USE_REKOGNITION = os.environ.get('USE_REKOGNITION', 'false').lower() == 'true'

if USE_REKOGNITION:
    rekognition_client = boto3.client('rekognition')

def lambda_handler(event, context):
    print(f"Received event: {json.dumps(event)}")

    try:
        original_bucket = event['s3_bucket']
        original_key = event['s3_key']
        original_key_unquoted = urllib.parse.unquote_plus(original_key)

        print(f"Extracting metadata for: s3://{original_bucket}/{original_key_unquoted}")

        # --- Basic Metadata using Pillow ---
        response_s3 = s3_client.get_object(Bucket=original_bucket, Key=original_key_unquoted)
        image_data = response_s3['Body'].read()
        img = Image.open(io.BytesIO(image_data))
        
        metadata = {
            'filename': os.path.basename(original_key_unquoted),
            'filesize_bytes': len(image_data),
            'format': img.format,
            'width_pixels': img.width,
            'height_pixels': img.height,
            'mode': img.mode # e.g., RGB, RGBA
        }
        print(f"Basic metadata extracted: {metadata}")

        # --- Advanced Metadata using Rekognition (Optional) ---
        if USE_REKOGNITION and rekognition_client:
            try:
                print("Attempting Rekognition label detection...")
                rek_response = rekognition_client.detect_labels(
                    Image={'S3Object': {'Bucket': original_bucket, 'Name': original_key_unquoted}},
                    MaxLabels=10,
                    MinConfidence=75
                )
                rek_labels = [{'Name': label['Name'], 'Confidence': label['Confidence']} for label in rek_response.get('Labels', [])]
                metadata['rekognition_labels'] = rek_labels
                print(f"Rekognition labels: {rek_labels}")
            except Exception as rek_error:
                print(f"Error calling Rekognition: {str(rek_error)}")
                metadata['rekognition_error'] = str(rek_error)
        
        # Prepare output
        output = event.copy() # Pass through previous event data
        output['extracted_metadata'] = metadata
        output['metadata_extraction_status'] = 'SUCCESS'
        return output

    except Exception as e:
        print(f"Error extracting metadata: {str(e)}")
        raise

# Example Test Event:
# {
#   "s3_bucket": "your-original-image-uploads-bucket",
#   "s3_key": "test-image.jpg",
#   "image_type": ".jpg",
#   "validation_status": "SUCCESS",
#   "thumbnails": {
#     "128x128": "s3://your-processed-thumbnails-bucket/thumbnails/test-image_128x128.jpg"
#   },
#   "thumbnail_generation_status": "SUCCESS"
# }