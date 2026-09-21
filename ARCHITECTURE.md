# Architecture and Message Flow

## System Diagram
```text
[Client] --> (:8000) [Gateway (Nginx)]
                          |
             +------------+------------+
             |            |            |
         [API-1]      [API-2]      [API-3]
             |            |            |
             +------------+------------+
                          | (amqp)
                     [RabbitMQ]
                     /        \
           (scrape_queue)  (export_queue)
                  |             |
              [Worker]      [Worker]

Asynchronous Workflows
1. Job Posting Scraper (Workflow A)

Trigger: POST /api/jobs/scrape

Routing Key / Queue: scrape_queue

Payload Schema: {"id": "uuid", "url": "string", "job_id": "integer"}

Consumer: worker.py (handle_scrape)

Failure Behavior: If the worker crashes before acknowledging, the message remains on scrape_queue and is redelivered to the next available worker.

2. Application Summary Export (Workflow B)

Trigger: POST /api/exports

Routing Key / Queue: export_queue

Payload Schema: {"id": "uuid", "user_id": "integer"}

Consumer: worker.py (handle_export)

Failure Behavior: Unacknowledged messages are returned to export_queue for redelivery upon worker recovery.
## Event-Driven Routing

Part 2 uses the durable RabbitMQ topic exchange `job_tracker.events`. Publishers send events using dotted routing keys and do not know which subscribers receive them.

### Event Envelope

Every event uses the following common fields:

- `event_id`: unique UUID for the event
- `event_type`: dotted event type and routing key
- `version`: event schema version
- `timestamp`: UTC event creation time
- `source`: service that produced the event
- `data`: event-specific payload

### Event Types

1. `application.created`
   - Data: `application_id`, `job_id`, `user_id`, `status`

2. `application.status_updated`
   - Data: application status update information

3. `resume.uploaded`
   - Data: resume upload information

4. `job.created`
   - Data: job creation information

5. `job.deleted`
   - Data: job deletion information

### Subscribers

Notification Subscriber

- Queue: `notification.events`
- Binding keys: `application.*`, `resume.*`
- Consumer: `app.events.notification_subscriber`
- Failure behavior: messages are acknowledged only after successful processing; failed processing is negatively acknowledged without requeue.

Analytics Subscriber

- Queue: `analytics.events`
- Binding keys: `*.created`, `job.deleted`
- Consumer: `app.events.analytics_subscriber`
- Failure behavior: messages are acknowledged only after successful processing; failed processing is negatively acknowledged without requeue.

### Fanout Demonstration

The `application.created` routing key matches both `application.*` and `*.created`. RabbitMQ therefore routes one published event to both `notification.events` and `analytics.events`.

The publisher only publishes to the `job_tracker.events` exchange using the event type as the routing key. It does not reference either subscriber queue.

Evidence is recorded in `evidence/04-fanout.txt`.
