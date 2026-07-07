import os
import time
from decimal import Decimal

import boto3

dynamodb = boto3.resource("dynamodb")

RESULTS_TABLE = os.environ["RESULTS_TABLE"]
table = dynamodb.Table(RESULTS_TABLE)


def lambda_handler(event, context):
    image_id = event["image_id"]
    labels = event.get("labels", [])
    now = _now_iso()

    table.put_item(
        Item={
            "image_id": image_id,
            "original_key": event["key"],
            "thumbnail_key": event["thumbnail_key"],
            # DynamoDB's resource API rejects native floats (Rekognition
            # confidence scores are floats), so convert before writing.
            "labels": _floats_to_decimal(labels),
            "status": "COMPLETE",
            "uploaded_at": event.get("uploaded_at", now),
            "processed_at": now,
        }
    )

    return {"image_id": image_id, "status": "COMPLETE", "labels": labels}


def _floats_to_decimal(value):
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, list):
        return [_floats_to_decimal(v) for v in value]
    if isinstance(value, dict):
        return {k: _floats_to_decimal(v) for k, v in value.items()}
    return value


def _now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
