#!/usr/bin/env python3
"""Milestone 6 Part 4 — repeatable, warm, same-endpoint local vs Cloud Run benchmark.

No third-party Python packages. Creates one temporary test user per environment,
performs read-only GET samples, and writes CSV/JSON/Markdown evidence.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import http.client
import json
import math
import os
import pathlib
import secrets
import socket
import ssl
import statistics
import subprocess
import sys
import time
import urllib.parse
import uuid

UTC = dt.timezone.utc

def iso_now():
    return dt.datetime.now(UTC).isoformat(timespec="seconds")


def percentile(values: list[float], percent: float) -> float:
    """Linear-interpolation percentile (Hyndman/Fan type 7)."""
    s = sorted(values)
    if not s:
        raise ValueError("No samples")
    h = (len(s) - 1) * percent / 100
    i = int(math.floor(h))
    j = min(len(s) - 1, i + 1)
    return s[i] * (1 - (h - i)) + s[j] * (h - i)


def connection(url: str) -> http.client.HTTPConnection:
    p = urllib.parse.urlsplit(url)
    if p.scheme == "https":
        return http.client.HTTPSConnection(p.hostname, p.port or 443, timeout=15, context=ssl.create_default_context())
    if p.scheme == "http":
        return http.client.HTTPConnection(p.hostname, p.port or 80, timeout=15)
    raise ValueError("Use a full http(s) URL")


def request(conn: http.client.HTTPConnection, method: str, path: str, body: bytes | None = None, headers: dict | None = None):
    start = time.perf_counter()
    conn.request(method, path, body=body, headers=headers or {})
    response = conn.getresponse()
    payload = response.read()
    elapsed = (time.perf_counter() - start) * 1000.0
    return response.status, payload, elapsed


def create_user(base: str) -> str:
    """Register/login demo user, retaining JWT in memory only."""
    conn = connection(base)
    email = f"m6-bench-{uuid.uuid4().hex[:18]}@example.com"
    password = secrets.token_urlsafe(24)
    body = json.dumps({"email": email, "password": password}).encode()
    try:
        status, msg, _ = request(conn, "POST", "/auth/register", body, {"Content-Type": "application/json"})
        if status != 201:
            raise RuntimeError(f"{base}: user register returned HTTP {status}, expected 201; response={msg[:400]!r}")
        login = urllib.parse.urlencode({"username": email, "password": password}).encode()
        status, msg, _ = request(conn, "POST", "/auth/login", login, {"Content-Type": "application/x-www-form-urlencoded"})
        if status != 200:
            raise RuntimeError(f"{base}: login returned HTTP {status}, expected 200; response={msg[:400]!r}")
        token = json.loads(msg)["access_token"]
        if not token:
            raise RuntimeError("Empty login token")
        return token
    finally:
        conn.close()


def verify(base: str):
    conn = connection(base)
    try:
        status, data, _ = request(conn, "GET", "/health")
        if status != 200:
            raise RuntimeError(f"{base}/health returned HTTP {status}")
        response = json.loads(data)
        if response.get("status") != "ok" or any(x != "ok" for x in response.get("checks", {}).values()):
            raise RuntimeError(f"{base}/health degraded: {response}")
    finally:
        conn.close()


def missing_m3_endpoint(base: str):
    conn = connection(base)
    try:
        code, _, _ = request(conn, "GET", "/api/v1/applications")
        return code
    finally:
        conn.close()


def sample_run(base, token, path, name, rep, warmups, calls):
    """One persistent HTTP(S) connection, warmups not counted, all 200 responses."""
    conn = connection(base)
    rows = []
    headers = {"Accept": "application/json"}
    if path == "/tasks":
        headers["Authorization"] = "Bearer " + token
    try:
        for _ in range(warmups):
            status, body, _ = request(conn, "GET", path, headers=headers)
            if status != 200:
                raise RuntimeError(f"Warmup failed for {name} {path}: HTTP {status}: {body[:220]!r}")
        for i in range(1, calls + 1):
            status, body, ms = request(conn, "GET", path, headers=headers)
            if status != 200:
                raise RuntimeError(f"Measured request failed for {name} {path}: HTTP {status}: {body[:220]!r}")
            rows.append({"recorded_at_utc": iso_now(), "environment": name,
                         "endpoint": f"GET {path}", "repetition": rep,
                         "sample": i, "elapsed_ms": round(ms, 4), "http_status": status})
    finally:
        conn.close()
    return rows


def tcp_probe(base, count=5):
    """TCP handshake to edge is a rough one-RTT proxy, not an app breakdown."""
    p = urllib.parse.urlsplit(base)
    host, port = p.hostname, (p.port or (443 if p.scheme == "https" else 80))
    latencies = []
    for _ in range(count):
        start = time.perf_counter()
        sock = socket.create_connection((host, port), timeout=10)
        latencies.append((time.perf_counter() - start) * 1000.0)
        sock.close()
    return latencies


def gcp_url():
    cmd = ["gcloud", "run", "services", "describe", "itc531-job-tracker", "--project=itc531-module7", "--region=us-central1", "--format=value(status.url)"]
    return subprocess.check_output(cmd, text=True).strip()


def summary(rows):
    data = {}
    for env in ("local", "cloud"):
        for endpoint in ("GET /health", "GET /tasks"):
            repeats = []
            for rep in (1, 2, 3):
                values = [r["elapsed_ms"] for r in rows if r["environment"] == env and r["endpoint"] == endpoint and r["repetition"] == rep]
                repeats.append({"rep": rep, "n": len(values), "p50_ms": round(percentile(values, 50), 3), "p95_ms": round(percentile(values, 95), 3)})
            data[f"{env}:{endpoint}"] = {"repetitions": repeats,
                "median_p50_ms": round(statistics.median(x["p50_ms"] for x in repeats), 3),
                "median_p95_ms": round(statistics.median(x["p95_ms"] for x in repeats), 3)}
    return data


def report(data, info, network, billing, billed_at):
    if ":8013" in info["local"]:
        local_description = "The local application is exposed directly on port 8013 through the full root Compose stack (bypassing Nginx). "
    elif ":8012" in info["local"]:
        local_description = "The local application uses the separately started Part 3 monitoring Compose stack on port 8012, with local SQLite and storage check disabled; this differs from GCP's GCS-backed health route. "
    else:
        local_description = "The local FastAPI base URL was provided by the operator; verify that it bypasses the root Nginx gateway and uses the intended Docker Compose stack. "
    lines = ["# Milestone 6 — Part 4: Measurement and Evaluation", "",
        "## 4a. Warm request latency: local vs deployed", "",
        "**Method:** Measured on the same Mac using the Python standard library's persistent HTTP(S) connections. "
        + local_description +
        "Cloud is the deployed Google Cloud Run FastAPI service. Each endpoint/environment has 3 independent repetitions, "
        f"with {info['warmups']} discarded warmup requests and {info['calls']} timed requests per repetition. "
        "Samples are sequential, HTTP 200 responses only; any unexpected status aborts the run. "
        "All percentiles use linearly interpolated p50/p95, and the headline number is the **median of the three repetitions**.", "",
        f"- Measured at UTC: {info['measured_at_utc']}",
        f"- Local URL: `{info['local']}`", f"- Deployed URL: `{info['cloud']}`",
        "- Endpoints: `GET /health` (health/root workload group) and authenticated `GET /tasks` (task workload group), "
        "the two busiest workload categories estimated in Milestone 3 `WORKLOAD_PROFILE.md` (9,000 and 3,000 requests/month respectively).",
        "- The benchmark creates one temporary demo user per environment, logs in, and tests **read-only** `GET /tasks`. The login token is never written to evidence files.",
        "- Local runs against the complete Compose stack and local object store; Cloud Run uses GCS and ephemeral SQLite. Their database and storage dependencies differ, so response-time differences are not attributable to network alone.",
        "", "| Environment | Endpoint | Rep 1 p50 / p95 (ms) | Rep 2 p50 / p95 (ms) | Rep 3 p50 / p95 (ms) | Median p50 (ms) | Median p95 (ms) |", "|---|---|---:|---:|---:|---:|---:|" ]
    for ep in ("GET /health", "GET /tasks"):
        for env in ("local", "cloud"):
            item = data[f"{env}:{ep}"]
            reps = [f"{v['p50_ms']:.2f} / {v['p95_ms']:.2f}" for v in item["repetitions"]]
            lines.append(f"| {env} | `{ep}` | {reps[0]} | {reps[1]} | {reps[2]} | {item['median_p50_ms']:.2f} | {item['median_p95_ms']:.2f} |")
    lines.extend(["", "### Network round-trip contribution", "",
        "We measured five **new TCP connections** to each environment from the same Mac. "
        "The difference in median TCP-connect time is a rough **one-RTT proxy to the Google edge**, not a precise decomposition of HTTP latency. "
        "The timed HTTP requests reused persistent connections, so TLS setup and connection establishment were intentionally excluded after warmup.", ""])
    local_tcp = statistics.median(network["local"])
    cloud_tcp = statistics.median(network["cloud"])
    proxy = cloud_tcp - local_tcp
    lines.extend([f"- Local median TCP connect: **{local_tcp:.2f} ms**", f"- Cloud median TCP connect: **{cloud_tcp:.2f} ms**",
        f"- Rough network RTT proxy: **{proxy:.2f} ms** extra (cloud minus local)."])
    for ep in ("GET /health", "GET /tasks"):
        d = data[f"cloud:{ep}"]["median_p50_ms"] - data[f"local:{ep}"]["median_p50_ms"]
        lines.append(f"- `{ep}` end-to-end median-p50 difference: **{d:+.2f} ms** (cloud minus local). " +
            (f"The {proxy:.2f} ms TCP proxy is approximately {proxy/d*100:.0f}% of this delta, but should NOT be treated as a measured fraction caused by network." if d>0 and proxy>=0 else "This difference cannot be meaningfully partitioned using the TCP proxy."))
    lines.extend(["", "**Separating network from server processing:** Run a second load generator inside `us-central1` against the same Cloud Run service "
        "and compare it with results from the Mac; or capture per-request server-side processing durations using application tracing and request IDs. "
        "Those methods would isolate network contribution more directly. The TCP proxy alone cannot determine exact shares. "
        "The comparison also includes different storage backends and Mac ARM-emulation overhead.",
        "", "**Evidence:** `evidence/part4-latency-raw.csv`, `evidence/part4-latency-summary.json`, "
        "`evidence/part4-latency-console.txt`; runner `part4/measure_latency.py` and Compose override `part4/compose.benchmark.yml`.",
        "", "## 4b. Cost: Google Cloud billing versus the Milestone 3 model", "",
        "**Original model (Milestone 3 `COST_MODEL.md`, AWS `us-east-1`, September 27, 2026):** "
        "15,000 requests/month at **$0.025/month** for Lambda + API Gateway versus **$31.28/month** "
        "for the Fargate + ALB server shape, before applying provider free allowances. "
        "Its model uses 256 MB and 120 ms for Lambda, and a continuously running Fargate task and ALB for the server.",
        "", "**Actual deployment:** Google Cloud Run (`us-central1`), min instances 0, max instances 1, "
        "a GCS bucket, three Secret Manager secrets, a service account and HMAC key; ephemeral SQLite instead of persistent PostgreSQL. "
        "This is not the same service mix, price region, or usage period. Direct arithmetic difference between AWS model and GCP bill is **not a like-for-like model variance**.", ""])
    if billing is None:
        lines.extend(["- **Actual billing amount: PENDING** — must be transcribed from Google Cloud Billing Reports with timestamp and screenshot.",
                      "- **Comparison and variance: PENDING actual billing amount.** The prior AWS figures are theoretical monthly estimates, not an observed GCP total."])
    else:
        lines.extend([f"- **Actual reported project charges:** **${billing:.4f} USD** (GCP Billing Reports, {billed_at}).",
                      "- **Interpretation:** This is the observed GCP project total for the selected billing-report filter/time range, "
                      "not strictly an isolated Cloud Run-only bill. Subtracting AWS's $0.025 monthly forecast would mix different providers, volumes, and time horizons; "
                      "the variance is therefore **not directly comparable**. GCP free allowances and billing-report delays may explain low or zero displayed charges.",
                      "- **Billing evidence:** `evidence/gcp-billing-report.png` (or a saved report PDF), with the filter/time range and observed UTC time visible."])
    lines.extend(["", "**Capture method:** Google Cloud Console → Billing → Reports; select the `itc531-module7` project, "
        "Charge period starting October 18, 2026, Group by Service and show credits/discounts; screenshot the report and record the filtered total and observation time. "
        "Billing data can lag usage; explain any lag and include Secret Manager, Cloud Storage, Cloud Run, logging and egress line items if visible. "
        "The project's $5 budget is an **alert**, not an enforced cap.",
        "", "**Reference:** https://docs.cloud.google.com/billing/docs/how-to/reports (viewed October 18, 2026).",
        "", "## 4c. Reversal criterion (original Milestone 3)", "",
        "1. **Threshold:** The original `milestone3/RISKS.md` specifies **deployed p95 on `GET /api/v1/applications` greater than 800 ms due to cold starts**, then moving the web service from AWS Lambda to a container-on-demand service (Fargate).",
        f"2. **Measurement:** The deployed image returned HTTP **{info['original_route_http_status']}** for `GET /api/v1/applications`; it was not an implemented endpoint. Therefore **no valid p95 was measured for that original route**; as a reference only, the deployed **warm `GET /tasks` median p95 was {data['cloud:GET /tasks']['median_p95_ms']:.2f} ms**, which is not a cold-start test.",
        "3. **Action:** The original criterion cannot be declared crossed or not crossed from these samples. "
        "The team already deployed the container-on-demand shape (Google Cloud Run), so we will keep it for the course demo, "
        "and revisit the original threshold only if the named endpoint and cold-start test are implemented, or seek instructor approval for a revised criterion.",
        "", "This limitation is intentional: claiming a passing/failing score for a missing endpoint would falsify the assignment's original threshold.", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local", default="http://127.0.0.1:8013")
    parser.add_argument("--cloud", default=None, help="If omitted, resolve from gcloud run services describe")
    parser.add_argument("--calls", type=int, default=50)
    parser.add_argument("--warmups", type=int, default=8)
    parser.add_argument("--outdir", default="milestone6/evidence")
    parser.add_argument("--report", default="milestone6/MEASUREMENT.md")
    parser.add_argument("--billing-total", type=float, default=None, help="USD from GCP Billing Reports, NOT a guess")
    parser.add_argument("--billing-observed-at", default=None, help="date/time read from GCP Billing Reports")
    args = parser.parse_args()
    if args.calls < 20 or args.warmups < 3:
        parser.error("Use at least 20 samples and 3 warmups per repetition")
    if (args.billing_total is None) != (args.billing_observed_at is None):
        parser.error("Supply both --billing-total and --billing-observed-at, or neither")
    if args.billing_total is not None and (not math.isfinite(args.billing_total) or args.billing_total < 0):
        parser.error("Billing amount must be finite and nonnegative")
    cloud = (args.cloud or gcp_url()).rstrip("/")
    local = args.local.rstrip("/")
    print(f"Local app: {local}; Cloud Run app: {cloud}", flush=True)
    print("Preflight health and original Milestone 3 route", flush=True)
    verify(local)
    verify(cloud)
    m3status = missing_m3_endpoint(cloud)
    print(f"Original M3 GET /api/v1/applications status: {m3status}", flush=True)
    token = {"local": create_user(local), "cloud": create_user(cloud)}
    print("Temporary benchmark accounts created and authenticated (no secrets logged).", flush=True)
    info = {"measured_at_utc": iso_now(), "local": local, "cloud": cloud,
            "calls": args.calls, "warmups": args.warmups, "original_route_http_status": m3status}
    rows = []
    for rep in (1, 2, 3):
        for endpoint in ("/health", "/tasks"):
            for env, base in (("local", local), ("cloud", cloud)):
                print(f"Repetition {rep}/3: {env} GET {endpoint} ({args.calls} samples)", flush=True)
                rows += sample_run(base, token[env], endpoint, env, rep, args.warmups, args.calls)
    probes = {"local": tcp_probe(local), "cloud": tcp_probe(cloud)}
    data = summary(rows)
    output = pathlib.Path(args.outdir)
    output.mkdir(parents=True, exist_ok=True)
    with (output / "part4-latency-raw.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (output / "part4-latency-summary.json").open("w") as f:
        json.dump({"info": info, "summary": data, "tcp_connect_samples_ms": probes}, f, indent=2)
        f.write("\n")
    report_path = pathlib.Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report(data, info, probes, args.billing_total, args.billing_observed_at))
    print("\n=== MEDIANS FROM THREE RUNS ===")
    for env in ("local", "cloud"):
        for ep in ("GET /health", "GET /tasks"):
            obj = data[f"{env}:{ep}"]
            print(f"{env:5s} {ep:11s} p50={obj['median_p50_ms']:.2f}ms p95={obj['median_p95_ms']:.2f}ms")
    print(f"TCP edge RTT proxy (cloud-local) = {statistics.median(probes['cloud'])-statistics.median(probes['local']):.2f}ms")
    print(f"Wrote {report_path} and {output}/part4-latency-*.{{csv,json}}")
    if args.billing_total is None:
        print("BILLING EVIDENCE STILL REQUIRED: visit GCP Billing Reports and rerun with --billing-total and --billing-observed-at, or use fill_billing.py to update without rerunning latency")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"BENCHMARK STOPPED (no fabricated measurements): {exc}", file=sys.stderr)
        sys.exit(1)
