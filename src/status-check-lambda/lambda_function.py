# src/status-check-lambda/app.py
import json
import os
import boto3
import decimal # For handling Decimal types from DynamoDB for JSON serialization

# Helper class to convert Decimal types to float/int for JSON responses.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 == 0:
                return int(o)
            else:
                return float(o)
        return super(DecimalEncoder, self).default(o)

# Initialize DynamoDB resource
dynamodb_resource = boto3.resource('dynamodb')
# Get DynamoDB table name from environment variable
DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')

if not DYNAMODB_TABLE_NAME:
    print("CRITICAL WARNING: DYNAMODB_TABLE_NAME environment variable not set at global scope!")

def lambda_handler(event, context):
    """
    Handles API Gateway requests to check the status of an image by its filename.
    The 'uploads/' prefix is assumed and prepended to the filename.
    Retrieves item from DynamoDB and returns it.
    """
    print(f"Received API Gateway event: {json.dumps(event)}")

    if not DYNAMODB_TABLE_NAME:
        error_message = "Internal server error: DynamoDB table name not configured."
        print(f"ERROR: {error_message}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({"error": error_message})
        }

    try:
        # Extract filename from path parameters provided by API Gateway
        # Assumes your API Gateway resource path is /images/uploads/{filename}/status
        if 'pathParameters' not in event or event['pathParameters'] is None or 'filename' not in event['pathParameters']:
            print("ERROR: 'filename' not found in path parameters.")
            return {
                'statusCode': 400, # Bad Request
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({"error": "filename path parameter is missing."})
            }
            
        filename_from_path = event['pathParameters']['filename']
        
        # Construct the full imageId (S3 key) as stored in DynamoDB
        # by prepending the "uploads/" prefix.
        # Ensure no double slashes if filename_from_path could somehow start with one.
        if filename_from_path.startswith('/'):
            filename_from_path = filename_from_path[1:]
            
        image_id_to_query = f"uploads/{filename_from_path}"

        print(f"Constructed imageId for query: '{image_id_to_query}'. Attempting to retrieve from table '{DYNAMODB_TABLE_NAME}'")
        
        table = dynamodb_resource.Table(DYNAMODB_TABLE_NAME)
        
        # Query DynamoDB for the item using the constructed imageId.
        # Ensure your DynamoDB table's partition key is named 'ImageKey'
        response_ddb = table.get_item(
            Key={'ImageKey': image_id_to_query} 
        )

        if 'Item' in response_ddb:
            item = response_ddb['Item']
            print(f"Item found: {json.dumps(item, cls=DecimalEncoder)}")
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(item, cls=DecimalEncoder)
            }
        else:
            print(f"Item not found for constructed imageId: {image_id_to_query}")
            return {
                'statusCode': 404, # Not Found
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({"message": "Image details not found for the given image identifier."}) # Slightly updated message
            }

    except Exception as e:
        error_detail_str = str(e)
        # Log the original filename received if possible
        original_filename = event.get('pathParameters', {}).get('filename', 'UNKNOWN_FILENAME')
        print(f"Error processing request for filename '{original_filename}': {error_detail_str}")
        
        response_body = {"error": "An internal server error occurred while processing your request."}
        return {
            'statusCode': 500, 
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_body)
        }

# Example Test Event for AWS Lambda Console
# Simulating API Gateway proxy event for the path /images/uploads/{filename}/status
# {
#   "pathParameters": {
#     "filename": "Kubernetes2.png" 
#     // REPLACE with a filename (e.g., "YourImage.jpg") that, when "uploads/" is prepended,
#     // matches an ImageKey that EXISTS in your DynamoDB table for a successful test.
#     // OR use a filename that DOES NOT EXIST (after prepending "uploads/") to test the 404 path.
#   },
#   "httpMethod": "GET", //
#   "requestContext": { 
#       "requestId": "c6af9ac6-7b61-11e6-9a41-93e8deadbeef",
#       "stage": "$default"
#   }
# }