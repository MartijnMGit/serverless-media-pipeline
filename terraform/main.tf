module "storage" {
  source                = "./modules/storage"
  project               = var.project
  upload_retention_days = var.upload_retention_days
}

module "database" {
  source  = "./modules/database"
  project = var.project
}

module "sns" {
  source             = "./modules/sns"
  project            = var.project
  notification_email = var.notification_email
}

# --- Pipeline Lambdas (invoked by Step Functions, not API Gateway) ---

module "lambda_process_image" {
  source        = "./modules/lambda"
  function_name = "${var.project}-process-image"
  source_dir    = "${path.module}/../lambdas/process_image"
  timeout       = 30
  memory_size   = 512
  layers        = [aws_lambda_layer_version.pillow.arn]

  environment_variables = {
    MEDIA_BUCKET = module.storage.media_bucket_name
  }

  policy_statements = [
    {
      sid       = "ReadWriteMediaBucket"
      actions   = ["s3:GetObject", "s3:PutObject"]
      resources = ["${module.storage.media_bucket_arn}/*"]
    }
  ]
}

module "lambda_analyze_image" {
  source        = "./modules/lambda"
  function_name = "${var.project}-analyze-image"
  source_dir    = "${path.module}/../lambdas/analyze_image"
  timeout       = 30
  memory_size   = 256

  policy_statements = [
    {
      sid       = "ReadMediaBucket"
      actions   = ["s3:GetObject"]
      resources = ["${module.storage.media_bucket_arn}/*"]
    },
    {
      sid       = "DetectLabels"
      actions   = ["rekognition:DetectLabels"]
      resources = ["*"]
    }
  ]
}

module "lambda_save_metadata" {
  source        = "./modules/lambda"
  function_name = "${var.project}-save-metadata"
  source_dir    = "${path.module}/../lambdas/save_metadata"
  timeout       = 10
  memory_size   = 128

  environment_variables = {
    RESULTS_TABLE = module.database.table_name
  }

  policy_statements = [
    {
      sid       = "WriteResultsTable"
      actions   = ["dynamodb:PutItem"]
      resources = [module.database.table_arn]
    }
  ]
}

module "step_functions" {
  source            = "./modules/step_functions"
  project           = var.project
  process_image_arn = module.lambda_process_image.function_arn
  analyze_image_arn = module.lambda_analyze_image.function_arn
  save_metadata_arn = module.lambda_save_metadata.function_arn
  sns_topic_arn     = module.sns.topic_arn
  media_bucket_id   = module.storage.media_bucket_id
  media_bucket_arn  = module.storage.media_bucket_arn
}

# --- API Lambdas (invoked by API Gateway) ---

module "lambda_presign_upload" {
  source        = "./modules/lambda"
  function_name = "${var.project}-presign-upload"
  source_dir    = "${path.module}/../lambdas/presign_upload"
  timeout       = 10
  memory_size   = 128

  environment_variables = {
    MEDIA_BUCKET = module.storage.media_bucket_name
  }

  policy_statements = [
    {
      sid       = "PresignPutObject"
      actions   = ["s3:PutObject"]
      resources = ["${module.storage.media_bucket_arn}/uploads/*"]
    }
  ]
}

module "lambda_get_images" {
  source        = "./modules/lambda"
  function_name = "${var.project}-get-images"
  source_dir    = "${path.module}/../lambdas/get_images"
  timeout       = 10
  memory_size   = 128

  environment_variables = {
    RESULTS_TABLE = module.database.table_name
    DOMAIN_NAME   = var.domain_name
  }

  policy_statements = [
    {
      sid       = "ScanResultsTable"
      actions   = ["dynamodb:Scan"]
      resources = [module.database.table_arn]
    }
  ]
}

module "lambda_get_image" {
  source        = "./modules/lambda"
  function_name = "${var.project}-get-image"
  source_dir    = "${path.module}/../lambdas/get_image"
  timeout       = 10
  memory_size   = 128

  environment_variables = {
    RESULTS_TABLE = module.database.table_name
    DOMAIN_NAME   = var.domain_name
  }

  policy_statements = [
    {
      sid       = "GetResultsItem"
      actions   = ["dynamodb:GetItem"]
      resources = [module.database.table_arn]
    }
  ]
}

module "api_gateway" {
  source  = "./modules/api_gateway"
  project = var.project

  routes = [
    {
      route_key            = "POST /api/uploads"
      lambda_function_name = module.lambda_presign_upload.function_name
      lambda_invoke_arn    = module.lambda_presign_upload.invoke_arn
    },
    {
      route_key            = "GET /api/images"
      lambda_function_name = module.lambda_get_images.function_name
      lambda_invoke_arn    = module.lambda_get_images.invoke_arn
    },
    {
      route_key            = "GET /api/images/{id}"
      lambda_function_name = module.lambda_get_image.function_name
      lambda_invoke_arn    = module.lambda_get_image.invoke_arn
    },
  ]
}

module "cloudfront" {
  source = "./modules/cloudfront"
  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }

  project                              = var.project
  domain_name                          = var.domain_name
  root_domain_zone_id                  = var.root_domain_zone_id
  frontend_bucket_id                   = module.storage.frontend_bucket_id
  frontend_bucket_arn                  = module.storage.frontend_bucket_arn
  frontend_bucket_regional_domain_name = module.storage.frontend_bucket_regional_domain_name
  media_bucket_id                      = module.storage.media_bucket_id
  media_bucket_arn                     = module.storage.media_bucket_arn
  media_bucket_regional_domain_name    = "${module.storage.media_bucket_name}.s3.${var.region}.amazonaws.com"
  api_domain_name                      = replace(replace(module.api_gateway.api_endpoint, "https://", ""), "/", "")
}

module "budget" {
  source             = "./modules/budget"
  project            = var.project
  limit_usd          = var.budget_limit_usd
  notification_email = var.notification_email

  breaker_role_names = [
    module.lambda_process_image.role_name,
    module.lambda_analyze_image.role_name,
    module.lambda_save_metadata.role_name,
    module.lambda_presign_upload.role_name,
    module.lambda_get_images.role_name,
    module.lambda_get_image.role_name,
  ]
}

module "github_oidc" {
  source      = "./modules/github_oidc"
  project     = var.project
  github_org  = var.github_org
  github_repo = var.github_repo
}

module "monitoring" {
  source  = "./modules/monitoring"
  project = var.project
  region  = var.region

  lambda_function_names = [
    module.lambda_process_image.function_name,
    module.lambda_analyze_image.function_name,
    module.lambda_save_metadata.function_name,
    module.lambda_presign_upload.function_name,
    module.lambda_get_images.function_name,
    module.lambda_get_image.function_name,
  ]

  state_machine_arn = module.step_functions.state_machine_arn
}
