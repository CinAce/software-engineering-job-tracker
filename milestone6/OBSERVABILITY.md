# Milestone 6 - Part 3: Observability

## 3a. Prometheus Scraping

We used Prometheus and Grafana to monitor the Job Tracker
running locally in Docker.

Prometheus scrapes the application every 15 seconds at
http://job-tracker:8000/metrics/.

The trailing slash is important because the metrics endpoint
is mounted as a separate ASGI application.

The Prometheus target returned UP (1), confirming that
Prometheus can collect metrics from the application.

Configuration: monitoring/prometheus.yml

Images:
- Prometheus: prom/prometheus:v3.5.0
- Grafana: grafana/grafana:12.1.0
- Job Tracker: docker.io/marshaun06/job-tracker:e4686d7

No host exporter is used.

## 3b. Traffic and Error Queries

Request rate:

    sum(rate(itc531_requests_total[5m])) or vector(0)

Measured result: about 0.1608 requests per second.

This tells us how many requests the application is handling.
A sudden drop to zero during expected activity could mean
the application is unavailable. A sudden large increase
could mean unexpected traffic. We would check the health
endpoint, logs, and recent changes.

Server error rate:

    sum(rate(itc531_requests_total{status=~"5.."}[5m])) or vector(0)

Measured result: 0 server errors per second.

This counts HTTP 500-level responses. A consistent nonzero
value would be a problem because it means requests are
failing on the server. We would check the application logs,
identify the failing endpoint, and investigate its dependencies.

We use rate() because a counter only increases over time.
rate() converts that total into an average per-second rate
over the selected five-minute window.

## 3c. Grafana Dashboard

The dashboard has two panels:

1. Request rate (requests/sec)
2. Server error rate (errors/sec)

Both panels use the provisioned Prometheus data source.

During testing, we sent 35 requests to the local /health
endpoint. The request-rate graph increased, while the
server-error rate stayed at zero.

Dashboard screenshot:
evidence/grafana-dashboard.png

Dashboard configuration:
monitoring/grafana/dashboards/jobtracker.json

## 3d. Metric Labels and Cardinality

Our application's request counter uses these labels:

- method: The HTTP method, such as GET or POST. Values are
  limited in practice to the HTTP methods the API supports.
- path: The matched route template, such as /health.
  Values come from the application's defined routes, plus
  an unmatched-route fallback, so this is bounded.
- status: The HTTP response status code, such as 200 or 500.
  HTTP status codes come from a finite set.

Our request latency histogram uses:

- method: The HTTP method, as described above.
- path: The matched route template, as described above.
- le: The histogram bucket boundary, automatically added
  by prometheus_client from a fixed set of buckets.

The histogram also produces count and sum series using
the method and path labels.

Prometheus adds job and instance labels to identify its
scrape target. These are not application-defined labels.

The middleware reads the route after call_next(request),
which means the router has already processed the request.
This allows the metric to use a route template rather than
a different label for every ID in a URL.

For example, requests to /applications/1 and
/applications/2 should share the same route-template label,
if they match a parameterized application route.

This prevents the number of metric series from growing
unnecessarily as users access more records.
