# Milestone 6 - Google Cloud Deployment

Project repository:
https://github.com/CinAce/software-engineering-job-tracker

## Deployment Details

* **Cloud Run:** https://itc531-job-tracker-k7misaiyja-uc.a.run.app
* **Google Cloud Project:** project-2e54276d-7e4e-4719-b2b
* **Region:** us-central1
* **GCP Adapter:** `adapters/gcp.sh`
* **Adapter Reviewer:** Marshaun Adams

All 6 parts of Milestone 6 (Deployment, CI Pipeline, Observability, Measurement, Teardown, and Documentation) are complete.

---

## The CI Pipeline
Our GitHub Actions pipeline is structured to automate testing and image building securely[cite: 6]:
* **Jobs and Gating:** The workflow consists of a `test` job and a `build` job. The `build` job is strictly gated by the `test` job, meaning the container image is only built and pushed if the test coverage requirements and unit tests pass[cite: 6].
* **Maintainer Configuration:** To allow a fresh clone to deploy automatically, a maintainer must configure Workload Identity Federation (OIDC) at the provider level (Google Cloud). This involves setting up a subject condition that restricts token generation specifically to pushes from this repository, completely eliminating the need to store long-lived provider access keys in GitHub Secrets[cite: 6].

## Monitoring
The observability stack uses Prometheus to scrape application metrics, which are visualized via our dashboard[cite: 6].
* **Accessing the Dashboard:** The dashboard is accessible via our provisioned Grafana instance (running locally during metrics capture).
* **Request Rate Panel:** This panel tracks `sum(rate(...))` against our traffic counters, answering how much throughput the application is actively handling over a specific time window[cite: 6].
* **Error Rate Panel:** This panel tracks our failure counters, answering how many of the incoming requests are failing (e.g., returning 500-level HTTP status codes) so we can detect degradation[cite: 6].

## Troubleshooting
During the milestone deployment and teardown, our team encountered and resolved the following issues[cite: 6]:

1. **CRLF Line Endings in Scripts:** 
   * *Failure:* Running `bash scripts/cloud-audit.sh` crashed immediately with an `invalid option name 4: set: pipefail` error. 
   * *Fix:* The bash scripts were saved with Windows-style CRLF hidden characters. We fixed this by changing the line endings to LF in VS Code for both the audit script and `gcp.sh`.
2. **Disabled GCP APIs:**
   * *Failure:* The adapter script failed during the enumeration phase with a `SERVICE_DISABLED` error for both the Identity and Access Management (IAM) API and the Cloud Resource Manager API.
   * *Fix:* We followed the activation URLs provided in the error logs and manually enabled these APIs in the Google Cloud Console to allow the script to verify IAM bindings.
3. **Teardown Impersonation Lockout:**
   * *Failure:* The `cloud-down.sh` script crashed midway through destroying our resources. It deleted the `itc531-deployer` service account first, which it was currently impersonating, instantly locking itself out of the project and leaving resources stranded.
   * *Fix:* We modified `adapters/gcp.sh` to remove the impersonation rule (`CLOUDSDK_AUTH_IMPERSONATE_SERVICE_ACCOUNT=""`) and ran the teardown using the active Project Owner account to successfully destroy the remaining resources.

---

## Important Notes
- The private `adapters/gcp.env` file must never be committed.
- The Module 7 HMAC credential JSON must never be committed.
- SQLite currently uses temporary Cloud Run storage.
- RabbitMQ background processing is not configured in the cloud.
