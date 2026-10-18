# Milestone 6 — Part 4: Measurement and Evaluation

## 4a. Warm request latency: local vs deployed

**Method:** Measured on the same Mac using the Python standard library's persistent HTTP(S) connections. The local application uses the separately started Part 3 monitoring Compose stack on port 8012, with local SQLite and storage check disabled; this differs from GCP's GCS-backed health route. Cloud is the deployed Google Cloud Run FastAPI service. Each endpoint/environment has 3 independent repetitions, with 8 discarded warmup requests and 50 timed requests per repetition. Samples are sequential, HTTP 200 responses only; any unexpected status aborts the run. All percentiles use linearly interpolated p50/p95, and the headline number is the **median of the three repetitions**.

- Measured at UTC: 2026-10-18T23:12:22+00:00
- Local URL: `http://127.0.0.1:8012`
- Deployed URL: `https://itc531-job-tracker-k7misaiyja-uc.a.run.app`
- Endpoints: `GET /health` (health/root workload group) and authenticated `GET /tasks` (task workload group), the two busiest workload categories estimated in Milestone 3 `WORKLOAD_PROFILE.md` (9,000 and 3,000 requests/month respectively).
- The benchmark creates one temporary demo user per environment, logs in, and tests **read-only** `GET /tasks`. The login token is never written to evidence files.
- Local runs against the Part 3 monitoring Compose stack with local SQLite and no storage connectivity check; Cloud Run uses GCS and ephemeral SQLite. Their database and storage dependencies differ, so response-time differences are not attributable to network alone.

| Environment | Endpoint | Rep 1 p50 / p95 (ms) | Rep 2 p50 / p95 (ms) | Rep 3 p50 / p95 (ms) | Median p50 (ms) | Median p95 (ms) |
|---|---|---:|---:|---:|---:|---:|
| local | `GET /health` | 1.13 / 2.05 | 1.21 / 1.83 | 1.20 / 1.73 | 1.20 | 1.83 |
| cloud | `GET /health` | 137.06 / 180.18 | 155.69 / 308.70 | 135.54 / 270.74 | 137.06 | 270.74 |
| local | `GET /tasks` | 1.94 / 2.20 | 1.94 / 2.63 | 2.00 / 2.81 | 1.94 | 2.63 |
| cloud | `GET /tasks` | 38.95 / 45.86 | 39.69 / 58.39 | 44.28 / 58.91 | 39.69 | 58.39 |

### Network round-trip contribution

We measured five **new TCP connections** to each environment from the same Mac. The difference in median TCP-connect time is a rough **one-RTT proxy to the Google edge**, not a precise decomposition of HTTP latency. The timed HTTP requests reused persistent connections, so TLS setup and connection establishment were intentionally excluded after warmup.

- Local median TCP connect: **0.91 ms**
- Cloud median TCP connect: **17.47 ms**
- Rough network RTT proxy: **16.56 ms** extra (cloud minus local).
- `GET /health` end-to-end median-p50 difference: **+135.86 ms** (cloud minus local). The 16.56 ms TCP proxy is approximately 12% of this delta, but should NOT be treated as a measured fraction caused by network.
- `GET /tasks` end-to-end median-p50 difference: **+37.75 ms** (cloud minus local). The 16.56 ms TCP proxy is approximately 44% of this delta, but should NOT be treated as a measured fraction caused by network.

**Separating network from server processing:** Run a second load generator inside `us-central1` against the same Cloud Run service and compare it with results from the Mac; or capture per-request server-side processing durations using application tracing and request IDs. Those methods would isolate network contribution more directly. The TCP proxy alone cannot determine exact shares. The comparison also includes different storage backends and Mac ARM-emulation overhead.

**Evidence:** `evidence/part4-latency-raw.csv`, `evidence/part4-latency-summary.json`, `evidence/part4-latency-console.txt`; runner `part4/measure_latency.py`. The benchmark Compose override was prepared but not used.

## 4b. Cost: Google Cloud billing versus the Milestone 3 model

**Original Milestone 3 model:** `milestone3/COST_MODEL.md` assumed AWS `us-east-1`, 15,000 requests/month, 256 MB and 120 ms Lambda duration, and estimated **$0.025/month** for Lambda + API Gateway versus **$31.28/month** for Fargate + ALB; these were forecasts before free allowances, not observed bills.

**Deployed solution:** Google Cloud Run in `us-central1` with 0 minimum and 1 maximum instance, Google Cloud Storage, three Secret Manager secrets, and ephemeral SQLite. The configuration uses a different provider, storage service mix, compute shape, and time horizon from the original AWS model.

**Actual Google Cloud billing reported:** **$0.0000 USD** for GCP project `itc531-module7`, as observed **October 18, 2026, 7:06 PM EDT**.

**Selected time range and filter:** **October 18–31, 2026 (charges reported through October 18)**, `itc531-module7` project, grouped by Service, including applicable credits/discounts. Screenshot: `milestone6/evidence/gcp-billing-report.png`. A project total can include Module 7 and other demonstrations in that same window; it must not be mislabeled as costs of the Job Tracker alone.

**Variance:** A numerical AWS-versus-GCP difference is **not a like-for-like variance**; the actual $0.0000 is a project-period GCP charge, while $0.025 and $31.28 are monthly AWS models for different infrastructure and a hypothetical 15,000 requests. The main reasons for divergence are scale-to-zero instead of an always-on Fargate task and ALB, GCP's allowance and credit structure, regional prices, billed resources (Cloud Storage / Secret Manager / logging / egress) that AWS's stateless examples treat differently, and the small demonstration traffic volume. Check the screenshot for which line items actually have a charge; do not assume they were all free. Billing reports can lag fresh usage.

**Measurement method:** Google Cloud Console → Billing → Reports; Charge period starting October 18, 2026; project filter `itc531-module7`; group by Service. Read the filtered subtotal after credits and screenshot date/time and filters. See https://docs.cloud.google.com/billing/docs/how-to/reports (read October 18, 2026). The $5 budget alarm is notification only, not a hard spending cap.

## 4c. Reversal criterion (original Milestone 3)

1. **Threshold:** The original `milestone3/RISKS.md` specifies **deployed p95 on `GET /api/v1/applications` greater than 800 ms due to cold starts**, then moving the web service from AWS Lambda to a container-on-demand service (Fargate).
2. **Measurement:** The deployed image returned HTTP **404** for `GET /api/v1/applications`; it was not an implemented endpoint. Therefore **no valid p95 was measured for that original route**; as a reference only, the deployed **warm `GET /tasks` median p95 was 58.39 ms**, which is not a cold-start test.
3. **Action:** The original criterion cannot be declared crossed or not crossed from these samples. The team already deployed the container-on-demand shape (Google Cloud Run), so we will keep it for the course demo, and revisit the original threshold only if the named endpoint and cold-start test are implemented, or seek instructor approval for a revised criterion.

This limitation is intentional: claiming a passing/failing score for a missing endpoint would falsify the assignment's original threshold.
