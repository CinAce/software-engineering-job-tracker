# Deployment Decision

## Part 2: Deployment-Shape Decision

For each part of the application, we chose between:

- Long-running server
- Container-on-demand (scale-to-zero)
- Function

The choices below are based on the workload profile from Part 1.

## Deployment Decisions

| Component | Chosen Shape | Profile Rows That Drove the Choice | Rejected Shape | Why It Was Rejected | What Would Make Us Switch |
|---|---|---|---|---|---|
| Health and Root Endpoints | Long-running server | Latency budget: under 200 ms. Arrival pattern: health checks are steady. | Function | The steady health checks mean this endpoint is used regularly, and a cold start could make a health check slower. | If traffic becomes very low and hosted function cold starts stay under 200 ms, we could switch to a function. |
| Authentication Endpoints | Long-running server | Latency budget: under 1 second. State: authentication depends on user data in the database. | Function | Login is user-visible and depends on the database. We want to avoid adding cold-start delay to login. | If measured function p95 stays under 1 second during real deployment and database connections are not a problem, we could switch. |
| Task Endpoints | Long-running server | Latency budget: under 200 ms. Requests: about 3,000 per month, with a guess range of 1,000-10,000. | Function | These are normal user-facing requests and need quick database access. | If traffic stays near the low end of our estimate and a function can consistently stay below the 200 ms p95 goal, we could switch. |
| Job Posting Scrape Worker | Container-on-demand | Arrival pattern: event-driven and bursty. Requests: only about 200 jobs per month, with a guess range of 50-1,000. | Long-running server | Keeping a worker running all the time could waste resources when there are no scrape jobs. | If scrape jobs become frequent enough that the worker is almost always busy, we could move it to a long-running container. |
| Application Summary Export Worker | Container-on-demand | Arrival pattern: event-driven and bursty. Requests: only about 100 jobs per month, with a guess range of 25-500. | Long-running server | The worker does not need to run all the time when exports are requested only occasionally. | If export traffic increases enough that the worker is running most of the time, a long-running container may make more sense. |
| Event Publishing API | Long-running server | Latency budget: under 200 ms. State: it needs a connection to RabbitMQ to publish events. | Function | It is already part of the main API and needs quick communication with RabbitMQ. Separating it into a function would add more complexity for little benefit at our expected traffic. | If event publishing becomes a much larger and more independent workload, we could separate it from the main API. |
| Notification Subscriber | Long-running server | Arrival pattern: event-driven. Long-running risk: the subscriber stays running and waits for messages. | Function | The subscriber is designed to stay connected to RabbitMQ and wait for messages. A function does not match the current design as well. | If the target platform can directly start a function from each RabbitMQ event without needing a subscriber to stay running, we could switch. |
| Analytics Subscriber | Long-running server | Arrival pattern: event-driven. Long-running risk: the subscriber stays running and waits for messages. | Function | Like the notification subscriber, this component is designed to stay connected to RabbitMQ waiting for events. | If events can directly trigger functions and our event volume stays low, we could switch. |

---

# Why We Chose These Shapes

## Main API

The health, authentication, task, and event publishing endpoints will stay together as a **long-running server**.

These endpoints are user-facing or support the main API. Our project also has a goal of keeping normal local API responses below 200 ms.

The API also communicates with the database and RabbitMQ. Keeping these endpoints together in one server keeps the design simple and avoids creating a separate function for every small part of the API.

Our local Module 4 test also showed that the server shape performed well. The warm server p95 was about **6.83 ms**, which is well below our 200 ms local goal.

---

## Job Posting Scrape Worker

The scrape worker will use a **container-on-demand** shape.

The workload is event-driven and we only estimate about 200 jobs per month. Keeping a separate worker running all month when it may spend most of its time waiting would not be a good use of resources.

A container-on-demand allows the worker to run when work is available and stop when it is no longer needed.

We rejected a long-running worker because our expected job volume is low.

We also considered a function, but scraping could depend on outside websites and could take longer than a normal request. A container gives us more room if the scraping process becomes larger later.

---

## Application Summary Export Worker

The export worker will also use a **container-on-demand** shape.

We only estimate around 100 export jobs per month. This means the worker could spend a large amount of time doing nothing if it stayed running continuously.

An on-demand container matches this workload because it only needs compute when an export needs to be created.

We rejected a long-running worker because of the low expected workload.

If exports become much more common later, we could change it to a long-running worker.

---

## Notification Subscriber

The notification subscriber will use a **long-running server/container**.

This component is different from the scrape and export workers. It is designed to stay connected to RabbitMQ and wait for events.

Because of this, keeping the subscriber running matches the current design better than starting it for each individual event.

We rejected the function shape because our current design uses a RabbitMQ consumer that waits for messages.

If a future target can directly trigger a function from the RabbitMQ events, then a function could become an option.

---

## Analytics Subscriber

The analytics subscriber will also use a **long-running server/container**.

Like the notification subscriber, it waits for RabbitMQ events instead of being started directly by a user request.

