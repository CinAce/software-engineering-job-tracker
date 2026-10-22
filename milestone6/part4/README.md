# Part 4 — Measurement and evaluation

Run from the repository root on the **same Mac** used for the original Module 4 testing. Nothing in this folder creates new cloud resources or modifies your teammate's Part 2 workflow.

## 0. Check the live Cloud Run service and the $5 budget

GCP project: `itc531-module7`; region `us-central1`; service `itc531-job-tracker`. **Your $5 budget is an alert, not a guaranteed hard limit.** This script sends roughly 650 sequential requests; do not run repeatedly for no reason. Abort if you see billing issues.

## 1. Start the actual local project with Docker Compose

The main `nginx/gateway.conf` **intercepts `/health`** and returns a gateway-only status, and it **does not forward `/tasks`**. Therefore using the root `http://localhost:8000` gateway for latency would compare different functionality. The override exposes the **FastAPI app itself** on `127.0.0.1:8013`, leaving the existing gateway configuration untouched.

```bash
cd /Users/ace/Class/Fall2026/ITC531/software-engineering-job-tracker

docker compose --env-file .env.local \
  -f compose.yml \
  -f milestone6/part4/compose.benchmark.yml \
  up -d --wait

docker compose --env-file .env.local \
  -f compose.yml \
  -f milestone6/part4/compose.benchmark.yml ps

# If the local RustFS bucket has not been initialized, create it safely:
docker compose --env-file .env.local -f compose.yml -f milestone6/part4/compose.benchmark.yml exec -T app \
  python -c 'from app.ports.storage import ObjectStore; ObjectStore().ensure_bucket()'

curl -fsS http://127.0.0.1:8013/health
```

Expected: application JSON with database and local storage `ok`. If the command errors because local secrets or port 9000/8000 are missing/in use, **stop** and share the error. Do not edit credentials into tracked files or destroy another project's containers. The Part 3 monitoring stack (port 8012) is separate and can remain running.

**Fallback if the full local stack is unavailable:** the Part 3 monitoring stack you already started is a real Compose deployment and exposes the same FastAPI image at `http://127.0.0.1:8012`. You may run the benchmark with `--local http://127.0.0.1:8012` instead, but the report will explicitly flag that this local health check skips object storage, unlike GCP. The full Compose option above offers the better comparison.

## 2. Measure local and deployed latency three times (automated)

```bash
set -o pipefail
python3 milestone6/part4/measure_latency.py \
  2>&1 | tee milestone6/evidence/part4-latency-console.txt
```

The script reads the deployed URL from `gcloud run services describe`. It creates a uniquely named **demo user in each environment**, logs in, then sends only `GET` requests. It measures `GET /health` and authenticated `GET /tasks` in each environment. It uses 8 untimed warmups, 50 timed sequential requests per repetition, **three** repetitions, and the median of those three p50 and p95 values. Expected ~600 timed requests + warmups. It fails rather than recording invalid HTTP statuses or a degraded `/health` response. Login credentials and authorization tokens stay in RAM.

Evidence/output generated:

- `milestone6/MEASUREMENT.md` — complete latency table (real data only), comparison notes, model comparison, reversal criterion. Billing starts as PENDING until verified.
- `milestone6/evidence/part4-latency-raw.csv` — individual observations.
- `milestone6/evidence/part4-latency-summary.json` — independently checkable repetitions and medians, plus raw TCP connect probes.
- `milestone6/evidence/part4-latency-console.txt` — the invocation and summary output.

If local health is degraded, fix the local stack before measuring. If Cloud Run storage is degraded, do not report a successful latency run. Cloud Run's temporary SQLite may reset a test user when a new instance is created; a 401 will abort the test rather than silently collect error latencies.

## 3. Record **actual** billing (manual GCP Billing Reports reading required)

Google Cloud's `gcloud billing budgets` command verifies budget alerts; it does **not** show a reliable itemized live billing total. Open [Google Cloud Billing Reports](https://console.cloud.google.com/billing) in your signed-in browser, select project `itc531-module7`, choose **Charge period** from **Oct 18, 2026** to the observation date, **Group by Service**, and show credits. Screenshot the displayed total and visible filter settings as:

`milestone6/evidence/gcp-billing-report.png`

Before sharing the screenshot in a GitHub repository, **crop or redact your billing account ID, payment details, private email, and unrelated project names**, but keep the project, total, selected date range and timestamp visible. Save it as `gcp-billing-report.png` (or PDF).

Then enter the actual amount/time range interactively (no placeholder figures to accidentally copy):

```bash
python3 milestone6/part4/fill_billing.py
```

Supply the amount, timestamp and period displayed in your account. Don't treat a delayed `$0.00` as proof that no charges will arrive. This edits Part 4b of the existing report only; it does **not** rerun the benchmark.

Reference: https://docs.cloud.google.com/billing/docs/how-to/reports (read October 18, 2026).

## 4. Important Milestone 3 mismatch

Your submitted Milestone 3 `RISKS.md` uses **800 ms p95 on GET `/api/v1/applications` due to cold starts** as its explicit decision-reversal threshold. The repository and deployed image used for Milestone 6 do not implement that route. The benchmark records the route's actual HTTP status and does NOT pretend that `GET /tasks` proves the original criterion passed or failed. `GET /tasks` is the current, authenticated application-list analogue and is shown as a reference only. Also, **warm** p95 doesn't identify cold starts. The chosen cloud shape is now Google Cloud Run rather than proposed AWS Lambda/Fargate. Have the team flag this scope change to the instructor or explicitly approve a revised criterion.

## 5. Save, share, and stop locally

```bash
# After verifying the billing screenshot/report:
git add -- milestone6/MEASUREMENT.md milestone6/part4/ \
  milestone6/evidence/part4-latency-raw.csv \
  milestone6/evidence/part4-latency-summary.json \
  milestone6/evidence/part4-latency-console.txt \
  milestone6/evidence/gcp-billing-report.png

git diff --cached --check
```

Commit/push after review, and coordinate with teammate first if they have changed main. You can stop *local* monitoring and benchmark services without touching GCP:

```bash
# Stop just root local Compose project (no --volumes, preserves local DB):
docker compose --env-file .env.local -f compose.yml -f milestone6/part4/compose.benchmark.yml down
# Separate local Part 3 monitoring stack (if done):
docker compose -f milestone6/monitoring/compose.yml down
```

**Do not run `bash scripts/cloud-down.sh gcp` yet**; the current GCP adapter would also remove shared Module 7 HMAC credentials and service account, and the team still needs to coordinate final teardown/24-hour audit.
