import json
import os
from decimal import Decimal

import boto3

dynamodb = boto3.resource("dynamodb")

RESULTS_TABLE = os.environ["RESULTS_TABLE"]
DOMAIN_NAME = os.environ["DOMAIN_NAME"]

table = dynamodb.Table(RESULTS_TABLE)


def lambda_handler(event, context):
    image_id = event.get("pathParameters", {}).get("id")
    if not image_id:
        return _response(400, {"error": "Missing image id"})

    result = table.get_item(Key={"image_id": image_id})
    item = result.get("Item")

    if not item:
        return _response(404, {"error": "Not found"})

    if item.get("thumbnail_key"):
        item["thumbnail_url"] = f"https://{DOMAIN_NAME}/media/{item['thumbnail_key']}"
    if item.get("original_key"):
        item["original_url"] = f"https://{DOMAIN_NAME}/media/{item['original_key']}"

    return _response(200, item)


def _response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload, default=_json_default),
    }


def _json_default(value):
    # DynamoDB returns numbers as Decimal; render whole numbers as int and
    # everything else as float so the API returns real JSON numbers.
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    return str(value)
