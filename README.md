# Serverless Media Analysis Pipeline

**Event-driven image processing on AWS Lambda, Step Functions, and API Gateway — deployed with Terraform and GitHub Actions.**

🌐 **Live:** https://media.martinscloud.be

---

## 📋 Project Overview

Upload a photo and a fully serverless pipeline takes over: a Lambda generates a thumbnail, Amazon Rekognition labels the contents, the result lands in DynamoDB, and an SNS notification confirms it's done — all visible live on the demo page below.

This is the companion piece to my [MartinsCloud portfolio site](https://www.martinscloud.be), which is deliberately VM-based (EC2, RDS→SQLite, CloudFormation). That project proved I can run a server. This one proves the other half: **event-driven serverless architecture, Terraform (a second IaC tool beyond CloudFormation), and a real CI/CD pipeline** — the three things I was explicitly still building toward.

---

## 🏗 Architecture

```
Browser (frontend on S3 + CloudFront, media.martinscloud.be)
  │
  ├─ GET  /api/images        → API Gateway (HTTP API) → Lambda get_images     → DynamoDB
  ├─ GET  /api/images/{id}   → API Gateway            → Lambda get_image      → DynamoDB
  └─ POST /api/uploads       → API Gateway            → Lambda presign_upload → returns S3 presigned PUT URL
                                                                                    │
Browser PUTs the file directly to S3 ─────────────────────────────────────────────┘
  │
  ▼
S3 (uploads/ prefix) ──EventBridge──▶ Step Functions (Standard workflow)
                                        1. process_image  (Pillow thumbnail  → S3 processed/)
                                        2. analyze_image  (Rekognition DetectLabels)
                                        3. save_metadata  (write result → DynamoDB)
                                        4. SNS topic → email ("upload processed")
```

Everything — frontend, API, and media files — is served from one CloudFront distribution under one domain, so there's no cross-origin request in play at all.

---

## 🔑 Key design decisions

- **Presigned S3 upload, not a Lambda-proxied one.** The browser uploads straight to S3 via a presigned PUT URL instead of routing the file through API Gateway/Lambda. Avoids API Gateway's 10 MB payload limit and keeps the upload Lambda's cold start (and cost) near zero.
- **Step Functions, not a Lambda calling Lambdas.** Chaining three Lambdas as Step Functions states instead of direct invocation gives visible execution history, per-step retries, and a clean failure path (an SNS alert + `Fail` state) — a real orchestration pattern, not just glue code.
- **S3 → EventBridge → Step Functions, no shim Lambda.** S3 publishes object-created events straight onto the default EventBridge bus; a rule filters for the `uploads/` prefix and starts the state machine directly. One less thing to maintain.
- **ACM + CloudFront here, Let's Encrypt on the EC2 project.** ACM only attaches to CloudFront/ALB, so it's the right tool now that CloudFront is in the picture — the opposite constraint from the EC2 project, where ACM wasn't an option without a load balancer.
- **Terraform, not CloudFormation.** The EC2 project already proved CloudFormation; this one deliberately uses a second IaC tool, with its own state backend (S3 + DynamoDB lock table) bootstrapped once and reused on every run.
- **GitHub OIDC, not access keys.** GitHub Actions assumes an IAM role via short-lived OIDC tokens (`terraform/modules/github_oidc`) — no long-lived AWS keys ever sit in GitHub secrets.
- **DynamoDB on-demand.** Same choice as the visitor counter on the EC2 project, but here for the opposite reason: that one has predictable low traffic so a fixed 1 RCU/WCU makes sense; this one has *unpredictable* demo traffic, so on-demand avoids either throttling a burst or paying for idle capacity.

---

## 💰 Cost (near-$0 by design)

| Component | Why it's ~free |
|---|---|
| Lambda | Permanent free tier (1M requests/month) |
| DynamoDB | On-demand, permanent free tier covers this volume |
| API Gateway (HTTP API) | Cheaper API type; fractions of a cent per demo request |
| Step Functions (Standard) | $0.025 per 1,000 state transitions — cents even after hundreds of test uploads |
| Rekognition `DetectLabels` | ~$1/1,000 images outside the 12-month free tier — trivial at portfolio scale |
| S3 + SNS (email) | Fractions of a cent per test run |
| CloudFront | Free tier covers 1 TB/month for 12 months, pennies after |

**Guardrails, not just hope:**
- AWS Budget alert at $5/month (tag-filtered to just this project's resources, so it doesn't get lost in the noise of other AWS spend).
- S3 lifecycle rule expires `uploads/`/`processed/` objects after 30 days.
- DynamoDB on-demand — no idle capacity charge if the demo goes quiet.

---

## 🛠 Technologies

- **Compute:** AWS Lambda (Python 3.12), Pillow layer built from PyPI manylinux wheels (no Docker)
- **Orchestration:** AWS Step Functions (Standard workflow), EventBridge
- **API:** API Gateway (HTTP API)
- **Storage:** S3 (uploads, processed thumbnails, static frontend), DynamoDB (on-demand)
- **AI:** Amazon Rekognition (`DetectLabels`)
- **Delivery:** CloudFront, ACM, Route53
- **Messaging:** SNS
- **IaC:** Terraform (S3 + DynamoDB remote state backend)
- **CI/CD:** GitHub Actions, OIDC federation to AWS (no stored access keys)
- **Testing:** pytest + moto (mocked AWS), one isolated unit test per Lambda handler
- **Observability:** CloudWatch dashboard (Lambda invocations/errors/duration, Step Functions success/failure), AWS Budgets

---

## 📂 Repo layout

```
serverless-media-pipeline/
├── terraform/              # root config + modules (storage, database, lambda,
│                            #   step_functions, api_gateway, sns, cloudfront,
│                            #   budget, monitoring, github_oidc)
│   └── bootstrap/           # one-time: Terraform state S3 bucket + lock table
├── lambdas/                 # one directory per function, each with its own handler.py
├── step_functions/           # ASL state machine definition (Terraform templatefile)
├── frontend/                 # plain HTML/CSS/JS upload form + gallery
├── tests/                    # pytest + moto unit tests, one file per Lambda
├── scripts/build_pillow_layer.sh
└── .github/workflows/        # ci.yml (PR checks), deploy.yml (main branch)
```

---

## 💻 Local development

```bash
git clone https://github.com/MartijnMGit/serverless-media-pipeline.git
cd serverless-media-pipeline

python -m venv .venv
source .venv/Scripts/activate    # Windows Git Bash
pip install -r tests/requirements-test.txt
pytest tests/ -v
```

To plan/apply infrastructure locally:

```bash
bash scripts/build_pillow_layer.sh   # must run before any plan/apply
cd terraform
terraform init
terraform plan   -var="notification_email=you@example.com"
terraform apply  -var="notification_email=you@example.com"
```

---

## ✨ Highlights & challenges

- Caught a real bug via the test suite before it ever reached production: DynamoDB's resource API rejects native Python floats, so Rekognition's confidence scores needed converting to `Decimal` before being written — pytest + moto surfaced this locally in seconds instead of failing silently in a live Step Functions execution.
- Routed the frontend, API, and media files through a single CloudFront distribution and domain, which removes CORS from the picture entirely rather than configuring around it.
- Replaced a Terraform `null_resource` + `local-exec` build step for the Pillow layer with a plain shell script once I realized `archive_file` zips its source directory during `plan`, not just `apply` — the local-exec approach would only produce the directory on `apply`, breaking a clean `plan` on a fresh checkout.
- Scoped the GitHub Actions OIDC trust policy to exactly two subjects (`ref:refs/heads/main` and `pull_request`) instead of the whole repo wildcard, so forks and arbitrary branches can't assume the deploy role.

---

## 📸 Screenshots

_Added after first live deploy._
