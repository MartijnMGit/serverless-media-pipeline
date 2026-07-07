#!/usr/bin/env bash
# Assembles the Pillow Lambda layer from prebuilt manylinux wheels (no
# Docker, no compiling). Must run before any `terraform plan` or `apply`,
# since Terraform zips this directory as part of planning, not applying.
set -euo pipefail

cd "$(dirname "$0")/.."

rm -rf .build/pillow-layer
mkdir -p .build/pillow-layer/python

pip install \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all: \
  --target .build/pillow-layer/python \
  -r lambdas/process_image/requirements.txt

echo "Pillow layer built at .build/pillow-layer"
