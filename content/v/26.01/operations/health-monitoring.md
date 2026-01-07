+++
title = "Health Monitoring"
weight = 2
+++

Monitoring Sentinel health, readiness, and upstream status.

## Health Endpoints

### Liveness Check

The `/health` endpoint returns 200 OK if Sentinel is running:

```bash
curl http://localhost:9090/health
```

Response:
```json
{"status": "healthy"}
```

Configure the health route:

```kdl
routes {
    route "health" {
        priority 1000
        matches {
            path "/health"
        }
        service-type "builtin"
        builtin-handler "health"
    }
}
```

### Status Endpoint

The `/status` endpoint returns detailed status:

```bash
curl http://localhost:9090/status
```

Response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "uptime_seconds": 86400,
  "start_time": "2025-01-15T00:00:00Z",
  "config_reload_count": 3,
  "last_config_reload": "2025-01-15T12:00:00Z"
}
```

### Upstream Health

Check upstream health status:

```bash
curl http://localhost:9090/admin/upstreams
```

Response:
```json
{
  "upstreams": {
    "backend": {
      "healthy": true,
      "targets": [
        {
          "address": "10.0.1.1:8080",
          "healthy": true,
          "active_connections": 45,
          "total_requests": 150000,
          "failed_requests": 12
        },
        {
          "address": "10.0.1.2:8080",
          "healthy": true,
          "active_connections": 42,
          "total_requests": 148000,
          "failed_requests": 8
        },
        {
          "address": "10.0.1.3:8080",
          "healthy": false,
          "active_connections": 0,
          "total_requests": 50000,
          "failed_requests": 150,
          "last_error": "connection refused",
          "unhealthy_since": "2025-01-15T11:30:00Z"
        }
      ]
    }
  }
}
```

## Kubernetes Probes

### Liveness Probe

Detect if Sentinel needs restart:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 9090
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

### Readiness Probe

Detect if Sentinel is ready to receive traffic:

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 9090
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 2
```

### Startup Probe

For slow-starting instances:

```yaml
startupProbe:
  httpGet:
    path: /health
    port: 9090
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 30  # 150 seconds max startup
```

### Complete Kubernetes Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sentinel
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sentinel
  template:
    metadata:
      labels:
        app: sentinel
    spec:
      containers:
        - name: sentinel
          image: sentinel:latest
          ports:
            - name: http
              containerPort: 8080
            - name: admin
              containerPort: 9090
          livenessProbe:
            httpGet:
              path: /health
              port: admin
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: admin
            initialDelaySeconds: 5
            periodSeconds: 5
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "1Gi"
              cpu: "1000m"
```

## Load Balancer Health Checks

### AWS ALB/NLB

```
Target type: instance or ip
Health check path: /health
Health check port: 9090
Healthy threshold: 2
Unhealthy threshold: 3
Timeout: 5 seconds
Interval: 10 seconds
Success codes: 200
```

### GCP Load Balancer

```yaml
healthChecks:
  - name: sentinel-health
    type: HTTP
    httpHealthCheck:
      port: 9090
      requestPath: /health
    checkIntervalSec: 10
    timeoutSec: 5
    healthyThreshold: 2
    unhealthyThreshold: 3
```

### HAProxy Backend Check

```
backend sentinel_backend
    option httpchk GET /health
    http-check expect status 200
    server sentinel1 10.0.1.1:8080 check port 9090
    server sentinel2 10.0.1.2:8080 check port 9090
```

## Upstream Health Checks

### HTTP Health Check

```kdl
upstreams {
    upstream "backend" {
        health-check {
            type "http" {
                path "/health"
                expected-status 200
                host "backend.internal"
            }
            interval-secs 10
            timeout-secs 5
            healthy-threshold 2
            unhealthy-threshold 3
        }
    }
}
```

### TCP Health Check

For non-HTTP services:

```kdl
upstreams {
    upstream "database" {
        health-check {
            type "tcp"
            interval-secs 5
            timeout-secs 2
            healthy-threshold 2
            unhealthy-threshold 3
        }
    }
}
```

### gRPC Health Check

```kdl
upstreams {
    upstream "grpc-service" {
        health-check {
            type "grpc" {
                service "grpc.health.v1.Health"
            }
            interval-secs 10
            timeout-secs 5
        }
    }
}
```

### Health Check Tuning

| Scenario | interval | timeout | healthy | unhealthy |
|----------|----------|---------|---------|-----------|
| Fast failover | 5s | 2s | 2 | 2 |
| Default | 10s | 5s | 2 | 3 |
| Stable (reduce flapping) | 30s | 10s | 3 | 5 |
| Slow backends | 30s | 15s | 2 | 3 |

## Monitoring Key Metrics

### Request Metrics

```promql
# Request rate
rate(sentinel_requests_total[5m])

