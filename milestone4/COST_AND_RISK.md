# Cost and Risk

**Lifecycle Rules**

Our first lifecycle rule would remove incomplete multipart uploads after **7 days**. If someone starts uploading a large file but never finishes it, there is no reason to keep the unfinished parts forever. Removing them after 7 days prevents unused data from taking up storage space.

Our second rule would remove old versions of files after **30 days** if versioning is turned on. This would give us some time to recover an older file if something was accidentally replaced, while also preventing old copies from building up forever.

**Versioning**

For this class project, we would **not turn on versioning by default**. Our files are expected to be small, and the project is mainly being used for testing and demonstration.

Versioning can be useful because an older copy can be recovered after a file is changed or deleted. The downside is that every old version also takes up storage space. This could increase the amount of storage we are paying for.

If versioning was needed later, we would keep old versions for 30 days and then remove them.

**Storage Classes**

For this project, we would keep uploaded files in the normal or Standard storage class.

We would **not move files into a cheaper archive storage class right now**. Our project does not have enough stored data for the savings to matter much, and some cheaper storage classes require files to stay there for a minimum amount of time.

Before using a cheaper storage class, we would first compare the amount saved against any minimum storage time and retrieval costs. If moving the files would cost more than leaving them in Standard storage, we would not make the change.

**Egress Risk**

Egress is data that leaves the cloud provider and goes to a user or another location. Large file downloads can create extra costs, so this needs to be considered when choosing an object storage provider.

**Google Cloud**

Google Cloud Storage includes 100 GB per month of free data transfer from North America to eligible destinations. The Cloud Storage free tier applies to `us-west1`, `us-central1`, and `us-east1`.

Traffic above the free allowance can be billed depending on the source and destination, so we would check the current Google Cloud network pricing before a real deployment.

Source:
https://cloud.google.com/storage/pricing

Date checked: October 4, 2026.

**Cloudflare**

Cloudflare R2 does not charge for Internet egress. Its Standard storage free tier also includes 10 GB-month of storage, 1 million Class A operations, and 10 million Class B operations each month.

Our application would also need a place to run its container. Cloudflare Containers currently requires the Workers Paid plan, which has a minimum charge of $5 per month.

For Cloudflare Containers, network egress in North America and Europe includes 1 TB per month and is $0.025 per GB after that included amount.

Sources:
https://developers.cloudflare.com/r2/pricing/
https://developers.cloudflare.com/containers/platform/pricing/
https://developers.cloudflare.com/workers/platform/pricing/

Date checked: October 4, 2026.

**Spending Risk**

The main cost risk is accidentally leaving resources running or using more storage and network traffic than expected.

We would use budget alerts and check our usage while the project is active. We would also remove resources when they are no longer needed.

For this milestone, we are using Route B and testing the storage system locally, so we are not creating paid cloud resources.

**Main Risk**

The biggest storage risk is the database and object storage getting out of sync. An object could exist without a database row, or a database row could exist after its object is gone.

Our `storage_report.py` script helps find these problems by comparing the objects in storage against the file records in the database.