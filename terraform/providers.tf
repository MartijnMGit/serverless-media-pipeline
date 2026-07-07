terraform {
  required_version = ">= 1.5"

  backend "s3" {
    bucket         = "serverless-media-pipeline-tfstate"
    key            = "main/terraform.tfstate"
    region         = "eu-west-3"
    dynamodb_table = "serverless-media-pipeline-tf-lock"
    encrypt        = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = "serverless-media-pipeline"
      ManagedBy = "terraform"
    }
  }
}

# ACM certificates for CloudFront must live in us-east-1 regardless of
# where everything else is deployed.
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      Project   = "serverless-media-pipeline"
      ManagedBy = "terraform"
    }
  }
}
