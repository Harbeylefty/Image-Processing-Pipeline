# src/generate-thumbnails-lambda/app.py
import json
import os
import boto3
from PIL import Image # Pillow library for image manipulation
import io # To handle image data in memory
import urllib.parse

s3_client = boto3.client('s3')

# Get thumbnail sizes from environment variable or use this as default if not set
# Format: "width1xheight1,width2xheight2" (e.g., "100x100,640x480")
THUMBNAIL_SIZES_STR = os.environ.get('THUMBNAIL_SIZES', '128x128,256x256')
THUMBNAIL_SIZES = []
for size_pair in THUMBNAIL_SIZES_STR.split(','):
    try:
        width, height = map(int, size_pair.split('x'))
        THUMBNAIL_SIZES.append((width, height))
    except ValueError:
        print(f"Warning: Invalid size format '{size_pair}' in THUMBNAIL_SIZES. Skipping.")


THUMBNAILS_S3_BUCKET = os.environ.get('THUMBNAILS_S3_BUCKET')
if not THUMBNAILS_S3_BUCKET:
    print("Error: THUMBNAILS_S3_BUCKET environment variable not set!")

def lambda_handler(event, context):
    print(f"Received event: {json.dumps(event)}")

    if not THUMBNAILS_S3_BUCKET:
        raise EnvironmentError("THUMBNAILS_S3_BUCKET environment variable is not configured.")

    try:
        original_bucket = event['s3_bucket']
        original_key = event['s3_key']
        
        # Unquote the object key
        original_key_unquoted = urllib.parse.unquote_plus(original_key)

        print(f"Generating thumbnails for: s3://{original_bucket}/{original_key_unquoted}")

        # Get the original image from S3
        response = s3_client.get_object(Bucket=original_bucket, Key=original_key_unquoted)
        image_data = response['Body'].read()
        
        img = Image.open(io.BytesIO(image_data))
        # Preserve original format if possible, or default to JPEG/PNG
        original_format = img.format if img.format else 'JPEG'
        if original_format.upper() not in ['JPEG', 'PNG']:
            print(f"Warning: Original format {original_format} not ideal for web. Converting to JPEG.")
            original_format = 'JPEG' # Default to JPEG for thumbnails

        thumbnail_locations = {}
        base_filename, _ = os.path.splitext(os.path.basename(original_key_unquoted))

        for width, height in THUMBNAIL_SIZES:
            img_copy = img.copy()
            img_copy.thumbnail((width, height)) # Preserves aspect ratio, fits within bounds

            # Save thumbnail to an in-memory buffer
            buffer = io.BytesIO()
            # Convert to RGB if it's RGBA (PNG with alpha) to save as JPEG
            if original_format.upper() == 'JPEG' and img_copy.mode == 'RGBA':
                img_copy = img_copy.convert('RGB')
            
            img_copy.save(buffer, format=original_format)
            buffer.seek(0) # Reset buffer's position to the beginning

            thumbnail_key = f"thumbnails/{base_filename}_{width}x{height}.{original_format.lower()}"
            
            s3_client.put_object(
                Bucket=THUMBNAILS_S3_BUCKET,
                Key=thumbnail_key,
                Body=buffer,
                ContentType=Image.MIME[original_format] # e.g., 'image/jpeg'
            )
            print(f"Uploaded thumbnail: s3://{THUMBNAILS_S3_BUCKET}/{thumbnail_key}")
            thumbnail_locations[f"{width}x{height}"] = f"s3://{THUMBNAILS_S3_BUCKET}/{thumbnail_key}"

        # Prepare output for the next Step Functions state
        output = event.copy() # Pass through previous event data
        output['thumbnails'] = thumbnail_locations
        output['thumbnail_generation_status'] = 'SUCCESS'
        return output

    except Exception as e:
        print(f"Error generating thumbnails: {str(e)}")
        raise

# Example Test Event:
# {
#   "s3_bucket": "image-uploads-bucket",
#   "s3_key": "image.jpg",
#   "image_type": ".jpg",
#   "validation_status": "SUCCESS"
# }