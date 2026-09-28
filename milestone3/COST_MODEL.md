# Cost Model: Function vs. Server Shape

## A. Line Item Comparison
Target Component: FastAPI Web Service (Software Engineering Job Tracker)

**1. Per-request charge**
* **Function (AWS Lambda + API Gateway):** $0.20 per 1 million Lambda requests, plus $1.00 per 1 million API Gateway HTTP API requests. 
* **Server (AWS Fargate + ALB):** Zero. Fargate bills strictly by time for the underlying container running, regardless of how many requests it handles.

**2. Compute duration**
* **Function:** $0.0000166667 per GB-second. We allocate 256MB (0.25GB). For a 120ms p95 duration, this equals 0.03 GB-seconds per request.
* **Server:** Zero. The duration of individual requests does not incur additional compute charges beyond the continuous idle capacity bill.

**3. Idle capacity**
* **Function:** Zero. The function scales to zero when not in use; compute costs only accrue during active execution.
* **Server:** $0.04048 per vCPU-hour and $0.004445 per GB-hour. For a minimal task (0.25 vCPU, 0.5 GB RAM) running 24/7 (730 hours/month), this is $7.39 for vCPU and $1.62 for RAM, totaling $9.01/month.

**4. The HTTP front door**
* **Function:** Billed entirely via the per-request API Gateway charge listed in line item 1. Fixed cost is zero.
* **Server:** Application Load Balancer requires $0.0225 per hour plus ~$0.008 per LCU-hour. Running 24/7 (730 hours), the base cost is $16.43/month, plus roughly $5.84/month for 1 LCU, totaling $22.27/month.

**5. Data out**
* **Function:** Zero. The expected 15,000 requests per month generating ~10KB responses each equals ~0.15 GB/month, falling completely within the standard 100GB/month free tier.
* **Server:** Zero. Same reason as the function shape.

**6. Log ingestion and retention**
* **Function:** $0.50 per GB ingested via CloudWatch. With 15,000 requests generating ~1KB of logs each (~0.015 GB), the cost rounds to zero (negligible).
* **Server:** Zero. Same log volume yields negligible cost.

**7. Storage at rest**
* **Function:** Zero. The API is stateless and does not provision persistent EBS volumes.
* **Server:** Zero. The Fargate task is stateless and ephemeral.

---

## B. Pricing Sources
*All prices evaluated for the **US East (N. Virginia) `us-east-1`** region on **September 27, 2026**.*
* **AWS Lambda:** $0.20 per 1M requests; $0.0000166667 per GB-second. (URL: https://aws.amazon.com/lambda/pricing/)
* **Amazon API Gateway:** $1.00 per 1M requests for HTTP API. (URL: https://aws.amazon.com/api-gateway/pricing/)
* **AWS Fargate:** $0.04048 per vCPU-hour; $0.004445 per GB-hour. (URL: https://aws.amazon.com/fargate/pricing/)
* **AWS Application Load Balancer:** $0.0225 per hour; $0.008 per LCU-hour. (URL: https://aws.amazon.com/elasticloadbalancing/pricing/)

---

## C. Break-Even Analysis
Let $R$ be the number of monthly requests. 

**Function Shape Cost (Total `a * R + b`):**
* Per-request variable cost (`a`):
  * API Gateway: $1.00 / 1,000,000 = $0.000001
  * Lambda Request: $0.20 / 1,000,000 = $0.0000002
  * Lambda Duration: 0.25GB * 0.12s * $0.0000166667 = $0.0000005
  * Total `a` = **$0.0000017 per request**
* Fixed monthly cost (`b`): **$0**
* Equation: `function_total = $0.0000017 * R + 0`

**Server Shape Cost (Total `c * R + F`):**
* Per-request variable cost (`c`): **$0**
* Fixed monthly cost (`F`):
  * Fargate Idle Compute: $9.01
  * ALB Base + LCU: $22.27
  * Total `F` = **$31.28 per month**
* Equation: `server_total = 0 * R + 31.28`

**Volume Calculations:**
* **Expected term volume (15,000 requests/month):**
  * Function: $0.0000017 * 15,000 = **$0.025 / month**
  * Server: **$31.28 / month**
* **100x volume (1,500,000 requests/month):**
  * Function: $0.0000017 * 1,500,000 = **$2.55 / month**
  * Server: **$31.28 / month**

**Break-Even Point ($R^*$):**
`R* = (F - b) / (a - c)`
`R* = (31.28 - 0) / (0.0000017 - 0)`
`R* = 18,400,000 requests/month`

Our expected volume of 15,000 requests per month sits drastically below the break-even point $R^*$ by a factor of **1,226x**, making the function shape overwhelmingly cheaper for this specific workload.

---

## D. Sensitivity and Free Allowance
* **Sensitivity 1: Execution Duration.** If our API suddenly requires heavy data processing and the p95 duration spikes from 120ms to 5,000ms, the duration cost (`a`) jumps. However, given our extremely low request volume, the total function cost would still fall drastically below the server's fixed cost. Duration would have to increase to over 22 minutes per request (exceeding Lambda's hard timeout limit) to flip the recommendation.
* **Sensitivity 2: Request Amplification.** If a frontend bug generates 100x our expected traffic (1.5 million requests), the function bill only rises to $2.55/month. Traffic would have to jump to over 18.4 million requests per month to make the server shape cheaper.
* **Free Allowance:** The AWS Lambda free tier (1 million requests and 400,000 GB-seconds per month) is perpetual and does not expire after 12 months.
* **Exceeding the Allowance:** When the free tier is exceeded, the account is seamlessly billed at standard on-demand rates without service interruption. For our team, this means we face no risk of the application going offline from hitting a hard cap, but we are exposed to financial billing risk if traffic spikes catastrophically.