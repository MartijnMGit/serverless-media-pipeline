import json
import os
import re
import uuid

import boto3
from botocore.config import Config

# boto3's default S3 endpoint resolution generates presigned URLs against
# the global s3.amazonaws.com host regardless of region_name, and S3
# 307-redirects that away for any bucket outside us-east-1 - a redirect a
# presigned PUT can't safely follow. Forcing the regional endpoint directly
# avoids the redirect entirely.
_REGION = os.environ["AWS_REGION"]
s3 = boto3.client(
    "s3",
    region_name=_REGION,
    endpoint_url=f"https://s3.{_REGION}.amazonaws.com",
    config=Config(s3={"addressing_style": "virtual"}),
)

MEDIA_BUCKET = os.environ["MEDIA_BUCKET"]
UPLOAD_URL_TTL_SECONDS = 300
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Keep the object key readable but safe: strip anything that isn't a
# word character, dot or dash so a filename can't inject a path/prefix.
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]")


def _clean_filename(filename: str) -> str:
    name = _SAFE_NAME_RE.sub("_", filename)[-100:]
    return name or "upload"


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "Body must be valid JSON"})

    filename = body.get("filename")
    content_type = body.get("content_type")

    if not filename or not content_type:
        return _response(400, {"error": "filename and content_type are required"})

    if content_type not in ALLOWED_CONTENT_TYPES:
        return _response(400, {"error": f"content_type must be one of {sorted(ALLOWED_CONTENT_TYPES)}"})

    image_id = str(uuid.uuid4())
    key = f"uploads/{image_id}-{_clean_filename(filename)}"

    upload_url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": MEDIA_BUCKET, "Key": key, "ContentType": content_type},
        ExpiresIn=UPLOAD_URL_TTL_SECONDS,
    )

    return _response(200, {"image_id": image_id, "upload_url": upload_url, "key": key})


def _response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }
