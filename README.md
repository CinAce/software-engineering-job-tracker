# Software Engineering Job Tracker (ITC 531)

A full-stack, distributed application designed to track software engineering job applications. This project fulfills the final amalgamation requirements for ITC 531 by successfully integrating a web API, relational database, message broker, and object storage into a cohesive cloud environment.

## Architecture & Tech Stack

This application has been fully migrated from local development (SQLite/Docker) to a production-ready cloud architecture:

*   **Compute:** Google Cloud Run (Serverless Container Deployment)
*   **Database:** Neon PostgreSQL (Cloud-native relational database)
*   **Message Broker:** CloudAMQP / RabbitMQ (Background event processing)
*   **Object Storage:** Google Cloud Storage (S3-compatible bucket)
*   **API Framework:** FastAPI (Python)
*   **Secrets Management:** Google Cloud Secret Manager

## Cloud Deployment Details

*   **GCP Project ID:** `project-2e54276d-7e4e-4719-b2b`
*   **GCP Region:** `us-central1`
*   **Live Service URL:** `https://itc531-job-tracker-447540810315.us-central1.run.app`
*   **Storage Bucket:** `itc531-job-tracker-bucket-2e54276d`

## Environment Variables & Secrets

The live Cloud Run environment maps the following variables. Sensitive credentials are automatically injected securely at runtime via GCP Secret Manager:

*   `DATABASE_URL`: Connection string for Neon PostgreSQL.
*   `AMQP_URL` / `BROKER_URL`: Connection strings for the CloudAMQP RabbitMQ instance.
*   `JWT_SECRET`: Secret key for generating and validating API authentication tokens.
*   `S3_ENDPOINT_URL`: `https://storage.googleapis.com`
*   `S3_BUCKET`: `itc531-job-tracker-bucket-2e54276d`
*   `S3_REGION`: `auto` *(Required for GCP S3-compatibility)*
*   `AWS_REQUEST_CHECKSUM_CALCULATION`: `WHEN_REQUIRED` *(Bypasses proprietary checksums that cause GCP signature mismatches)*
*   `AWS_ACCESS_KEY_ID`: GCP HMAC Access Key
*   `AWS_SECRET_ACCESS_KEY`: GCP HMAC Secret Key

## Key Features & Event Amalgamation

1.  **Authentication:** Secure JWT-based user login and token generation.
2.  **File Storage (`/files`):** Users can upload files (e.g., resumes). The application streams the file directly to Google Cloud Storage and records the file metadata in the Neon PostgreSQL database.
3.  **Background Processing (`/api/jobs/scrape` & `/api/exports`):** The API accepts long-running tasks, instantly returns an `HTTP 202 Accepted` status with a UUID tracking ID, and publishes a persistent message to the RabbitMQ broker for background consumer processing.

## Running the Application

### Local Development
To run the application locally using Docker Compose:
1. Ensure your `.env.local` is configured.
2. Run `docker-compose up --build` to start the API and background workers.

### Cloud Deployment & Auditing
Deployment and teardown are managed via custom bash adapters. 
*   **Deploy:** Run `source adapters/gcp.sh` followed by `adapter_deploy`.
*   **Audit:** Run `./adapters/cloud-audit.sh` to verify infrastructure health and IAM configurations.
*   **Teardown:** Run `./adapters/cloud-down.sh` to safely destroy the Cloud Run service and associated resources when the environment is no longer needed.