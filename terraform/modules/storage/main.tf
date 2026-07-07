# Media bucket holds two prefixes: uploads/ (raw browser uploads) and
# processed/ (generated thumbnails). One bucket keeps the module simple;
# prefixes are enough to separate lifecycle/read patterns.
resource "aws_s3_bucket" "media" {
  bucket = "${var.project}-media"
}

resource "aws_s3_bucket_public_access_block" "media" {
  bucket                  = aws_s3_bucket.media.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_cors_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  cors_rule {
    allowed_methods = ["PUT", "GET"]
    allowed_origins = ["*"]
    allowed_headers = ["*"]
    max_age_seconds = 3000
  }
}

# Cost control: nobody needs a portfolio demo upload to live forever.
resource "aws_s3_bucket_lifecycle_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  rule {
    id     = "expire-uploads"
    status = "Enabled"
    filter {
      prefix = "uploads/"
    }
    expiration {
      days = var.upload_retention_days
    }
  }

  rule {
    id     = "expire-processed"
    status = "Enabled"
    filter {
      prefix = "processed/"
    }
    expiration {
      days = var.upload_retention_days
    }
  }
}

# Static frontend bucket, private — only reachable via CloudFront's
# Origin Access Control (no public bucket policy needed).
resource "aws_s3_bucket" "frontend" {
  bucket = "${var.project}-frontend"
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket                  = aws_s3_bucket.frontend.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
