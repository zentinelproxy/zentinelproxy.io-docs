+++
title = "Monitoring Setup"
weight = 6
updated = 2026-02-19
+++

Production monitoring and observability for Zentinel deployments.

## Metrics Endpoint

Zentinel exposes Prometheus metrics on the configured address:

```kdl
observability {
    metrics {
        enabled #true
        address "0.0.0.0:9090"
        path "/metrics"
    }
}
```

Verify:

```bash
curl http://localhost:9090/metrics
```

## Prometheus Setup

### prometheus.yml

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  # Zentinel proxy
  - job_name: 'zentinel'
    static_configs:
      - targets: ['zentinel:9090']
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        regex: '([^:]+):\d+'
        replacement: '${1}'

  # Zentinel agents
  - job_name: 'zentinel-agents'
    static_configs:
      - targets:
          - 'zentinel-waf:9091'
          - 'zentinel-auth:9092'
          - 'zentinel-ratelimit:9093'
```

### Docker Compose

```yaml
services:
  prometheus:
    image: prom/prometheus:v2.47.0
    ports:
      - "9091:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=15d'

volumes:
  prometheus-data:
```

### Kubernetes ServiceMonitor

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: zentinel
  labels:
    app: zentinel
spec:
  selector:
    matchLabels:
      app: zentinel
  endpoints:
    - port: metrics
      interval: 15s
      path: /metrics
```

## Key Metrics

### Request Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `zentinel_requests_total` | Counter | Total requests by route, method, status |
| `zentinel_request_duration_seconds` | Histogram | Request latency distribution |
| `zentinel_request_size_bytes` | Histogram | Request body size |
| `zentinel_response_size_bytes` | Histogram | Response body size |

### Upstream Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `zentinel_upstream_requests_total` | Counter | Requests per upstream target |
| `zentinel_upstream_latency_seconds` | Histogram | Upstream response time |
| `zentinel_upstream_health` | Gauge | Target health (1=healthy, 0=unhealthy) |
| `zentinel_upstream_connections_active` | Gauge | Active connections per upstream |

### Agent Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `zentinel_agent_duration_seconds` | Histogram | Agent processing time |
| `zentinel_agent_errors_total` | Counter | Agent errors by type |
| `zentinel_agent_decisions_total` | Counter | Agent decisions (allow/block) |

### System Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `zentinel_connections_active` | Gauge | Active client connections |
| `zentinel_connections_total` | Counter | Total connections |
| `process_cpu_seconds_total` | Counter | CPU usage |
| `process_resident_memory_bytes` | Gauge | Memory usage |

## Essential PromQL Queries

### Request Rate

```promql
# Requests per second
rate(zentinel_requests_total[5m])

# By route
sum by (route) (rate(zentinel_requests_total[5m]))

# By status code
sum by (status) (rate(zentinel_requests_total[5m]))
```

### Error Rate

```promql
# 5xx error rate
sum(rate(zentinel_requests_total{status=~"5.."}[5m]))
/ sum(rate(zentinel_requests_total[5m])) * 100

# 4xx rate
sum(rate(zentinel_requests_total{status=~"4.."}[5m]))
/ sum(rate(zentinel_requests_total[5m])) * 100
```

### Latency

```promql
# 50th percentile
histogram_quantile(0.50, rate(zentinel_request_duration_seconds_bucket[5m]))

# 95th percentile
histogram_quantile(0.95, rate(zentinel_request_duration_seconds_bucket[5m]))

# 99th percentile
histogram_quantile(0.99, rate(zentinel_request_duration_seconds_bucket[5m]))
```

### Upstream Health

```promql
# Unhealthy upstreams
zentinel_upstream_health == 0

# Upstream latency p95
histogram_quantile(0.95, rate(zentinel_upstream_latency_seconds_bucket[5m]))
```

## Alerting Rules

### alerts.yml

```yaml
groups:
  - name: zentinel
    rules:
      # High error rate
      - alert: ZentinelHighErrorRate
        expr: |
          sum(rate(zentinel_requests_total{status=~"5.."}[5m]))
          / sum(rate(zentinel_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate on Zentinel"
          description: "Error rate is {{ $value | humanizePercentage }}"

      # High latency
      - alert: ZentinelHighLatency
        expr: |
          histogram_quantile(0.95, rate(zentinel_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency on Zentinel"
          description: "p95 latency is {{ $value | humanizeDuration }}"

      # Upstream down
      - alert: ZentinelUpstreamDown
        expr: zentinel_upstream_health == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Upstream target is down"
          description: "{{ $labels.upstream }}/{{ $labels.target }} is unhealthy"

      # No requests
      - alert: ZentinelNoTraffic
        expr: |
          sum(rate(zentinel_requests_total[5m])) == 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "No traffic to Zentinel"
          description: "Zentinel has received no requests in 5 minutes"

      # Agent errors
      - alert: ZentinelAgentErrors
        expr: rate(zentinel_agent_errors_total[5m]) > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Agent errors detected"
          description: "Agent {{ $labels.agent }} has errors"

      # High memory
      - alert: ZentinelHighMemory
        expr: |
          process_resident_memory_bytes / 1024 / 1024 > 1024
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Zentinel using {{ $value | humanize }}MB"
```

