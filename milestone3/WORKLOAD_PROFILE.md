# Workload Profile

This document describes the expected workload for the Software Engineering Job Tracker. Since the project is still being developed and does not have real users yet, most traffic numbers are estimates. Estimates are labeled as guesses and include a range when possible.

## 1. Health and Root Endpoints

**Endpoints:** `GET /` and `GET /health`

**Requests per month:**  
Estimate: about 9,000 requests per month.  
Guess range: 5,000-15,000.

Most of these requests would come from health checks. If a health check happens about every five minutes, that would be around 8,640 checks in a 30-day month.

**Arrival pattern:**  
Mostly steady.  
Peak-to-trough ratio: about 2:1.

Health checks should happen at a steady rate, while the root endpoint would mostly be used by developers or users checking the service.

**Duration:**  
The local `/health` test had a p95 of about **6.83 ms**. One request took about 199 ms, which raised the mean to about **8.23 ms**.

**Memory:**  
The Module 4 server container used about **61.86 MiB** during local testing. This was measured with `docker stats --no-stream`.

**Concurrency:**  
Estimate: 1-3 requests at the same time.  
Guess range: 1-5.

**State:**  
The root endpoint does not need stored state. The health endpoint checks the database, so it depends on the database being available.

**Latency budget:**  
Target p95: under 200 ms.

A slow health check could make the service appear unhealthy or make it take longer to notice a problem.

**Long-running risk:**  
Low. These are short HTTP requests with no streaming or long-running connection.

---

## 2. Authentication Endpoints

**Endpoints:** `POST /auth/register`, `POST /auth/login`, and `GET /auth/me`

**Requests per month:**  
Estimate: about 300 requests per month.  
Guess range: 100-1,000.

This is a guess because the project does not have real user traffic yet.

**Arrival pattern:**  
Bursty and somewhat diurnal.  
Peak-to-trough ratio: about 10:1.

Users would probably register or log in more during normal daytime and evening hours instead of at a steady rate all day.

**Duration:**  
Not directly measured. Registration and login may take longer than basic endpoints because password hashing and password checking are involved.

**Memory:**  
Uses the same API server process. The Module 4 server used about **61.86 MiB** during local testing.

**Concurrency:**  
Estimate: 1-3 requests at the same time.  
Guess range: 1-5.

**State:**  
User accounts, password hashes, roles, and account status are stored in the relational database.

**Latency budget:**  
Target p95: under 1 second.

Authentication can take a little longer than a basic API request, but a long wait would make login and registration feel slow.

**Long-running risk:**  
Low. There are no WebSockets, streaming responses, or operations expected to last more than 60 seconds.

---

## 3. Task Endpoints

**Endpoints:** `POST /tasks`, `GET /tasks`, `GET /tasks/{task_id}`, and `DELETE /tasks/{task_id}`

**Requests per month:**  
Estimate: about 3,000 requests per month.  
Guess range: 1,000-10,000.

This is a guess because there is no real production traffic yet.

**Arrival pattern:**  
Bursty and diurnal.  
Peak-to-trough ratio: about 10:1.

Users would probably make several requests while actively using the application and very few while nobody is using it.

**Duration:**  
Not directly measured. These endpoints mainly perform basic database operations, so they are expected to be short.

**Memory:**  
Uses the API server process. The Module 4 server used about **61.86 MiB** during local testing.

**Concurrency:**  
Estimate: 2-5 requests at the same time.  
Guess range: 1-10.

**State:**  
Task information is stored in the relational database. Each task currently contains an ID, title, completion status, and creation time.

**Latency budget:**  
Target p95: under 200 ms.

The project proposal uses sub-200 ms local API response time as a success goal.

**Long-running risk:**  
Low. These are normal database requests and should not run longer than 60 seconds.

---

## 4. Job Posting Scrape Workflow

**API endpoint:** `POST /api/jobs/scrape`

**Background work:** `scrape_queue`

**Requests/jobs per month:**  
Estimate: about 200 jobs per month.  
Guess range: 50-1,000.

This is a guess because the application does not have real production usage yet.

**Arrival pattern:**  
Event-driven and bursty.  
Peak-to-trough ratio: about 20:1.

A scrape job only starts when the API receives a request for one, so jobs may arrive close together instead of at a steady rate.

**Duration:**  
Not measured yet for the complete background job.

