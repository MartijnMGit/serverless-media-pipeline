import json

import boto3
import pytest
from moto import mock_aws

from conftest import load_lambda_handler

BUCKET = "test-media-bucket"


@pytest.fixture
def handler_module(monkeypatch):
    monkeypatch.setenv("MEDIA_BUCKET", BUCKET)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-3")
    monkeypatch.setenv("AWS_REGION", "eu-west-3")
    with mock_aws():
        s3 = boto3.client("s3", region_name="eu-west-3")
        s3.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": "eu-west-3"})
        yield load_lambda_handler("presign_upload")


def _invoke(module, body: dict):
    return module.lambda_handler({"body": json.dumps(body)}, None)


def test_returns_presigned_url_and_key(handler_module):
    response = _invoke(handler_module, {"filename": "photo.jpg", "content_type": "image/jpeg"})

    assert response["statusCode"] == 200
    payload = json.loads(response["body"])
    assert payload["key"].startswith("uploads/")
    assert payload["key"].endswith("photo.jpg")
    assert "upload_url" in payload
    assert "image_id" in payload
    # Must be the regional endpoint - the global s3.amazonaws.com endpoint
    # gets 307-redirected for buckets outside us-east-1, breaking presigned PUTs.
    assert "eu-west-3" in payload["upload_url"]


def test_sanitizes_unsafe_filename(handler_module):
    response = _invoke(handler_module, {"filename": "../../etc/passwd", "content_type": "image/png"})

    payload = json.loads(response["body"])
    # No extra "/" beyond the one "uploads/" prefix - a hostile filename can't
    # smuggle path segments into the object key.
    assert payload["key"].count("/") == 1
    assert payload["key"].startswith("uploads/")


def test_rejects_missing_fields(handler_module):
    response = _invoke(handler_module, {"filename": "photo.jpg"})
    assert response["statusCode"] == 400


def test_rejects_disallowed_content_type(handler_module):
    response = _invoke(handler_module, {"filename": "script.svg", "content_type": "image/svg+xml"})
    assert response["statusCode"] == 400


def test_rejects_invalid_json_body(handler_module):
    response = handler_module.lambda_handler({"body": "not json"}, None)
    assert response["statusCode"] == 400
