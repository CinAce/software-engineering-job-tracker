# Milestone 6 - Google Cloud Deployment

Project repository:
https://github.com/CinAce/software-engineering-job-tracker

## Current Progress

Part 1a: Production Docker image completed.
Part 1b: HTTPS deployment completed.
Part 1c: Two adapter deployments and idempotence verified.

Cloud Run:
https://itc531-job-tracker-k7misaiyja-uc.a.run.app

Google Cloud project: itc531-module7
Region: us-central1

The GCP adapter is located at adapters/gcp.sh.
Cloud scripts are located under scripts/.
Deployment evidence is located under milestone6/evidence/.

## Important Notes

- The private adapters/gcp.env file must never be committed.
- The Module 7 HMAC credential JSON must never be committed.
- SQLite currently uses temporary Cloud Run storage.
- RabbitMQ background processing is not configured in the cloud.
- Do not run cloud-down.sh until monitoring and measurements
  are finished and teardown is coordinated.
- cloud-down.sh also removes the shared Module 7 service
  account and HMAC credentials.
- The GCP adapter still requires teammate code review.

Adapter reviewer: Pending teammate review.
Parts 2 through 6: In progress.