Keeping the subscriber running allows it to maintain its connection to RabbitMQ and process events when they arrive.

We would reconsider this if our deployment target supports directly starting a function from the events.

---

# Architecture Diagram

```text
                         User
                           |
                           | HTTPS
                           v
                +----------------------+
                |   Long-Running API   |
                |----------------------|
                | Health / Root        |
                | Authentication       |
                | Tasks                |
                | Event Publishing     |
                | Scrape Requests      |
                | Export Requests      |
                +----------+-----------+
                           |
                +----------+----------+
                |                     |
                v                     v
        +---------------+      +---------------+
        |   Database    |      |   RabbitMQ    |
        | Persistent    |      |    Broker     |
        |     Data      |      +-------+-------+
        +---------------+              |
                              +---------+---------+
                              |         |         |
                              v         v         v
                       +-----------+ +-----------+ +-----------+
                       | Scrape    | |Notification| | Analytics |
                       | Worker    | | Subscriber| | Subscriber|
                       |           | |           | |           |
                       | On-Demand | |Long-      | |Long-      |
                       | Container | |Running    | |Running    |
                       +-----------+ +-----------+ +-----------+
                              |
                              |
                              v
                       Outside Job
                         Sources

                              +
                              |
                              | export messages
                              v
                       +-----------+
                       |  Export   |
                       |  Worker   |
                       |           |
                       | On-Demand |
                       | Container |
                       +-----------+
```

The API is the main entry point for users.

Normal application information is stored in the database. Work that does not need to finish during the original HTTP request is sent through RabbitMQ.

The scrape and export workers can run when their work is needed. The notification and analytics subscribers stay running because they wait for RabbitMQ events.

---

# Capability Contract

We are not choosing a deployment provider in this milestone. Instead, these are the capabilities that a future target needs to support our design.

| Requirement | Needed? | Why? |
|---|---|---|
| **C1: Runs an OCI image we pushed and returns an HTTPS URL** | Yes | Our API and workers are already containerized. We need to be able to run our container image, and users need an HTTPS URL for the API. |
| **C2: S3-compatible object storage reachable using SigV4 credentials** | Yes | The project has an object-storage adapter and stored-file support. This gives us a place for files that should not live inside a temporary container. |
| **C3: Credentials narrower than account-wide, using OIDC federation or a revocable token** | Yes | The application will need credentials for services such as storage. We do not want the application using full account credentials. |
| **C4: A published and scriptable way to list and delete resources** | Yes | We need to be able to see what project resources exist and remove them when we are finished. This also helps prevent forgotten resources from continuing to run. |
| **C5: A spend alert or hard spending cap** | Yes | This is a student project with a limited budget. We need a way to notice or stop unexpected spending. |
| **C6: A stated free allowance or a cost under $5 for the term's usage** | Yes | Our workload is small and the project should stay inexpensive for the semester. |

## Compute Requirements

Our design does **not require a function service**.

The main API and subscribers can run as containers. The scrape and export workers are also containers, but we want them to be able to scale down when they are not being used.

Because of this, our main compute requirement is **C1**, the ability to run our OCI container images.

For the two on-demand workers, it would also be useful for a target to support starting or scaling container work based on demand. If a target cannot do that, we could run those workers continuously instead, but that may increase idle cost.

We do not require a function-specific event trigger, scheduler, or per-invocation billing system.

---

# Part 2 Summary

Our deployment decision keeps the user-facing API simple by running it as a long-running server. The notification and analytics subscribers also stay running because they wait for RabbitMQ messages.

The scrape and export workers are different because their expected workloads are small and event-driven. We chose on-demand containers for those so they do not need to use resources while there is no work.

We did not choose a cloud provider in this section. The C1-C6 requirements describe what a future target needs to provide. The actual target will be compared against these requirements later.

---

## Part 4: Runtime Lifecycle

### Compute Runtime: AWS Lambda (Python)
* **Target Version:** `python3.12`
* **End of Support Date:** October 31, 2028
* **Platform Consequence:** On this date (Phase 1), AWS Lambda stops applying security patches and technical support ends. The code will continue to run, but function creation is blocked on January 10, 2029.
* **Upgrade Ownership:** Our team owns the upgrade process. We must schedule a migration to a newer Python runtime (e.g., Python 3.13 or 3.14) and update our IaC templates before the October 2028 deadline, which is well past the end of our current academic term.

### Database Engine: Amazon RDS for PostgreSQL
* **Target Version:** PostgreSQL 16
* **End of Standard Support Date:** February 28, 2029
* **Platform Consequence:** At the end of standard support, AWS will automatically enroll the database in RDS Extended Support, which incurs additional monthly charges. The database will not stop running, but it will become significantly more expensive.
* **Upgrade Ownership:** Our team owns the major version upgrade. While AWS can handle automated minor version patches during scheduled maintenance windows, we must manually test and execute the upgrade to a newer major version (like PostgreSQL 17 or 18) before February 2029.
