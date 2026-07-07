import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from conftest import load_lambda_handler

BUCKET = "test-media-bucket"
ORIGINAL_KEY = "uploads/x-photo.jpg"
THUMBNAIL_KEY = "processed/x-photo-thumb.jpg"


class FakeRekognitionClient:
    def __init__(self, labels=None, moderation_labels=None):
        self._labels = labels or []
        self._moderation_labels = moderation_labels or []
        self.last_request = None

    def detect_labels(self, **kwargs):
        self.last_request = kwargs
        return {"Labels": self._labels}

    def detect_moderation_labels(self, **kwargs):
        return {"ModerationLabels": self._moderation_labels}


@pytest.fixture
def s3_client(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-3")
    with mock_aws():
        client = boto3.client("s3", region_name="eu-west-3")
        client.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": "eu-west-3"})
        client.put_object(Bucket=BUCKET, Key=ORIGINAL_KEY, Body=b"fake-original-bytes")
        client.put_object(Bucket=BUCKET, Key=THUMBNAIL_KEY, Body=b"fake-thumbnail-bytes")
        yield client


EVENT = {"bucket": BUCKET, "key": ORIGINAL_KEY, "thumbnail_key": THUMBNAIL_KEY}


def test_returns_labels_above_confidence_and_passes_through_state(s3_client):
    module = load_lambda_handler("analyze_image")
    module.rekognition = FakeRekognitionClient(
        labels=[
            {"Name": "Cat", "Confidence": 98.654},
            {"Name": "Animal", "Confidence": 91.2},
        ]
    )

    result = module.lambda_handler(dict(EVENT), None)

    assert result["labels"] == [
        {"name": "Cat", "confidence": 98.7},
        {"name": "Animal", "confidence": 91.2},
    ]
    # Pass-through fields from the previous pipeline step must survive.
    assert result["bucket"] == BUCKET
    assert result["thumbnail_key"] == THUMBNAIL_KEY


def test_sends_thumbnail_bytes_not_s3_reference(s3_client):
    module = load_lambda_handler("analyze_image")
    fake = FakeRekognitionClient()
    module.rekognition = fake

    module.lambda_handler(dict(EVENT), None)

    # Bytes, not S3Object: Rekognition's S3Object input requires the bucket
    # to be in the same region as the Rekognition endpoint, which isn't true
    # here (Rekognition isn't available in this stack's region at all).
    assert fake.last_request["Image"]["Bytes"] == b"fake-thumbnail-bytes"
    assert fake.last_request["MaxLabels"] == module.MAX_LABELS
    assert fake.last_request["MinConfidence"] == module.MIN_CONFIDENCE


def test_flagged_upload_is_rejected_and_deleted(s3_client):
    module = load_lambda_handler("analyze_image")
    module.rekognition = FakeRekognitionClient(
        moderation_labels=[{"Name": "Explicit Nudity", "Confidence": 97.0}]
    )

    with pytest.raises(module.ModerationRejected, match="Explicit Nudity"):
        module.lambda_handler(dict(EVENT), None)

    # Both objects must be gone so the content can never be served.
    for key in (ORIGINAL_KEY, THUMBNAIL_KEY):
        with pytest.raises(ClientError):
            s3_client.head_object(Bucket=BUCKET, Key=key)


def test_clean_upload_is_not_deleted(s3_client):
    module = load_lambda_handler("analyze_image")
    module.rekognition = FakeRekognitionClient(labels=[{"Name": "Cat", "Confidence": 99.0}])

    module.lambda_handler(dict(EVENT), None)

    s3_client.head_object(Bucket=BUCKET, Key=ORIGINAL_KEY)
    s3_client.head_object(Bucket=BUCKET, Key=THUMBNAIL_KEY)