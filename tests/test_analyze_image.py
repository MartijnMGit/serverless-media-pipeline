import boto3
import pytest
from moto import mock_aws

from conftest import load_lambda_handler

BUCKET = "test-media-bucket"


class FakeRekognitionClient:
    def __init__(self, labels):
        self._labels = labels
        self.last_request = None

    def detect_labels(self, **kwargs):
        self.last_request = kwargs
        return {"Labels": self._labels}


@pytest.fixture
def s3_client(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-3")
    with mock_aws():
        client = boto3.client("s3", region_name="eu-west-3")
        client.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": "eu-west-3"})
        client.put_object(Bucket=BUCKET, Key="processed/x-photo-thumb.jpg", Body=b"fake-thumbnail-bytes")
        yield client


def test_returns_labels_above_confidence_and_passes_through_state(s3_client):
    module = load_lambda_handler("analyze_image")
    module.rekognition = FakeRekognitionClient(
        labels=[
            {"Name": "Cat", "Confidence": 98.654},
            {"Name": "Animal", "Confidence": 91.2},
        ]
    )

    event = {"bucket": BUCKET, "key": "uploads/x-photo.jpg", "thumbnail_key": "processed/x-photo-thumb.jpg"}
    result = module.lambda_handler(event, None)

    assert result["labels"] == [
        {"name": "Cat", "confidence": 98.7},
        {"name": "Animal", "confidence": 91.2},
    ]
    # Pass-through fields from the previous pipeline step must survive.
    assert result["bucket"] == BUCKET
    assert result["thumbnail_key"] == "processed/x-photo-thumb.jpg"


def test_sends_thumbnail_bytes_not_s3_reference(s3_client):
    module = load_lambda_handler("analyze_image")
    fake = FakeRekognitionClient(labels=[])
    module.rekognition = fake

    module.lambda_handler({"bucket": BUCKET, "key": "uploads/x-photo.jpg", "thumbnail_key": "processed/x-photo-thumb.jpg"}, None)

    # Bytes, not S3Object: Rekognition's S3Object input requires the bucket
    # to be in the same region as the Rekognition endpoint, which isn't true
    # here (Rekognition isn't available in this stack's region at all).
    assert fake.last_request["Image"]["Bytes"] == b"fake-thumbnail-bytes"
    assert fake.last_request["MaxLabels"] == module.MAX_LABELS
    assert fake.last_request["MinConfidence"] == module.MIN_CONFIDENCE
