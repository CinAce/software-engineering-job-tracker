# Milestone 6 — Deployment

## 1a. Production Docker Image

The Software Engineering Job Tracker was built using the project's Dockerfile.

Image reference:
docker.io/marshaun06/job-tracker:e4686d7

Image digest:
sha256:7c625b8aef14920cb73cd5ff9af0f77bc3dec274475e2d8722e899ff76535a07

Git commit:
e4686d7

Build platform: linux/amd64
Runtime user: appuser
Health check: curl -fsS http://localhost:8000/health

The dependencies are installed before the application source is copied.
The image was pushed successfully to Docker Hub.

Evidence:
- evidence/image-build.txt
- evidence/image-push.txt
- evidence/image-ref.txt

## 1b. HTTPS Deployment

Provider: Google Cloud Platform
Project: itc531-module7
Region: us-central1
Service: itc531-job-tracker

Service URL:
https://itc531-job-tracker-k7misaiyja-uc.a.run.app

Health response:

    {"status":"ok","environment":"cloud","checks":{"database":"ok","storage":"ok"}}

Root endpoint: http=200

Both database and storage checks passed.

The deployment uses SQLite at /tmp/app.db. The database is
temporary and is not persistent across Cloud Run instance
replacements. RabbitMQ processing has not been verified
in this cloud deployment.

Evidence:
- evidence/gcp-deploy1.txt
- evidence/gcp-health.txt
- evidence/gcp-root.txt

## 1c. Idempotence

The GCP adapter successfully deployed the same service twice.

First revision: itc531-job-tracker-00001-p5s
Second revision: itc531-job-tracker-00002-vdj

An independent Cloud Run listing confirmed exactly one
service named itc531-job-tracker.

The cloud audit reported NOT CLEAN with 8 tracked resources,
as expected while the deployment remains active.

Evidence:
- evidence/gcp-deploy1.txt
- evidence/gcp-deploy2.txt
- evidence/gcp-audit2.txt