# Error rate
sum(rate(sentinel_requests_total{status=~"5.."}[5m]))
  / sum(rate(sentinel_requests_total[5m]))

# P99 latency
histogram_quantile(0.99,
  rate(sentinel_request_duration_seconds_bucket[5m]))
```

### Upstream Metrics

```promql
# Upstream failure rate
sum(rate(sentinel_upstream_failures_total[5m])) by (upstream)
  / sum(rate(sentinel_upstream_attempts_total[5m])) by (upstream)

# Circuit breaker status (1 = open)
sentinel_circuit_breaker_state{component="upstream"}

# Connection pool utilization
(sentinel_connection_pool_size - sentinel_connection_pool_idle)
  / sentinel_connection_pool_size
```

### System Metrics

```promql
# Memory usage
sentinel_memory_usage_bytes

# Active connections
sentinel_open_connections

# Active requests
sentinel_active_requests
```

## Alerting

### Critical Alerts

```yaml
groups:
  - name: sentinel-critical
    rules:
      # High error rate
      - alert: SentinelHighErrorRate
        expr: |
          sum(rate(sentinel_requests_total{status=~"5.."}[5m]))
          / sum(rate(sentinel_requests_total[5m])) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Sentinel error rate above 5%"

      # All upstreams unhealthy
      - alert: SentinelNoHealthyUpstreams
        expr: |
          sum(sentinel_circuit_breaker_state{component="upstream"})
          == count(sentinel_circuit_breaker_state{component="upstream"})
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "No healthy upstream servers"

      # Sentinel down
      - alert: SentinelDown
        expr: up{job="sentinel"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Sentinel instance down"
```

### Warning Alerts

```yaml
groups:
  - name: sentinel-warning
    rules:
      # High latency
      - alert: SentinelHighLatency
        expr: |
          histogram_quantile(0.99,
            rate(sentinel_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P99 latency above 1 second"

      # Circuit breaker open
      - alert: SentinelCircuitBreakerOpen
        expr: sentinel_circuit_breaker_state == 1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Circuit breaker open for {{ $labels.component }}"

      # High memory usage
      - alert: SentinelHighMemory
        expr: |
          sentinel_memory_usage_bytes
          / on() node_memory_MemTotal_bytes > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Memory usage above 80%"
```

## Dashboards

### Key Panels

1. **Traffic Overview**
   - Request rate (RPS)
   - Error rate (%)
   - Active requests

2. **Latency**
   - P50, P95, P99 latency
   - Latency by route

3. **Upstream Health**
   - Upstream status (healthy/unhealthy)
   - Connection pool utilization
   - Circuit breaker states

4. **System Resources**
   - Memory usage
   - CPU usage
   - Open connections

### Grafana Variables

```
# Datasource
datasource: prometheus

# Variables
- name: instance
  query: label_values(sentinel_requests_total, instance)

- name: route
  query: label_values(sentinel_requests_total, route)

- name: upstream
  query: label_values(sentinel_upstream_attempts_total, upstream)
```

## External Health Monitoring

### Synthetic Monitoring

Use external monitors to verify end-to-end health:

```bash
# Simple availability check
curl -sf https://api.example.com/health || alert

# Response time check
response_time=$(curl -sf -w "%{time_total}" -o /dev/null https://api.example.com/health)
if (( $(echo "$response_time > 1.0" | bc -l) )); then
  alert "Slow response: ${response_time}s"
fi
```

### Recommended Tools

- **Uptime monitoring:** Pingdom, UptimeRobot, Datadog Synthetics
- **APM:** Datadog, New Relic, Dynatrace
- **Logs:** Elasticsearch/Kibana, Loki/Grafana, Splunk

## See Also

- [Troubleshooting](../troubleshooting/) - Diagnosing issues
- [Metrics Reference](../../reference/metrics/) - All available metrics
- [Deployment](../../deployment/) - Production deployment guides
