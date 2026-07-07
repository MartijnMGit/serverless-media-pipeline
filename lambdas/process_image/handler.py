import io
import re

import boto3
from PIL import Image

s3 = boto3.client("s3")

THUMBNAIL_MAX_SIZE = (400, 400)
UUID_LENGTH = 36

# Presigned PUT URLs can't enforce an upload size, so this is the first
# place oversized files can be stopped. Refusing here (before any S3 read
# or Pillow work) keeps a hostile multi-GB upload from costing anything
# beyond its brief S3 storage, which the lifecycle rule cleans up.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def lambda_handler(event, context):
    bucket = event["bucket"]
    key = event["key"]

    size = event.get("size")
    if size is not None and int(size) > MAX_UPLOAD_BYTES:
        raise ValueError(f"Upload {key} is {size} bytes, over the {MAX_UPLOAD_BYTES} byte limit")

    obj = s3.get_object(Bucket=bucket, Key=key)
    image = Image.open(io.BytesIO(obj["Body"].read())).convert("RGB")
    image.thumbnail(THUMBNAIL_MAX_SIZE)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    buffer.seek(0)

    thumbnail_key = _thumbnail_key(key)
    s3.put_object(Bucket=bucket, Key=thumbnail_key, Body=buffer, ContentType="image/jpeg")

    return {
        **event,
        "image_id": _extract_image_id(key),
        "thumbnail_key": thumbnail_key,
    }


def _extract_image_id(key: str) -> str:
    # Matches the "uploads/{uuid}-{filename}" convention set by presign_upload.
    filename_part = key.split("/", 1)[1]
    return filename_part[:UUID_LENGTH]


def _thumbnail_key(key: str) -> str:
    filename_part = key.split("/", 1)[1]
    base = re.sub(r"\.[^.]+$", "", filename_part)
    return f"processed/{base}-thumb.jpg"
