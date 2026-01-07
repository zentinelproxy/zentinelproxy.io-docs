+++
title = "Observability"
weight = 6
+++

Complete observability setup with Prometheus metrics, Grafana dashboards, and Jaeger distributed tracing.

## Use Case

- Monitor request rates, latencies, and errors
- Visualize traffic patterns and health status
- Trace requests across services
- Alert on anomalies

## Architecture

```
                    ┌─────────────────┐
                    │    Sentinel     │
                    │   :8080/:9090   │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
   ┌───────────┐      ┌───────────┐      ┌───────────┐
   │Prometheus │      │  Grafana  │      │  Jaeger   │
   │  :9091    │◄─────│  :3000    │      │  :16686   │
   └───────────┘      └───────────┘      └───────────┘
```

## Configuration

Create `sentinel.kdl`:

```kdl
// Observability Configuration
// Metrics, logging, and distributed tracing

server {
    worker-threads 0
    graceful-shutdown-timeout-secs 30
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

routes {
    route "api" {
        matches {
            path-prefix "/api/"
        }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
        health-check {
            type "http" {
                path "/health"
            }
            interval-secs 10
        }
    }
}

observability {
    // Prometheus metrics endpoint
    metrics {
        enabled true
        address "0.0.0.0:9090"
        path "/metrics"
    }

    // Structured JSON logging
    logging {
        level "info"
        format "json"
        access-log {
            enabled true
            fields ["method" "path" "status" "latency" "upstream" "client_ip"]
        }
    }

    // OpenTelemetry tracing
    tracing {
        enabled true
        service-name "sentinel"
        endpoint "http://jaeger:4317"
        protocol "grpc"  // or "http"
        sample-rate 1.0  // Sample all requests (reduce in production)
        propagation "w3c"  // W3C Trace Context
    }
}
```

## Prometheus Setup

### prometheus.yml

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'sentinel'
    static_configs:
      - targets: ['sentinel:9090']
    metrics_path: /metrics

  - job_name: 'sentinel-agents'
    static_configs:
      - targets:
        - 'sentinel-waf:9091'
        - 'sentinel-auth:9092'
        - 'sentinel-ratelimit:9093'
```

### Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `sentinel_requests_total` | Counter | Total requests by route, method, status |
| `sentinel_request_duration_seconds` | Histogram | Request latency distribution |
| `sentinel_upstream_requests_total` | Counter | Requests per upstream target |
| `sentinel_upstream_latency_seconds` | Histogram | Upstream response times |
| `sentinel_upstream_health` | Gauge | Upstream health (1=healthy, 0=unhealthy) |
| `sentinel_connections_active` | Gauge | Active client connections |
| `sentinel_agent_duration_seconds` | Histogram | Agent processing time |
| `sentinel_agent_errors_total` | Counter | Agent errors by type |

### Useful PromQL Queries

```promql
# Request rate (requests per second)
rate(sentinel_requests_total[5m])