Estimate: p50 around 2 seconds and p95 around 10 seconds. These are guesses and should be replaced if the worker gets real timing measurements.

**Memory:**  
Estimate: 100-200 MiB for a worker. This is a guess because the worker was not separately measured during the Module 4 test.

**Concurrency:**  
Estimate: 1 job per worker at a time. Additional work can wait in RabbitMQ.

**State:**  
The API creates a task ID and sends a persistent message to RabbitMQ's `scrape_queue`. RabbitMQ holds the message until a worker processes it.

**Latency budget:**  
The API should accept the request in under 200 ms. The background scrape itself should normally finish within about 30 seconds.

Since the API returns `202 Accepted`, the user does not need to wait for the entire scrape to finish before receiving a response.

**Long-running risk:**  
Medium. Scraping could depend on another website or network connection. A slow outside service could make the job take longer than expected.

---

## 5. Application Summary Export Workflow

**API endpoint:** `POST /api/exports`

**Background work:** `export_queue`

**Requests/jobs per month:**  
Estimate: about 100 jobs per month.  
Guess range: 25-500.

This is a guess because there is no production traffic yet.

**Arrival pattern:**  
Event-driven and bursty.  
Peak-to-trough ratio: about 20:1.

Exports only happen when requested.

**Duration:**  
Not directly measured.

Estimate: p50 around 500 ms and p95 around 3 seconds. These values are guesses until the complete export worker is measured.

**Memory:**  
Estimate: 100-200 MiB for a worker. This is a guess because the worker was not separately measured.

**Concurrency:**  
Estimate: 1-2 jobs being processed at the same time depending on the number of workers.

**State:**  
The API sends a persistent message containing a task ID and user ID to RabbitMQ's `export_queue`.

**Latency budget:**  
The API should accept the request in under 200 ms. The completed export should normally be ready within about 10 seconds.

**Long-running risk:**  
Low to medium. A large export could take longer, but normal exports are not expected to run for more than 60 seconds.

---

## 6. Event Publishing API

**Endpoint:** `POST /api/events/publish`

**Requests per month:**  
Estimate: about 1,000 events per month.  
Guess range: 300-5,000.

This is a guess based on a small job tracking application.

**Arrival pattern:**  
Event-driven and bursty.  
Peak-to-trough ratio: about 20:1.

Events happen when something changes in the application, so they will not arrive at a completely steady rate.

**Duration:**  
Not directly measured.

The endpoint creates the event and publishes it to RabbitMQ. It returns `202 Accepted` when the event is published.

**Memory:**  
Uses the API server process. The Module 4 server used about **61.86 MiB** during local testing.

**Concurrency:**  
Estimate: 1-5 event publishing requests at the same time.  
Guess range: 1-10.

**State:**  
Events are published to the durable RabbitMQ topic exchange named `job_tracker.events`. Messages are marked as persistent.

**Latency budget:**  
Target p95: under 200 ms.

If the broker is unavailable, the API returns a `503 Service Unavailable` response.

**Long-running risk:**  
Low. Publishing an event should be a short operation.

---

## 7. Notification Subscriber

**Component:** `app.events.notification_subscriber`

**Jobs per month:**  
Estimate: about 1,000 events per month.  
Guess range: 300-5,000.

**Arrival pattern:**  
Event-driven and bursty.  
Peak-to-trough ratio: about 20:1.

The subscriber receives application and resume events from RabbitMQ.

**Duration:**  
Not directly measured.

Estimate: p50 around 10 ms and p95 around 100 ms for the current simple processing. These values are guesses.

**Memory:**  
Estimate: 50-100 MiB. This should be replaced with a direct measurement if the subscriber is measured separately.

**Concurrency:**  
The subscriber is designed to process a small amount of work at a time. RabbitMQ can hold extra messages until the subscriber is ready.

**State:**  
Messages are stored in RabbitMQ until they are processed. The notification subscriber receives events from the `notification.events` queue.

**Latency budget:**  
Target p95: under 1 second after receiving a message.

A delay would mean the notification-related event takes longer to process, but it would not block the original API request.

**Long-running risk:**  
The subscriber itself is a long-running process, but each individual message should be short. Individual jobs are not expected to run longer than 60 seconds.

---

## 8. Analytics Subscriber

**Component:** `app.events.analytics_subscriber`

