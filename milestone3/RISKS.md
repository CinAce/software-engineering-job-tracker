# Risks and Reversal Criterion

## Architectural Risks

**1. Cold start on a user-visible path**
* **What goes wrong:** A user experiences a noticeable delay in the UI because the infrastructure must provision a new execution environment before running the code.
* **Which component:** FastAPI Web Service (Function Shape).
* **The trigger:** A user hits an endpoint after a period of inactivity, or a sudden traffic spike causes rapid function scale-out.
* **The signal you would see and where:** High `InitDuration` metrics in AWS CloudWatch logs and a spike in p95 latency on API Gateway.
* **What you would do about it:** Configure Provisioned Concurrency for the Lambda function to keep a baseline number of instances warm during active hours.

**2. State that does not survive an instance being recycled**
* **What goes wrong:** In-memory session data or temporary file buffers are unexpectedly lost between requests[cite: 4].
* **Which component:** FastAPI Web Service.
* **The trigger:** The cloud provider destroys an idle function container, and a newly provisioned container handles the user's subsequent HTTP request.
* **The signal you would see and where:** Users suddenly receiving 401 Unauthorized errors mid-session or failed resume uploads, visible in the application logs and API Gateway 4xx metrics[cite: 4].
* **What you would do about it:** Ensure all session state is strictly managed in the PostgreSQL database and have users upload resumes directly to object storage via presigned URLs instead of buffering files on the server.

**3. Concurrency limits and database connections**
* **What goes wrong:** The database exhausts its maximum allowed connections and rejects new queries, causing API endpoints to fail[cite: 4].
* **Which component:** FastAPI Web Service and PostgreSQL Database.
* **The trigger:** A burst of user traffic spins up hundreds of concurrent Lambda instances, with each instance attempting to open its own direct database connection[cite: 4].
* **The signal you would see and where:** `DatabaseConnections` maxing out in RDS CloudWatch metrics, and `FATAL: sorry, too many clients already` errors in the application logs[cite: 4].
* **What you would do about it:** Implement a managed connection pooler like Amazon RDS Proxy to multiplex connections between the ephemeral functions and the database.

**4. API Gateway hard timeout on synchronous processing**
* **What goes wrong:** The API gateway forcibly cuts the connection and returns a 504 Gateway Timeout before the backend function can finish processing.
* **Which component:** FastAPI Web Service.
* **The trigger:** A user triggers a complex report generation that takes longer than the 29-second maximum integration timeout limit of API Gateway.
* **The signal you would see and where:** `IntegrationError` and 5xx errors spiking in API Gateway metrics, even if the Lambda logs show the function eventually succeeded.
* **What you would do about it:** Decouple the endpoint. Have the API immediately return a `202 Accepted` response and place the heavy task onto the message broker for the async background worker to handle.

## Reversal Criterion

The decision we would reverse first is running the FastAPI Web Service in the serverless function shape. The specific evidence that would make us reverse it is if the measured p95 latency on the `GET /api/v1/applications` endpoint exceeds 800 milliseconds in Module 7's deployed environment due to cold starts[cite: 4]. If we hit this exact threshold, we will migrate the web service to the container-on-demand shape (AWS Fargate) to ensure consistent user-facing response times[cite: 4].