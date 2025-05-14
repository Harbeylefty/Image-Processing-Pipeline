# src/status-check-lambda/app.py
import json
import os
import boto3
import decimal # For handling Decimal types from DynamoDB for JSON serialization

# Helper class to convert Decimal types to float/int for JSON responses.
# This is important because json.dumps() cannot serialize Decimal objects directly.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            # Convert Decimal to float or int.
            # If it's a whole number (no fractional part), convert to int, otherwise float.
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
    # This print is for deployment-time check; the handler has a stricter check.
    print("CRITICAL WARNING: DYNAMODB_TABLE_NAME environment variable not set at global scope!")

def lambda_handler(event, context):
    """
    Handles API Gateway requests to check the status of an image by its ID.
    Retrieves item from DynamoDB and returns it.
    """
    print(f"Received API Gateway event: {json.dumps(event)}")

    if not DYNAMODB_TABLE_NAME:
        error_message = "Internal server error: DynamoDB table name not configured."
        print(f"ERROR: {error_message}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({"error": error_message})
        }

    try:
        # Extract imageId from path parameters provided by API Gateway
        # Assumes your API Gateway resource path is something like /images/{imageId}/status
        if 'pathParameters' not in event or event['pathParameters'] is None or 'imageId' not in event['pathParameters']:
            print("ERROR: imageId not found in path parameters.")
            return {
                'statusCode': 400, # Bad Request
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({"error": "imageId path parameter is missing."})
            }
            
        image_id_from_path = event['pathParameters']['imageId']
        
        # S3 keys (which are used as imageId here) can contain URL-encoded characters.
        # API Gateway usually decodes path parameters, but if you find it's still encoded,
        # you might need to unquote it. For now, we assume it's passed as needed
        # or that your imageIds don't contain characters that need special URL encoding
        # that isn't handled by API Gateway.
        # The imageId in DynamoDB was stored unquoted.
        image_id_to_query = image_id_from_path
        # For example, if an s3 key was 'uploads/my image.jpg', it would be 'uploads/my%20image.jpg' in a URL.
        # API Gateway path parameter mapping often handles this decoding automatically.
        # If not, you'd use:
        # import urllib.parse
        # image_id_to_query = urllib.parse.unquote_plus(image_id_from_path)


        print(f"Attempting to retrieve item for imageId: '{image_id_to_query}' from table '{DYNAMODB_TABLE_NAME}'")
        
        table = dynamodb_resource.Table(DYNAMODB_TABLE_NAME)
        
        # Query DynamoDB for the item using the imageId
        response_ddb = table.get_item(
            Key={'ImageKey': image_id_to_query} 
        )

        if 'Item' in response_ddb:
            item = response_ddb['Item']
            print(f"Item found: {json.dumps(item, cls=DecimalEncoder)}") # Log with DecimalEncoder
            
            # Prepare a successful HTTP response for API Gateway
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*' # Basic CORS header, adjust as needed
                },
                'body': json.dumps(item, cls=DecimalEncoder) # Use DecimalEncoder for the response body
            }
        else:
            print(f"Item not found for imageId: {image_id_to_query}")
            return {
                'statusCode': 404, # Not Found
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({"message": "Image details not found for the given imageId."})
            }

    except Exception as e:
        error_detail_str = str(e)
        print(f"Error processing request for imageId '{event.get('pathParameters', {}).get('imageId', 'UNKNOWN')}': {error_detail_str}")
        # Avoid sending detailed internal error messages or stack traces in production API responses
        # For debugging, you might include more, but for a live API, a generic message is safer.
        response_body = {"error": "An internal server error occurred while processing your request."}
        # If you want to log the specific error for your own debugging:
        # response_body = {"error": "Internal server error.", "detail": error_detail_str}
        return {
            'statusCode': 500, # Internal Server Error
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_body)
        }

# --- Example Test Event for AWS Lambda Console (simulating API Gateway proxy event) ---
# # {
# #   "pathParameters": {
# #     "imageId": "uploads/grafana-dashboard-english.png" 
# #     // REPLACE with an imageId that EXISTS in your DynamoDB table for a successful test
# #     // OR use an imageId that DOES NOT EXIST to test the 404 path
# #   },
# #   "httpMethod": "GET", // Illustrative, this Lambda doesn't use it but API Gateway sends it
# #   "requestContext": { // Illustrative, provides context about the request
# #       "requestId": "c6af9ac6-7b61-11e6-9a41-93e8deadbeef",
# #       "stage": "prod"
# #   }
# #   // API Gateway sends many other fields, but pathParameters.imageId is the one this Lambda uses.
# # }