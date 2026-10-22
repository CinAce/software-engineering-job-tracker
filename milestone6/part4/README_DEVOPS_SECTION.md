## Milestone 6: Cloud deployment and observability (DevOps contributor)

This section covers the deployment and monitoring work. The **CI workflow, job gates, GitHub OIDC trust policy, and first-time registry/provider setup** belong to the teammate's Part 2 documentation and are not claimed as complete here.

### Deployment: what is running and how it was verified

- Provider: Google Cloud, project `itc531-module7`, region `us-central1`.
- Cloud Run service: `itc531-job-tracker` at <https://itc531-job-tracker-k7misaiyja-uc.a.run.app>.
- Image: `docker.io/marshaun06/job-tracker:e4686d7` (fixed Git-SHA tag; do not use `latest`).
- Adapter: `adapters/gcp.sh`; public example: `adapters/gcp.env.example`; lifecycle scripts: `scripts/cloud-verify.sh`, `scripts/cloud-audit.sh`, `scripts/cloud-down.sh`.
- Required preflight: `bash scripts/cloud-verify.sh gcp` must report `CONTRACT SATISFIED` **before** creating paid cloud resources.
- Local private settings live in **gitignored** `adapters/gcp.env`; the GCS HMAC credential JSON from Module 7 is also private. The Cloud Run runtime obtains its JWT and HMAC access/secret via three project Secret Manager secrets, not committed values. The storage bucket has a bucket-scoped object role.
- Two runs of `adapter_deploy` successfully generated revisions `00001-p5s` and `00002-vdj`, while `gcloud run services list` showed **one** service. Health returned `{"status":"ok","environment":"cloud","checks":{"database":"ok","storage":"ok"}` and root HTTP status was 200. See `milestone6/DEPLOYMENT.md` and `milestone6/evidence/`.
- Scale is minimum **0** and maximum **1** Cloud Run instance. This reduces idle spend but cold starts are possible. The configured **$5 monthly budget is a notification, not a hard spending cap**.
- **Demo-only limitations:** Cloud Run currently uses `sqlite:////tmp/app.db`, which loses records when instances are replaced. The RabbitMQ broker and asynchronous workers are not deployed to GCP; production persistence and background tasks are **not** proven by the successful `/health` check.

To review live status (read-only):

```bash
bash scripts/cloud-audit.sh gcp
gcloud run services list --project=itc531-module7 --region=us-central1
curl -fsS https://itc531-job-tracker-k7misaiyja-uc.a.run.app/health
```

An active cloud audit correctly says `NOT CLEAN` until the final coordinated teardown. **Important current risk:** The borrowed GCP `adapter_destroy` function also deletes the pre-existing Module 7 HMAC key, its shared service account, and local credential file. **Do not run `scripts/cloud-down.sh gcp` until it has been changed and independently reviewed to preserve those shared resources.** Part 5 owns the final teardown and the follow-up audit after at least 24 hours.

### Local monitoring / dashboard

The monitoring files are in `milestone6/monitoring/` and use version-pinned Prometheus `prom/prometheus:v3.5.0`, Grafana `grafana/grafana:12.1.0`, and the same fixed Job Tracker image. There is **no host exporter**. The local monitoring stack is intentionally separate from your team's existing `compose.yml` and the deployed Cloud Run service; it doesn't incur extra GCP monitoring resource charges.

From the repository root:

```bash
docker compose -f milestone6/monitoring/compose.yml up -d --wait
```

- Prometheus target page: <http://localhost:9091/targets>. Check the `job-tracker` target is **UP**; the scrape path is **`/metrics/`** with the trailing slash.
- Grafana dashboard: <http://localhost:3001/d/jobtracker-observability/job-tracker-observability>. Local-only demo login: `admin` / `local-demo-only`.
- Two provisioned panels: request rate `sum(rate(itc531_requests_total[5m])) or vector(0)` with requests/second units; server error rate `sum(rate(itc531_requests_total{status=~"5.."}[5m])) or vector(0)` with errors/second units.
- The verified Prometheus scrape returned `up=1`; during demo load, request rate was approximately `0.1608` requests/second and server 5xx rate was `0`. See `milestone6/OBSERVABILITY.md`, the Grafana dashboard JSON, and screenshots in `milestone6/evidence/`.
- Stop locally with `docker compose -f milestone6/monitoring/compose.yml down`; omit `--volumes` if you want to retain historical dashboard data.

### Latency and cost evaluation (Part 4)

Run the same 3-repetition benchmark locally and on Cloud Run using `milestone6/part4/README.md`. The root Nginx gateway short-circuits `/health`, so the Part 4 Docker Compose override exposes the **actual FastAPI app** directly at `127.0.0.1:8013` for a fair endpoint comparison. The harness creates temporary test users and measures warm `GET /health` and authenticated `GET /tasks` with 50 timed requests per repetition; no credentials go in the CSV evidence. Report generated at `milestone6/MEASUREMENT.md` with per-repetition p50/p95, medians, and a separately labeled rough TCP RTT proxy.

Actual provider charges must be captured in Google Cloud Billing Reports (screenshot + time range + timestamp). The old Milestone 3 model assumed AWS, so the change of provider, service mix and demo volume is noted rather than forcing a false apples-to-apples variance. The Milestone 3 reversal threshold names `GET /api/v1/applications`, an endpoint absent from the current app; report that limitation and don't substitute an unrelated endpoint silently.

### Three problems actually encountered, and fixes

1. **Adapter ZIP wasn't at `~/Downloads`:** An initial `unzip` failed with “cannot find or open”. We corrected the archive path to the copy in the actual module folder, then checked `adapters/gcp.sh` exists and passes `bash -n`.
2. **A documentation heredoc didn't terminate:** Pasting a long Python edit left the terminal showing `heredoc>` instead of changing `milestone6/DEPLOYMENT.md`. We used a complete, properly terminated `python3 - <<'PY'` block and verified the output with `cat` before committing.
3. **Whitespace warnings in Docker build evidence:** `git diff --cached --check` flagged trailing whitespace and carriage-return progress output in `milestone6/evidence/image-build.txt`. The warnings came from captured build output rather than changed Python source; logs should be normalized for cleaner diffs (without altering what was measured), and the team should inspect the staged changes before pushing.

For other failures, start with the application's `/health` **checks object**, `docker compose ... ps`, Prometheus's Targets page, Cloud Run revision logs, and `bash scripts/cloud-audit.sh gcp`. Avoid deleting GCP resources as a first troubleshooting step.
