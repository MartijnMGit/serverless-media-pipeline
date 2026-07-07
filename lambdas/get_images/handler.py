import json
import os
from decimal import Decimal

import boto3

dynamodb = boto3.resource("dynamodb")

RESULTS_TABLE = os.environ["RESULTS_TABLE"]
DOMAIN_NAME = os.environ["DOMAIN_NAME"]

table = dynamodb.Table(RESULTS_TABLE)


def lambda_handler(event, context):
    # Table is small (portfolio-scale demo traffic) so a full scan is fine;
    # a GSI on uploaded_at would be the move if this ever needed to paginate.
    items = table.scan().get("Items", [])
    items.sort(key=lambda item: item.get("uploaded_at", ""), reverse=True)

    for item in items:
        _add_public_urls(item)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"images": items}, default=_json_default),
    }


def _add_public_urls(item):
    if item.get("thumbnail_key"):
        item["thumbnail_url"] = f"https://{DOMAIN_NAME}/media/{item['thumbnail_key']}"
    if item.get("original_key"):
        item["original_url"] = f"https://{DOMAIN_NAME}/media/{item['original_key']}"


def _json_default(value):
    # DynamoDB returns numbers as Decimal; render whole numbers as int and
    # everything else as float so the API returns real JSON numbers.
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    return str(value)
