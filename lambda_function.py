import json
import urllib.parse
from company_search import main  # or however you import your "main" function


def lambda_handler(event, context):
    """
    Lambda handler to orchestrate the company search script (company_search.py).

    Expects a query parameter 'company' from the event (typical for API Gateway).
    Example: GET /?company=Microsoft
    """
    try:
        # If using API Gateway with GET /?company=NAME
        params = event.get("queryStringParameters", {})
        company_name = params.get("company", None)

        # Alternatively, if you pass the name in the path param, e.g. /company/{name}:
        # company_name = event["pathParameters"]["name"]

        if not company_name:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing 'company' query parameter."})
            }

        # Decode in case of URL-encoded input (e.g., spaces turned into %20)
        company_name = urllib.parse.unquote(company_name)

        # Call the existing main() function from your script
        result = main(company_name)

        # Return result as JSON
        return {
            "statusCode": 200,
            "body": json.dumps({
                "company": company_name,
                "result": result
            }, ensure_ascii=False),
            "headers": {
                "Content-Type": "application/json"
            }
        }

    except Exception as e:
        # In case of unexpected errors
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


# Example usage:
if __name__ == "__main__":
    # Simulate an event with a query parameter
    event = {"queryStringParameters": {"company": "Big Panda"}}
    context = None
    print(lambda_handler(event, context))