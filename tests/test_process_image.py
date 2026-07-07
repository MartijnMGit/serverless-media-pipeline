import io

import boto3
import pytest
from moto import mock_aws
from PIL import Image

from conftest import load_lambda_handler

BUCKET = "test-media-bucket"


@pytest.fixture
def s3_client(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-3")
    with mock_aws():
        client = boto3.client("s3", region_name="eu-west-3")
        client.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": "eu-west-3"})
        yield client


def _upload_test_image(s3_client, key):
    image = Image.new("RGB", (800, 600), color="blue")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    s3_client.put_object(Bucket=BUCKET, Key=key, Body=buffer, ContentType="image/jpeg")


def test_generates_thumbnail_and_returns_metadata(s3_client):
    key = "uploads/11111111-2222-3333-4444-555555555555-photo.jpg"
    _upload_test_image(s3_client, key)

    module = load_lambda_handler("process_image")
    result = module.lambda_handler({"bucket": BUCKET, "key": key}, None)

    assert result["image_id"] == "11111111-2222-3333-4444-555555555555"
    assert result["thumbnail_key"] == "processed/11111111-2222-3333-4444-555555555555-photo-thumb.jpg"

    thumb_obj = s3_client.get_object(Bucket=BUCKET, Key=result["thumbnail_key"])
    thumb_image = Image.open(io.BytesIO(thumb_obj["Body"].read()))
    assert max(thumb_image.size) <= 400


def test_passes_through_input_fields(s3_client):
    key = "uploads/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee-pic.png"
    _upload_test_image(s3_client, key)

    module = load_lambda_handler("process_image")
    result = module.lambda_handler({"bucket": BUCKET, "key": key, "uploaded_at": "2026-01-01T00:00:00Z"}, None)

    assert result["bucket"] == BUCKET
    assert result["key"] == key
    assert result["uploaded_at"] == "2026-01-01T00:00:00Z"
