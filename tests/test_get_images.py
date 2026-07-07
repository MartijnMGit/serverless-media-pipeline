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


def test_returns_images_with_public_urls_sorted_newest_first(table):
    table.put_item(Item={"image_id": "old", "uploaded_at": "2026-01-01T00:00:00Z", "thumbnail_key": "processed/old-thumb.jpg"})
    table.put_item(Item={"image_id": "new", "uploaded_at": "2026-02-01T00:00:00Z", "thumbnail_key": "processed/new-thumb.jpg"})

    module = load_lambda_handler("get_images")
    response = module.lambda_handler({}, None)

    assert response["statusCode"] == 200
    images = json.loads(response["body"])["images"]
    assert [i["image_id"] for i in images] == ["new", "old"]
    assert images[0]["thumbnail_url"] == f"https://{DOMAIN}/media/processed/new-thumb.jpg"


def test_returns_empty_list_when_no_uploads(table):
    module = load_lambda_handler("get_images")
    response = module.lambda_handler({}, None)

    assert json.loads(response["body"])["images"] == []
