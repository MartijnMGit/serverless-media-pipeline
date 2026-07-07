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
MODERATION_MIN_CONFIDENCE = 60


class ModerationRejected(Exception):
    """Raised when Rekognition flags the upload as unsafe content."""


def lambda_handler(event, context):
    bucket = event["bucket"]
    key = event["key"]
    thumbnail_key = event["thumbnail_key"]

    image_bytes = s3.get_object(Bucket=bucket, Key=thumbnail_key)["Body"].read()

    # Anyone on the internet can upload here and the result is displayed
    # publicly, so unsafe content has to be caught before it reaches the
    # gallery. Flagged uploads are deleted outright (both the original and
    # the thumbnail); no DynamoDB record is ever written for them because
    # save_metadata only runs after this step succeeds.
    moderation = rekognition.detect_moderation_labels(
        Image={"Bytes": image_bytes},
        MinConfidence=MODERATION_MIN_CONFIDENCE,
    )
    flagged = [m["Name"] for m in moderation.get("ModerationLabels", [])]
    if flagged:
        s3.delete_object(Bucket=bucket, Key=key)
        s3.delete_object(Bucket=bucket, Key=thumbnail_key)
        raise ModerationRejected(f"Upload {key} rejected and deleted: {', '.join(flagged)}")

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