## Grafana Dashboards

### Dashboard JSON

```json
{
  "title": "Zentinel Overview",
  "panels": [
    {
      "title": "Request Rate",
      "type": "timeseries",
      "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
      "targets": [{
        "expr": "sum(rate(zentinel_requests_total[5m]))",
        "legendFormat": "Requests/sec"
      }]
    },
    {
      "title": "Error Rate",
      "type": "gauge",
      "gridPos": {"x": 12, "y": 0, "w": 6, "h": 8},
      "targets": [{
        "expr": "sum(rate(zentinel_requests_total{status=~\"5..\"}[5m])) / sum(rate(zentinel_requests_total[5m])) * 100"
      }],
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
      "title": "Latency",
      "type": "timeseries",
      "gridPos": {"x": 0, "y": 8, "w": 12, "h": 8},
      "targets": [
        {
          "expr": "histogram_quantile(0.50, rate(zentinel_request_duration_seconds_bucket[5m]))",
          "legendFormat": "p50"
        },
        {
          "expr": "histogram_quantile(0.95, rate(zentinel_request_duration_seconds_bucket[5m]))",
          "legendFormat": "p95"
        },
        {
          "expr": "histogram_quantile(0.99, rate(zentinel_request_duration_seconds_bucket[5m]))",
          "legendFormat": "p99"
        }
      ]
    },
    {
      "title": "Upstream Health",
      "type": "stat",
      "gridPos": {"x": 12, "y": 8, "w": 6, "h": 8},
      "targets": [{
        "expr": "zentinel_upstream_health",
        "legendFormat": "{{upstream}}/{{target}}"
      }]
    }
  ]
}
```

## Health Checks

### Zentinel Health Endpoint

```bash
# Simple health check
curl http://localhost:9090/health

# Response
{"status": "healthy"}
```

### Detailed Health

```bash
curl http://localhost:9090/health/detailed

# Response
{
  "status": "healthy",
  "upstreams": {
    "backend": {
      "healthy": 2,
      "unhealthy": 0,
      "targets": [
        {"address": "10.0.0.1:3000", "healthy": true},
        {"address": "10.0.0.2:3000", "healthy": true}
      ]
    }
  },
  "agents": {
    "waf": {"status": "connected"},
    "auth": {"status": "connected"}
  }
}
```

### Kubernetes Probes

```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
    - name: zentinel
      livenessProbe:
        httpGet:
          path: /health
          port: 9090
        initialDelaySeconds: 5
        periodSeconds: 10
        failureThreshold: 3
      readinessProbe:
        httpGet:
          path: /health/detailed
          port: 9090
        initialDelaySeconds: 5
        periodSeconds: 5
        failureThreshold: 2
```

## Logging

### Structured Logging

```kdl
system {
    worker-threads 0
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

routes {
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
}

```

### Log Output

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
  "client_ip": "192.168.1.100"
}
```

### Log Aggregation with Loki

```yaml
# promtail.yml
server:
  http_listen_port: 9080

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: zentinel
    static_configs:
      - targets:
          - localhost
        labels:
          job: zentinel
          __path__: /var/log/zentinel/*.log
    pipeline_stages:
      - json:
          expressions:
            level: level
            status: status
      - labels:
          level:
          status:
```

## Distributed Tracing

### OpenTelemetry Configuration

```kdl
system {
    worker-threads 0
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

routes {
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
}

```

### Jaeger Setup

```yaml
services:
  jaeger:
    image: jaegertracing/all-in-one:1.50
    ports:
      - "16686:16686"  # UI
      - "4317:4317"    # OTLP gRPC
      - "4318:4318"    # OTLP HTTP
    environment:
      - COLLECTOR_OTLP_ENABLED=true
```

## SLA Monitoring

### SLI/SLO Dashboard

```promql
# Availability SLI (non-5xx responses)
sum(rate(zentinel_requests_total{status!~"5.."}[5m]))
/ sum(rate(zentinel_requests_total[5m]))

# Latency SLI (requests under 200ms)
sum(rate(zentinel_request_duration_seconds_bucket{le="0.2"}[5m]))
/ sum(rate(zentinel_request_duration_seconds_count[5m]))

# Error budget remaining (99.9% SLO)
1 - (
  (1 - (sum(rate(zentinel_requests_total{status!~"5.."}[30d]))
  / sum(rate(zentinel_requests_total[30d]))))
  / (1 - 0.999)
)
```

## Next Steps

- [Rolling Updates](../rolling-updates/) - Zero-downtime updates
- [Kubernetes](../kubernetes/) - Cloud-native deployment
- [Docker Compose](../docker-compose/) - Container orchestration
