import boto3

rekognition = boto3.client("rekognition")

MAX_LABELS = 10
MIN_CONFIDENCE = 70


def lambda_handler(event, context):
    bucket = event["bucket"]
    key = event["key"]

    response = rekognition.detect_labels(
        Image={"S3Object": {"Bucket": bucket, "Name": key}},
        MaxLabels=MAX_LABELS,
        MinConfidence=MIN_CONFIDENCE,
    )

    labels = [
        {"name": label["Name"], "confidence": round(label["Confidence"], 1)}
        for label in response.get("Labels", [])
    ]

    return {**event, "labels": labels}
