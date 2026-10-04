# Provider Shortlist

Our two providers are **Google Cloud** and **Cloudflare**. These are the same two providers researched for the Module 5 provider survey.

**Date checked:** October 3, 2026

## Google Cloud

**C1 - Runs our container and gives us a web address**

**Verdict: Meets**

Google Cloud Run can deploy a container image and gives the application a URL that can be reached through the Internet.

URL: https://docs.cloud.google.com/run/docs/deploying

Date read: October 1, 2026.

**C2 - S3-compatible object storage**

**Verdict: Partially Meets**

Google Cloud Storage works with some tools made for Amazon S3. It supports HMAC keys, V4 signing, and signed URLs. However, Google does not describe Cloud Storage as a completely S3-compatible service, so this was marked as partially meets.

URLs:

https://docs.cloud.google.com/storage/docs/interoperability

https://docs.cloud.google.com/storage/docs/request-endpoints

https://docs.cloud.google.com/storage/docs/access-control/signed-urls

Date read: October 1, 2026.

**C3 - Limited credentials**

**Verdict: Meets**

Google Cloud supports service accounts and permissions that can limit what the application is allowed to access. This means the application does not need to use a person's main account credentials.

URLs:

https://docs.cloud.google.com/storage/docs/authentication/managing-hmackeys

https://docs.cloud.google.com/storage/docs/access-control/iam-permissions

Date read: October 1, 2026.

**C4 - List and delete resources**

**Verdict: Meets**

Google provides command-line commands that can list and delete stored files.

List:

`gcloud storage ls gs://my-bucket`

Delete:

`gcloud storage rm gs://my-bucket/my-object`

URLs:

https://docs.cloud.google.com/sdk/gcloud/reference/storage/ls

https://docs.cloud.google.com/sdk/gcloud/reference/storage/rm

Date read: October 1, 2026.

**C5 - Spending warning or limit**

**Verdict: Meets**

Google Cloud supports budget alerts. It also has a spend-cap feature for some services, including Cloud Run. The spend-cap feature is listed as preview and does not cover every Google Cloud service.

URLs:

https://docs.cloud.google.com/billing/docs/how-to/budgets

https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps

Date read: October 1, 2026.

**C6 - Free allowance or cost under $5**

**Verdict: Meets**

Google has an ongoing Free Tier. Cloud Run has free monthly usage and Cloud Storage includes 5 GB-months of Standard storage each month in certain U.S. regions.

The ongoing Free Tier does not expire for eligible customers, although Google can change the limits.

URLs:

https://cloud.google.com/free

https://cloud.google.com/run/pricing

https://cloud.google.com/storage/pricing

Date read: October 1, 2026.

## Cloudflare

**C1 - Runs our container and gives us a web address**

**Verdict: Meets**

Cloudflare Containers can use container images pushed to Cloudflare's registry. The application can then receive requests through a Worker.

URL: https://developers.cloudflare.com/containers/guides/deploy/

Date read: October 1, 2026.

**C2 - S3-compatible object storage**

**Verdict: Meets**

Cloudflare R2 has an S3-compatible API and supports signed requests and presigned URLs.

Its endpoint follows this format:

`https://<ACCOUNT_ID>.r2.cloudflarestorage.com`

URL: https://developers.cloudflare.com/r2/api/s3/api/

Date read: October 1, 2026.

**C3 - Limited credentials**

**Verdict: Meets**

Cloudflare allows credentials to be limited to a certain bucket. It also supports temporary credentials that can expire automatically.

URL: https://developers.cloudflare.com/r2/api/s3/temporary-credentials/

Date read: October 1, 2026.

**C4 - List and delete resources**

**Verdict: Meets**

Cloudflare provides command-line tools that can list and delete objects.

Example list command:

`aws s3 ls s3://my-bucket/ --endpoint-url https://<ACCOUNT_ID>.r2.cloudflarestorage.com`

Example delete command:

`npx wrangler r2 object delete <BUCKET>/<KEY>`

URLs:

https://developers.cloudflare.com/r2/get-started/cli/

https://developers.cloudflare.com/r2/reference/wrangler-commands/

Date read: October 1, 2026.

**C5 - Spending warning or limit**

**Verdict: Meets**

Cloudflare supports budget alerts. The alert can warn us when spending reaches an amount we choose, but it does not automatically stop spending.

URL: https://developers.cloudflare.com/billing/manage/budget-alerts/

Date read: October 1, 2026.

**C6 - Free allowance or cost under $5**

**Verdict: Meets**