**Jobs per month:**  
Estimate: about 1,000 events per month.  
Guess range: 300-5,000.

**Arrival pattern:**  
Event-driven and bursty.  
Peak-to-trough ratio: about 20:1.

The analytics subscriber receives matching events from RabbitMQ.

**Duration:**  
Not directly measured.

Estimate: p50 around 10 ms and p95 around 100 ms for the current simple processing. These are guesses.

**Memory:**  
Estimate: 50-100 MiB. This is a guess until the subscriber is directly measured.

**Concurrency:**  
Expected to process a small number of messages at once, while RabbitMQ holds messages that are waiting.

**State:**  
Messages are stored in RabbitMQ. The analytics subscriber receives events through the `analytics.events` queue.

**Latency budget:**  
Target p95: under 1 second after receiving an event.

Analytics work happens in the background, so a small delay does not block the original user request.

**Long-running risk:**  
The subscriber stays running while waiting for events, but each individual event should be short. Individual jobs are not expected to run longer than 60 seconds.

---

# Measured Baseline

For the required baseline, I compared the server-shaped and function-shaped versions locally using the Module 4 setup.

The server was tested using:

`GET http://localhost:8000/health`

The function was tested using:

`POST http://localhost:8001/invoke`

The function request used:

```json
{"name":"Marshaun"}
```

## Warm Server Test

I ran 50 sequential requests with:

```bash
for i in {1..50}; do
  curl -s -o /dev/null \
    -w "%{time_total}\n" \
    http://localhost:8000/health
done | tee server-warm.txt
```

### Results

- Requests: 50
- Mean: about **8.23 ms**
- p95: about **6.83 ms**
- One request took about **199 ms**, which raised the mean.

The other requests were mostly only a few milliseconds. I kept the slower request in the results instead of removing it.

## Warm Function Test

I ran 50 sequential requests with:

```bash
for i in {1..50}; do
  curl -s -o /dev/null \
    -w "%{time_total}\n" \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{"name":"Marshaun"}' \
    http://localhost:8001/invoke
done | tee function-warm.txt
```

### Results

- Requests: 50
- Mean: about **4.28 ms**
- p95: about **5.58 ms**

Most requests completed in around 2-5 ms.

## First-Invocation Test

For the server, I stopped and restarted the application container and then sent a request to `/health`.

Commands:

```bash
docker compose stop app
docker compose start app

until curl -s -o /dev/null http://localhost:8000/; do sleep 0.1; done

curl -s -o /dev/null \
  -w "HTTP: %{http_code}\nTime: %{time_total}\n" \
  http://localhost:8000/health
```

Result:

- HTTP status: **200**
- First measured request: **10.561 ms**

For the function, I stopped and restarted the function container and then invoked it.

Commands:

```bash
docker compose stop fn
docker compose start fn

curl -s -o /dev/null \
  -w "HTTP: %{http_code}\nTime: %{time_total}\n" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"name":"Marshaun"}' \
  http://localhost:8001/invoke
```

Result:

- HTTP status: **200**
- First measured request: **9.707 ms**

## Memory Measurement

I used:

```bash
docker stats --no-stream
```

The local results were:

| Component | Memory |
|---|---:|
| Function (`itc531m4-fn-1`) | 36.31 MiB |
| Server (`itc531m4-app-1`) | 61.86 MiB |
| Database (`itc531m4-db-1`) | 21.74 MiB |

These numbers show the approximate memory being used by the containers at the time the command was run. They do not show the maximum amount of memory the containers could use under a heavy workload.

## What the Local Test Tells Us

The local test shows that both shapes respond quickly on the development computer. In these tests, both normally completed requests in only a few milliseconds.

The function-shaped version also used less memory during the local measurement.

However, this test does **not** show exactly how a hosted cloud function would behave. Both versions were running locally in Docker. A real hosted function could have extra startup time when the provider has to create a new function instance. Network delay and cloud hardware could also change the results.

Because of this, the local measurements are useful as a baseline, but they should not be treated as exact cloud performance numbers.

# Estimation Notes

Most monthly traffic, concurrency, and background job numbers in this document are guesses because the project does not have real production users yet.

The estimates were based on a small job tracking application used mainly by students and job seekers. Ranges were included because actual usage could be much lower or higher.

The latency and memory numbers in the measured baseline are different because those came from actual local tests using the Module 4 Docker setup.