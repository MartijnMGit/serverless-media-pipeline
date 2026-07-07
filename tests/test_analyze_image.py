from conftest import load_lambda_handler


class FakeRekognitionClient:
    def __init__(self, labels):
        self._labels = labels
        self.last_request = None

    def detect_labels(self, **kwargs):
        self.last_request = kwargs
        return {"Labels": self._labels}


def test_returns_labels_above_confidence_and_passes_through_state():
    module = load_lambda_handler("analyze_image")
    module.rekognition = FakeRekognitionClient(
        labels=[
            {"Name": "Cat", "Confidence": 98.654},
            {"Name": "Animal", "Confidence": 91.2},
        ]
    )

    event = {"bucket": "b", "key": "uploads/x-photo.jpg", "thumbnail_key": "processed/x-photo-thumb.jpg"}
    result = module.lambda_handler(event, None)

    assert result["labels"] == [
        {"name": "Cat", "confidence": 98.7},
        {"name": "Animal", "confidence": 91.2},
    ]
    # Pass-through fields from the previous pipeline step must survive.
    assert result["bucket"] == "b"
    assert result["thumbnail_key"] == "processed/x-photo-thumb.jpg"


def test_calls_rekognition_with_correct_s3_object():
    module = load_lambda_handler("analyze_image")
    fake = FakeRekognitionClient(labels=[])
    module.rekognition = fake

    module.lambda_handler({"bucket": "my-bucket", "key": "uploads/x-photo.jpg"}, None)

    assert fake.last_request["Image"]["S3Object"] == {"Bucket": "my-bucket", "Name": "uploads/x-photo.jpg"}
    assert fake.last_request["MaxLabels"] == module.MAX_LABELS
    assert fake.last_request["MinConfidence"] == module.MIN_CONFIDENCE
