+++
title = "Monitoring Setup"
weight = 6
+++

Production monitoring and observability for Sentinel deployments.

## Metrics Endpoint

Sentinel exposes Prometheus metrics on the configured address:

```kdl
observability {
    metrics {
        enabled true
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
  # Sentinel proxy
  - job_name: 'sentinel'
    static_configs:
      - targets: ['sentinel:9090']
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        regex: '([^:]+):\d+'
        replacement: '${1}'

  # Sentinel agents
  - job_name: 'sentinel-agents'
    static_configs:
      - targets:
          - 'sentinel-waf:9091'
          - 'sentinel-auth:9092'
          - 'sentinel-ratelimit:9093'
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
  name: sentinel
  labels:
    app: sentinel
spec:
  selector:
    matchLabels:
      app: sentinel
  endpoints:
    - port: metrics
      interval: 15s
      path: /metrics
```

## Key Metrics

### Request Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `sentinel_requests_total` | Counter | Total requests by route, method, status |
| `sentinel_request_duration_seconds` | Histogram | Request latency distribution |
| `sentinel_request_size_bytes` | Histogram | Request body size |
| `sentinel_response_size_bytes` | Histogram | Response body size |

### Upstream Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `sentinel_upstream_requests_total` | Counter | Requests per upstream target |
| `sentinel_upstream_latency_seconds` | Histogram | Upstream response time |
| `sentinel_upstream_health` | Gauge | Target health (1=healthy, 0=unhealthy) |
| `sentinel_upstream_connections_active` | Gauge | Active connections per upstream |

### Agent Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `sentinel_agent_duration_seconds` | Histogram | Agent processing time |
| `sentinel_agent_errors_total` | Counter | Agent errors by type |
| `sentinel_agent_decisions_total` | Counter | Agent decisions (allow/block) |

### System Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `sentinel_connections_active` | Gauge | Active client connections |
| `sentinel_connections_total` | Counter | Total connections |
| `process_cpu_seconds_total` | Counter | CPU usage |
| `process_resident_memory_bytes` | Gauge | Memory usage |

## Essential PromQL Queries

### Request Rate

```promql
# Requests per second
rate(sentinel_requests_total[5m])

# By route
sum by (route) (rate(sentinel_requests_total[5m]))

# By status code
sum by (status) (rate(sentinel_requests_total[5m]))
```

### Error Rate

```promql
# 5xx error rate
sum(rate(sentinel_requests_total{status=~"5.."}[5m]))
/ sum(rate(sentinel_requests_total[5m])) * 100

# 4xx rate
sum(rate(sentinel_requests_total{status=~"4.."}[5m]))
/ sum(rate(sentinel_requests_total[5m])) * 100
```

### Latency

```promql
# 50th percentile
histogram_quantile(0.50, rate(sentinel_request_duration_seconds_bucket[5m]))

# 95th percentile
histogram_quantile(0.95, rate(sentinel_request_duration_seconds_bucket[5m]))

# 99th percentile
histogram_quantile(0.99, rate(sentinel_request_duration_seconds_bucket[5m]))
```

### Upstream Health

```promql
# Unhealthy upstreams
sentinel_upstream_health == 0

# Upstream latency p95
histogram_quantile(0.95, rate(sentinel_upstream_latency_seconds_bucket[5m]))
```

## Alerting Rules

### alerts.yml

```yaml
groups:
  - name: sentinel
    rules:
      # High error rate
      - alert: SentinelHighErrorRate
        expr: |
          sum(rate(sentinel_requests_total{status=~"5.."}[5m]))
          / sum(rate(sentinel_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate on Sentinel"
          description: "Error rate is {{ $value | humanizePercentage }}"

      # High latency
      - alert: SentinelHighLatency
        expr: |
          histogram_quantile(0.95, rate(sentinel_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency on Sentinel"
          description: "p95 latency is {{ $value | humanizeDuration }}"

      # Upstream down
      - alert: SentinelUpstreamDown
        expr: sentinel_upstream_health == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Upstream target is down"
          description: "{{ $labels.upstream }}/{{ $labels.target }} is unhealthy"

      # No requests
      - alert: SentinelNoTraffic
        expr: |
          sum(rate(sentinel_requests_total[5m])) == 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "No traffic to Sentinel"
          description: "Sentinel has received no requests in 5 minutes"

      # Agent errors
      - alert: SentinelAgentErrors
        expr: rate(sentinel_agent_errors_total[5m]) > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Agent errors detected"
          description: "Agent {{ $labels.agent }} has errors"

      # High memory
      - alert: SentinelHighMemory
        expr: |
          process_resident_memory_bytes / 1024 / 1024 > 1024
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Sentinel using {{ $value | humanize }}MB"
```

## Grafana Dashboards

### Dashboard JSON

```json
{
  "title": "Sentinel Overview",
  "panels": [
    {
      "title": "Request Rate",
      "type": "timeseries",
      "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
      "targets": [{
        "expr": "sum(rate(sentinel_requests_total[5m]))",
        "legendFormat": "Requests/sec"
      }]
    },
    {
      "title": "Error Rate",
      "type": "gauge",
      "gridPos": {"x": 12, "y": 0, "w": 6, "h": 8},
      "targets": [{
        "expr": "sum(rate(sentinel_requests_total{status=~\"5..\"}[5m])) / sum(rate(sentinel_requests_total[5m])) * 100"
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
      "gridPos": {"x": 12, "y": 8, "w": 6, "h": 8},
      "targets": [{
        "expr": "sentinel_upstream_health",
        "legendFormat": "{{upstream}}/{{target}}"
      }]
    }
  ]
}
```

## Health Checks

### Sentinel Health Endpoint

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
    - name: sentinel
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
observability {
    logging {
        level "info"
        format "json"
        access-log {
            enabled true
            fields ["method" "path" "status" "latency" "upstream" "client_ip"]
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
  - job_name: sentinel
    static_configs:
      - targets:
          - localhost
        labels:
          job: sentinel
          __path__: /var/log/sentinel/*.log
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
observability {
    tracing {
        enabled true
        service-name "sentinel"
        endpoint "http://jaeger:4317"
        protocol "grpc"
        sample-rate 0.1  # 10% sampling
        propagation "w3c"
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
sum(rate(sentinel_requests_total{status!~"5.."}[5m]))
/ sum(rate(sentinel_requests_total[5m]))

# Latency SLI (requests under 200ms)
sum(rate(sentinel_request_duration_seconds_bucket{le="0.2"}[5m]))
/ sum(rate(sentinel_request_duration_seconds_count[5m]))

# Error budget remaining (99.9% SLO)
1 - (
  (1 - (sum(rate(sentinel_requests_total{status!~"5.."}[30d]))
  / sum(rate(sentinel_requests_total[30d]))))
  / (1 - 0.999)
)
```

## Next Steps

- [Rolling Updates](../rolling-updates/) - Zero-downtime updates
- [Kubernetes](../kubernetes/) - Cloud-native deployment
- [Docker Compose](../docker-compose/) - Container orchestration
