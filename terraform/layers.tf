# Pillow ships prebuilt manylinux wheels on PyPI, so the layer is assembled
# with a plain `pip install --platform` (see scripts/build_pillow_layer.sh) -
# no Docker, no compiling. That script must run before any plan/apply,
# because archive_file zips this directory during *plan* already (not just
# apply), so the directory has to exist up front rather than be produced by
# a Terraform-triggered build step.
data "archive_file" "pillow_layer" {
  type        = "zip"
  source_dir  = "${path.module}/../.build/pillow-layer"
  output_path = "${path.module}/../.build/pillow-layer.zip"
}

resource "aws_lambda_layer_version" "pillow" {
  layer_name          = "${var.project}-pillow"
  filename            = data.archive_file.pillow_layer.output_path
  source_code_hash    = data.archive_file.pillow_layer.output_base64sha256
  compatible_runtimes = ["python3.12"]
}
