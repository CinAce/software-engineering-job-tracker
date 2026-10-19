# Milestone 6: Teardown Evidence & Documentation

## 5b. Enumerate Completeness
To guarantee that our "CLEAN" status truly means no billable resources remain, our `cloud-audit.sh` and `gcp.sh` adapter specifically enumerate every resource type created during this deployment that could incur charges on Google Cloud Platform (GCP).

**Resources GCP charges for in our stack:**
*   **Cloud Run:** Billed for allocated CPU/memory time during request processing and network egress.
*   **Cloud Storage:** Billed for gigabytes stored, API operations (Class A/B), and network egress.
*   **Secret Manager:** Billed per active secret version and access operations.

**What we check:**
Our `adapter_enumerate` function explicitly queries:
1. Cloud Run services (`gcloud run services list`)
2. Cloud Storage HMAC keys (`gcloud storage hmac list`)
3. IAM Service Accounts (`gcloud iam service-accounts list`)
4. IAM Policy Bindings (`gcloud projects get-iam-policy`)
5. Secret Manager secrets (`gcloud secrets list`)
6. Cloud Storage buckets (`gcloud storage buckets list`)

**What we decided not to check and why:**
*   **VPC Networks / Compute Engine:** Our application uses Cloud Run's default serverless networking. We did not provision custom VPCs, NAT gateways, or persistent Compute Engine VMs, so we do not enumerate them.
*   **Artifact Registry / Container Registry:** The container image was built and hosted via our CI pipeline (GitHub Actions). The teardown adapter is only responsible for the live deployment infrastructure, not the CI storage.
*   **Cloud SQL / Managed Databases:** Our service connects to an external database via the `DATABASE_URL` environment variable. We did not provision a managed database directly on GCP for this deployment, so we do not audit for one.

**Region Completeness:**
We strictly enumerate resources in `us-central1`. This covers everything because our deployment script (`adapter_deploy`) explicitly passes `--region "$GCP_REGION"` for all compute resources. Cloud Storage buckets, Secret Manager secrets, and IAM policies are global/project-level resources, and our `gcloud` audit commands evaluate them across the entire project, ensuring no resources are hiding in other regions.

---

## 5c. Destroy Blockers
We evaluated the four common destroy blockers from Tutorial 4.2 against our specific GCP stack:

1.  **`prevent_destroy` lifecycle flag:**
    *   *Does it apply?* No.
    *   *Reason:* This is a Terraform/OpenTofu specific feature. Because our team used bash scripts wrapping the imperative `gcloud` CLI for the deployment adapter, Terraform state flags do not exist in our environment.
2.  **Provider deletion protection:**
    *   *Does it apply?* No.
    *   *Reason:* We do not use resources that enable deletion protection by default (like Cloud SQL or Spanner). Cloud Run services and standard Cloud Storage buckets can be deleted directly via `gcloud run services delete` and `gcloud storage rm` without needing to toggle a protection flag first.
3.  **Versioned bucket with non-current versions and delete markers:**
    *   *Does it apply?* Handled by our script.
    *   *Reason:* We did not explicitly enable Object Versioning on our GCS bucket. However, to prevent a non-empty bucket from blocking deletion, our teardown script uses `gcloud storage rm --recursive "gs://$S3_BUCKET"`. This command recursively deletes all objects (and versions, if any existed) inside the bucket before destroying the bucket itself.
4.  **Automatic final snapshot:**
    *   *Does it apply?* No.
    *   *Reason:* Cloud Run is a stateless compute platform and does not support or take disk snapshots. Cloud Storage does not take automatic final snapshots upon bucket deletion. Since our database is externally hosted and not part of this specific GCP deployment adapter, there are no managed database snapshots to worry about.