# Error rate (5xx responses)
rate(sentinel_requests_total{status=~"5.."}[5m]) / rate(sentinel_requests_total[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(sentinel_request_duration_seconds_bucket[5m]))

# Upstream health status
sentinel_upstream_health

# Requests by route
sum by (route) (rate(sentinel_requests_total[5m]))
```

## Grafana Dashboard

### dashboard.json

```json
{
  "title": "Sentinel Overview",
  "panels": [
    {
      "title": "Request Rate",
      "type": "timeseries",
      "targets": [
        {
          "expr": "sum(rate(sentinel_requests_total[5m]))",
          "legendFormat": "Total"
        }
      ]
    },
    {
      "title": "Error Rate",
      "type": "gauge",
      "targets": [
        {
          "expr": "sum(rate(sentinel_requests_total{status=~\"5..\"}[5m])) / sum(rate(sentinel_requests_total[5m])) * 100"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "thresholds": {
            "steps": [
              {"value": 0, "color": "green"},
              {"value": 1, "color": "yellow"},
              {"value": 5, "color": "red"}
            ]
          },
          "unit": "percent"
        }
      }
    },
    {
      "title": "Latency (p50, p95, p99)",
      "type": "timeseries",
      "targets": [
        {
          "expr": "histogram_quantile(0.50, rate(sentinel_request_duration_seconds_bucket[5m]))",
          "legendFormat": "p50"
        },
        {
          "expr": "histogram_quantile(0.95, rate(sentinel_request_duration_seconds_bucket[5m]))",
          "legendFormat": "p95"
        },
        {
          "expr": "histogram_quantile(0.99, rate(sentinel_request_duration_seconds_bucket[5m]))",
          "legendFormat": "p99"
        }
      ]
    },
    {
      "title": "Upstream Health",
      "type": "stat",
      "targets": [
        {
          "expr": "sentinel_upstream_health",
          "legendFormat": "{{upstream}}/{{target}}"
        }
      ]
    }
  ]
}
```

## Jaeger Tracing

### docker-compose.yml

```yaml
version: '3.8'

services:
  sentinel:
    image: ghcr.io/raskell-io/sentinel:latest
    ports:
      - "8080:8080"
      - "9090:9090"
    volumes:
      - ./sentinel.kdl:/etc/sentinel/sentinel.kdl
    environment:
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317

  jaeger:
    image: jaegertracing/all-in-one:1.50
    ports:
      - "16686:16686"  # UI
      - "4317:4317"    # OTLP gRPC
      - "4318:4318"    # OTLP HTTP
    environment:
      - COLLECTOR_OTLP_ENABLED=true

  prometheus:
    image: prom/prometheus:v2.47.0
    ports:
      - "9091:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:10.1.0
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning
      - ./grafana/dashboards:/var/lib/grafana/dashboards
```

### Trace Context Propagation

Sentinel propagates trace context through requests:

```bash
# Incoming request with trace context
curl -H "traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01" \
     http://localhost:8080/api/users
```

Backend receives headers:
- `traceparent` - W3C Trace Context
- `tracestate` - Vendor-specific trace state
- `X-Request-Id` - Sentinel request ID

### Viewing Traces

1. Open Jaeger UI: http://localhost:16686
2. Select service: `sentinel`
3. Find traces by:
   - Operation (route name)
   - Tags (status, method, path)
   - Duration
   - Request ID

## Alerting

### Prometheus Alerting Rules

Create `alerts.yml`:

```yaml
groups:
  - name: sentinel
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(sentinel_requests_total{status=~"5.."}[5m]))
          / sum(rate(sentinel_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"

      - alert: HighLatency
        expr: |
          histogram_quantile(0.95, rate(sentinel_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "95th percentile latency is {{ $value }}s"

      - alert: UpstreamDown
        expr: sentinel_upstream_health == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Upstream target is down"
          description: "{{ $labels.upstream }}/{{ $labels.target }} is unhealthy"

      - alert: AgentErrors
        expr: rate(sentinel_agent_errors_total[5m]) > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Agent errors detected"
          description: "Agent {{ $labels.agent }} has errors"
```

## Log Aggregation

### Structured Log Output

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "info",
  "message": "request completed",
  "request_id": "abc123",
  "method": "GET",
  "path": "/api/users",
  "status": 200,
  "latency_ms": 45,
  "upstream": "backend",
  "client_ip": "192.168.1.100",
  "trace_id": "0af7651916cd43dd8448eb211c80319c"
}
```

### Loki Integration

```yaml
# loki configuration
scrape_configs:
  - job_name: sentinel
    static_configs:
      - targets:
          - localhost
        labels:
          job: sentinel
          __path__: /var/log/sentinel/*.log
```

## Testing

### Verify Metrics

```bash
curl http://localhost:9090/metrics | grep sentinel
```

### Generate Test Traffic

```bash
# Install hey (HTTP load generator)
go install github.com/rakyll/hey@latest

# Generate load
hey -n 1000 -c 10 http://localhost:8080/api/users
```

### Check Traces

```bash
# Make a traced request
curl -H "X-Request-Id: test-trace-123" http://localhost:8080/api/users

# Find in Jaeger by tag: request_id=test-trace-123
```

## Next Steps

- [Security](../security/) - Add WAF and auth monitoring
- [Microservices](../microservices/) - Trace across services
- [Load Balancer](../load-balancer/) - Monitor upstream distribution
