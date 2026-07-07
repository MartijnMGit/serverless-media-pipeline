# On-demand billing: same choice as the visitor counter in the MartinsCloud
# project's DynamoDB table, but here request volume is unpredictable (driven
# by whoever tries the demo), so no capacity planning beats guessing an RCU/WCU.
resource "aws_dynamodb_table" "results" {
  name         = "${var.project}-results"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "image_id"

  attribute {
    name = "image_id"
    type = "S"
  }
}
