import boto3
import pytest
from moto import mock_aws

from conftest import load_lambda_handler

TABLE = "test-results-table"


@pytest.fixture
def handler_module(monkeypatch):
    monkeypatch.setenv("RESULTS_TABLE", TABLE)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-3")
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="eu-west-3")
        dynamodb.create_table(
            TableName=TABLE,
            KeySchema=[{"AttributeName": "image_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "image_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield load_lambda_handler("save_metadata")


def test_writes_item_and_returns_summary(handler_module):
    event = {
        "image_id": "abc-123",
        "key": "uploads/abc-123-photo.jpg",
        "thumbnail_key": "processed/abc-123-photo-thumb.jpg",
        "labels": [{"name": "Cat", "confidence": 98.7}],
    }

    result = handler_module.lambda_handler(event, None)

    assert result == {"image_id": "abc-123", "status": "COMPLETE", "labels": event["labels"]}

    dynamodb = boto3.resource("dynamodb", region_name="eu-west-3")
    item = dynamodb.Table(TABLE).get_item(Key={"image_id": "abc-123"})["Item"]
    assert item["status"] == "COMPLETE"
    assert item["original_key"] == event["key"]
    assert item["thumbnail_key"] == event["thumbnail_key"]
    # DynamoDB stores confidence as Decimal; comparing Decimal('98.7') (exact)
    # directly to the float 98.7 (a binary approximation) would spuriously
    # fail, so cast back to float first.
    assert item["labels"][0]["name"] == "Cat"
    assert float(item["labels"][0]["confidence"]) == 98.7
    assert "processed_at" in item


def test_defaults_labels_to_empty_list(handler_module):
    event = {"image_id": "no-labels", "key": "uploads/no-labels-photo.jpg", "thumbnail_key": "processed/x-thumb.jpg"}

    result = handler_module.lambda_handler(event, None)

    assert result["labels"] == []
