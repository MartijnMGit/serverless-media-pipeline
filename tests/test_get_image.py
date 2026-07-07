import json

import boto3
import pytest
from moto import mock_aws

from conftest import load_lambda_handler

TABLE = "test-results-table"
DOMAIN = "media.example.com"


@pytest.fixture
def table(monkeypatch):
    monkeypatch.setenv("RESULTS_TABLE", TABLE)
    monkeypatch.setenv("DOMAIN_NAME", DOMAIN)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-3")
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="eu-west-3")
        dynamodb.create_table(
            TableName=TABLE,
            KeySchema=[{"AttributeName": "image_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "image_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield dynamodb.Table(TABLE)


def test_returns_item_with_public_urls(table):
    table.put_item(
        Item={
            "image_id": "abc-123",
            "status": "COMPLETE",
            "original_key": "uploads/abc-123-photo.jpg",
            "thumbnail_key": "processed/abc-123-photo-thumb.jpg",
        }
    )

    module = load_lambda_handler("get_image")
    response = module.lambda_handler({"pathParameters": {"id": "abc-123"}}, None)

    assert response["statusCode"] == 200
    item = json.loads(response["body"])
    assert item["thumbnail_url"] == f"https://{DOMAIN}/media/processed/abc-123-photo-thumb.jpg"
    assert item["original_url"] == f"https://{DOMAIN}/media/uploads/abc-123-photo.jpg"


def test_returns_404_for_unknown_id(table):
    module = load_lambda_handler("get_image")
    response = module.lambda_handler({"pathParameters": {"id": "does-not-exist"}}, None)
    assert response["statusCode"] == 404


def test_returns_400_when_id_missing(table):
    module = load_lambda_handler("get_image")
    response = module.lambda_handler({"pathParameters": {}}, None)
    assert response["statusCode"] == 400
