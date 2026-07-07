import boto3

# Rekognition isn't available in every region (notably not in eu-west-3,
# where the rest of this stack lives), and its S3Object image input
# requires the bucket to be in the *same* region as the Rekognition
# endpoint - cross-region S3Object references aren't supported. Rather
# than move the whole stack, read the thumbnail bytes locally (same-region
# S3 client) and send them inline to a Rekognition client pinned at a
# region that supports it.
REKOGNITION_REGION = "eu-west-1"

s3 = boto3.client("s3")
rekognition = boto3.client("rekognition", region_name=REKOGNITION_REGION)

MAX_LABELS = 10
MIN_CONFIDENCE = 70


def lambda_handler(event, context):
    bucket = event["bucket"]
    thumbnail_key = event["thumbnail_key"]

    image_bytes = s3.get_object(Bucket=bucket, Key=thumbnail_key)["Body"].read()

    response = rekognition.detect_labels(
        Image={"Bytes": image_bytes},
        MaxLabels=MAX_LABELS,
        MinConfidence=MIN_CONFIDENCE,
    )

    labels = [
        {"name": label["Name"], "confidence": round(label["Confidence"], 1)}
        for label in response.get("Labels", [])
    ]

    return {**event, "labels": labels}
