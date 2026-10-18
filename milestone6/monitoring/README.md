# Milestone 6 Part 3 — Local observability

This standalone Docker Compose stack starts the **same pinned Job Tracker image** deployed to GCP, plus version-pinned Prometheus and Grafana. It does **not** scrape the live Cloud Run service, create GCP resources, or require provider secrets. Do not put production data into this local demo.

## Start

From the repository root:

```sh
docker compose -f milestone6/monitoring/compose.yml up -d --wait
docker compose -f milestone6/monitoring/compose.yml ps
```

The local API is at <http://localhost:8012/health>, Prometheus at <http://localhost:9091/targets>, and Grafana at <http://localhost:3001/> (demo-only login `admin` / `local-demo-only`). Grafana provisions its Prometheus data source and **Job Tracker Observability** dashboard automatically.

Prometheus scrapes `job-tracker:8000/metrics/` every 15 seconds. **The trailing slash matters** because `/metrics` redirects to the mounted ASGI metrics app. Prometheus should show the `job-tracker` target **UP**.

## Generate request data

Wait for at least two scrapes, then run requests over time so the 5-minute `rate()` query has data:

```sh
for i in $(seq 1 35); do
  curl -fsS http://localhost:8012/health >/dev/null || break
  sleep 1
done
```

Check the Prometheus target (UP means 1):

```sh
curl -fsS 'http://localhost:9091/api/v1/query?query=up%7Bjob%3D%22job-tracker%22%7D'
```

Dashboard URL: <http://localhost:3001/d/jobtracker-observability/job-tracker-observability>. Grafana may require a minute to show enough samples for rate(). Take screenshots of the Prometheus UP target and the Grafana dashboard showing both panels.

## Required queries

**Request rate** (requests/sec):

```promql
sum(rate(itc531_requests_total[5m])) or vector(0)
```

Bad: traffic unexpectedly drops to zero during expected usage or rises sharply beyond capacity. Investigate availability, traffic source, and scaling.

**Server error rate** (5xx responses/sec):

```promql
sum(rate(itc531_requests_total{status=~"5.."}[5m])) or vector(0)
```

Bad: sustained nonzero 5xx during normal traffic. Inspect app logs, recent deployments, DB/storage dependencies, and rollback if needed. 4xx client errors are deliberately excluded from this panel.

Why `rate()`? A counter only increases across requests; `rate()` converts its change over time into per-second activity and accounts for resets.

## Cardinality and labels

- `itc531_requests_total` (Counter): `method` (bounded HTTP verbs, e.g., GET/POST/PUT/PATCH/DELETE/OPTIONS), `path` (bounded declared route templates and `__unmatched__`), `status` (bounded HTTP status codes).
- `itc531_request_seconds` (Histogram): `method` (bounded HTTP verbs), `path` (bounded declared route templates); histogram adds a fixed `le` bucket label to `_bucket` samples (bounded predefined bucket boundaries).
- Python `prometheus_client` generates conventional `_created`, `_bucket`, `_sum`, and `_count` series. The program does not attach user IDs, request IDs, or raw resource IDs as labels.

In `app/main.py`, the route is read **after** `await call_next(request)` from `request.scope.get('route')`, then its template `route.path` is used, not the raw URL. That prevents requests like `/jobs/1` and `/jobs/2` from generating unique time series for each ID.

## Notes and shutdown

- The demo app uses a local, temporary SQLite database and disables its storage health check with `S3_ENDPOINT_URL=unused-local-monitoring`; the Cloud Run deployment has separately verified real GCS storage.
- Local-only credentials in `compose.yml` are **not for cloud or production**.
- Grafana and Prometheus use persistent Docker named volumes; all monitoring services are local and bound to 127.0.0.1.
- No node-exporter or cAdvisor is used, per the course instructions.

Stop when finished:

```sh
docker compose -f milestone6/monitoring/compose.yml down --volumes
```

This deletes only the **local monitoring** containers and their named volumes; it does not delete the GCP deployment or its data. Do **not** run `scripts/cloud-down.sh gcp` until the team's performance measurements are complete.
