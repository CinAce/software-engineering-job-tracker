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