R2 includes 10 GB of Standard storage each month, 1 million Class A requests, and 10 million Class B requests for free.

R2 also does not charge for sending stored data to the Internet.

The issue for our project is Cloudflare Containers. Containers require the $5 per month Workers Paid plan. This puts us at the assignment's $5 limit before any extra use.

URLs:

https://developers.cloudflare.com/r2/pricing/

https://developers.cloudflare.com/containers/platform/pricing/

Date read: October 1, 2026.

## Comparison

| Candidate | C1 | C2 | C3 | C4 | C5 | C6 |
| --- | --- | --- | --- | --- | --- | --- |
| Google Cloud | Meets | Partially Meets | Meets | Meets | Meets | Meets |
| Cloudflare | Meets | Meets | Meets | Meets | Meets | Meets |

**Main difference:** Cloudflare has better direct S3 compatibility, but its container service starts at the $5 Workers Paid plan. Google Cloud's storage is only partially S3 compatible, but its ongoing Free Tier is a better fit for the small amount of use expected from this class project.

## Team Choice

Our main choice is **Google Cloud**.

Our Software Engineering Job Tracker should have a small amount of traffic and storage during the class project. We may store files such as resumes, but we do not expect enough storage or downloads to need a large paid plan.

Google Cloud Run can run our container, and Cloud Storage can store uploaded files. Cloud Storage also supports signed URLs, which gives us a way to upload or download files without sending all of the file data through our application.

The biggest reason for choosing Google Cloud is the ongoing Free Tier. For the amount of use expected from this project, the free monthly usage should be enough.

**Store events:** Our current application does not depend on object storage events. We use the storage reconciliation report to find differences between object storage and the database. Because store events are not required by our current design, they were not a deciding factor between the two providers. If we add event-based reconciliation later, we would check the provider's current object event support before deployment.

## Fallback Provider

Our fallback is **Cloudflare**.

Cloudflare is a strong fallback because R2 directly supports the S3 API used by our application. R2 also has a good free allowance and does not charge for Internet egress.

The deciding clause for not choosing it first is **C6**. Cloudflare Containers require the $5 per month Workers Paid plan. This puts the project at the assignment's $5 limit before any extra usage.

We would reconsider Cloudflare if Containers became available on a free plan or another option allowed us to run our required container without immediately reaching the $5 limit.

## Disagreement Resolution

The providers have different advantages. Cloudflare has better S3 compatibility, while Google Cloud has a better cost situation for our class project.

We settled the decision by giving more importance to the expected use of our actual project. Since our project should have low traffic and a small amount of stored data, keeping the project inside an ongoing free allowance was more useful to us than having perfect S3 compatibility.

Because of that, we chose Google Cloud and kept Cloudflare as the fallback.

## Egress

**Google Cloud**

Cloud Storage includes 100 GB of free data transfer each month from supported North American Free Tier regions to eligible destinations.

For our application, downloads from Cloud Storage to users could count toward this outbound traffic. Traffic above the free allowance can be billed depending on the source and destination, so the current network transfer pricing should be checked before a real deployment.

URLs:

https://cloud.google.com/storage/pricing

https://cloud.google.com/run/pricing

Date read: October 4, 2026.

**Cloudflare**

Cloudflare R2 does **not charge Internet egress fees** for objects downloaded from R2.

Cloudflare Containers have separate network pricing. Internet traffic from Containers in North America and Europe is currently **$0.025 per GB after 1 TB of included traffic each month**.

For our application, files downloaded directly from R2 would not have an R2 Internet egress charge. Traffic sent from the container could have a charge after the included amount.

URLs:

https://developers.cloudflare.com/r2/pricing/

https://developers.cloudflare.com/containers/platform/pricing/

Date read: October 3, 2026.

## Switch Trigger

We would switch from Google Cloud to Cloudflare if Cloudflare Containers became available without immediately requiring the $5 Workers Paid plan.

This matters because R2 already gives us the stronger S3 compatibility and no Internet egress fee.

**Watcher:** Marshaun Adams

Before a real deployment, the watcher should check the current Cloudflare Containers and R2 pricing pages to see if this has changed.

## Route B

For this milestone, we are using **Route B**. We are not creating a real cloud account or deploying paid cloud resources for this milestone.

The application is tested locally using RustFS as the S3-compatible object store. The provider comparison is based on published provider documentation.

If the project later moves to a real provider, we would need the provider account, properly limited credentials, the storage bucket, the container deployment, and the required environment variables. No real provider credentials should be stored in the repository.