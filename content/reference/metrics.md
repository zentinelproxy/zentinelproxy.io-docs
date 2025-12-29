+++
title = "Metrics Reference"
weight = 4
+++

Prometheus metrics exposed by Sentinel for monitoring and alerting.

## Metrics Endpoint

Metrics are available at the `/metrics` endpoint on the admin listener:

```bash
curl http://localhost:9090/metrics
```

Configure the admin listener:

```kdl
listeners {
    listener "admin" {
        address "127.0.0.1:9090"
        protocol "http"
    }
}

routes {
    route "metrics" {
        matches {
            path "/metrics"
        }
        service-type "builtin"
        builtin-handler "metrics"
    }
}
```

## Request Metrics

### sentinel_request_duration_seconds

Request latency histogram.

| Type | Labels | Description |
|------|--------|-------------|
| Histogram | `route`, `method` | Request duration in seconds |

**Buckets:** 1ms, 5ms, 10ms, 25ms, 50ms, 100ms, 250ms, 500ms, 1s, 2.5s, 5s, 10s

**Example queries:**
```promql
# Average latency by route
rate(sentinel_request_duration_seconds_sum[5m])
  / rate(sentinel_request_duration_seconds_count[5m])

# P99 latency
histogram_quantile(0.99,
  rate(sentinel_request_duration_seconds_bucket[5m]))

# P95 latency by route
histogram_quantile(0.95,
  sum(rate(sentinel_request_duration_seconds_bucket[5m])) by (le, route))
```

### sentinel_requests_total

Total request counter.

| Type | Labels | Description |
|------|--------|-------------|
| Counter | `route`, `method`, `status` | Total requests |

**Example queries:**
```promql
# Requests per second
rate(sentinel_requests_total[5m])

# Error rate (5xx)
sum(rate(sentinel_requests_total{status=~"5.."}[5m]))
  / sum(rate(sentinel_requests_total[5m]))

# Success rate by route
sum(rate(sentinel_requests_total{status="200"}[5m])) by (route)
  / sum(rate(sentinel_requests_total[5m])) by (route)
```

### sentinel_active_requests

Currently active requests.

| Type | Labels | Description |
|------|--------|-------------|
| Gauge | - | Number of in-flight requests |

**Example queries:**
```promql
# Current active requests
sentinel_active_requests

# Alert if too high
sentinel_active_requests > 1000
```

### sentinel_request_body_size_bytes

Request body size histogram.

| Type | Labels | Description |
|------|--------|-------------|
| Histogram | `route` | Request body size in bytes |

**Buckets:** 100B, 1KB, 10KB, 100KB, 1MB, 10MB, 100MB

### sentinel_response_body_size_bytes

Response body size histogram.

| Type | Labels | Description |
|------|--------|-------------|
| Histogram | `route` | Response body size in bytes |

## Upstream Metrics

### sentinel_upstream_attempts_total

Upstream connection attempts.

| Type | Labels | Description |
|------|--------|-------------|
| Counter | `upstream`, `route` | Total connection attempts |

### sentinel_upstream_failures_total

Upstream connection failures.

| Type | Labels | Description |
|------|--------|-------------|
| Counter | `upstream`, `route`, `reason` | Total failures |

**Reason values:**
- `connection_refused` - TCP connection refused
- `connection_timeout` - Connection timed out
- `read_timeout` - Read timeout
- `write_timeout` - Write timeout
- `tls_error` - TLS handshake failed
- `dns_error` - DNS resolution failed

**Example queries:**
```promql
# Failure rate by upstream
sum(rate(sentinel_upstream_failures_total[5m])) by (upstream)
  / sum(rate(sentinel_upstream_attempts_total[5m])) by (upstream)

# Connection refused errors
sum(rate(sentinel_upstream_failures_total{reason="connection_refused"}[5m])) by (upstream)
```

### sentinel_circuit_breaker_state

Circuit breaker state.

| Type | Labels | Description |
|------|--------|-------------|
| Gauge | `component`, `route` | State: 0=closed, 1=open |

**Example queries:**
```promql
# Open circuit breakers
sentinel_circuit_breaker_state == 1

# Alert on circuit breaker open
sentinel_circuit_breaker_state{component="upstream"} == 1
```

## Agent Metrics

### sentinel_agent_latency_seconds

Agent call latency histogram.

| Type | Labels | Description |
|------|--------|-------------|
| Histogram | `agent`, `event` | Agent call duration |

**Event values:**
- `on_request_headers`
- `on_request_body`
- `on_response_headers`
- `on_response_body`

**Example queries:**
```promql
# P99 agent latency
histogram_quantile(0.99,
  rate(sentinel_agent_latency_seconds_bucket[5m]))

# Average latency by agent
rate(sentinel_agent_latency_seconds_sum[5m])
  / rate(sentinel_agent_latency_seconds_count[5m])
```

### sentinel_agent_timeouts_total

Agent call timeouts.

| Type | Labels | Description |
|------|--------|-------------|
| Counter | `agent`, `event` | Total timeouts |

**Example queries:**
```promql
# Timeout rate by agent
rate(sentinel_agent_timeouts_total[5m])

# Alert on high timeout rate
rate(sentinel_agent_timeouts_total[5m]) > 0.1
```

### sentinel_blocked_requests_total

Requests blocked by agents/WAF.

| Type | Labels | Description |
|------|--------|-------------|
| Counter | `reason` | Total blocked requests |

**Reason values:**
- `waf` - Blocked by WAF
- `auth` - Authentication failed
- `rate_limit` - Rate limited
- `policy` - Policy violation

## Connection Pool Metrics

### sentinel_connection_pool_size

Total connections in pool.

| Type | Labels | Description |
|------|--------|-------------|
| Gauge | `upstream` | Total connections |

### sentinel_connection_pool_idle

Idle connections in pool.

| Type | Labels | Description |
|------|--------|-------------|
| Gauge | `upstream` | Idle connections |

### sentinel_connection_pool_acquired_total

Connections acquired from pool.

| Type | Labels | Description |
|------|--------|-------------|
| Counter | `upstream` | Total acquisitions |

**Example queries:**
```promql
# Pool utilization
(sentinel_connection_pool_size - sentinel_connection_pool_idle)
  / sentinel_connection_pool_size

# Connection acquisition rate
rate(sentinel_connection_pool_acquired_total[5m])
```

## TLS Metrics

### sentinel_tls_handshake_duration_seconds

TLS handshake duration.

| Type | Labels | Description |
|------|--------|-------------|
| Histogram | `version` | Handshake duration |

**Version values:** `TLS1.2`, `TLS1.3`

## System Metrics

### sentinel_memory_usage_bytes

Process memory usage.

| Type | Labels | Description |
|------|--------|-------------|
| Gauge | - | Memory usage in bytes |

### sentinel_cpu_usage_percent

CPU usage percentage.

| Type | Labels | Description |
|------|--------|-------------|
| Gauge | - | CPU usage 0-100 |

### sentinel_open_connections

Open connections count.

| Type | Labels | Description |
|------|--------|-------------|
| Gauge | - | Number of open connections |

## Prometheus Configuration

### Basic Scrape Config

```yaml
scrape_configs:
  - job_name: 'sentinel'
    static_configs:
      - targets: ['localhost:9090']
    scrape_interval: 15s
    metrics_path: /metrics
```

### With Service Discovery

```yaml
scrape_configs:
  - job_name: 'sentinel'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        regex: sentinel
        action: keep
      - source_labels: [__meta_kubernetes_pod_container_port_name]
        regex: metrics
        action: keep
```

## Alerting Rules

### Example Alerts

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

      # Circuit breaker open
      - alert: SentinelCircuitBreakerOpen
        expr: sentinel_circuit_breaker_state == 1
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Circuit breaker open"
          description: "Circuit breaker open for {{ $labels.component }}"

      # High latency
      - alert: SentinelHighLatency
        expr: |
          histogram_quantile(0.99,
            rate(sentinel_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High P99 latency"
          description: "P99 latency is {{ $value }}s"

      # Agent timeouts
      - alert: SentinelAgentTimeouts
        expr: rate(sentinel_agent_timeouts_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Agent timeouts detected"
          description: "Agent {{ $labels.agent }} timing out"

      # No healthy upstreams
      - alert: SentinelNoHealthyUpstreams
        expr: |
          sum(sentinel_circuit_breaker_state{component="upstream"})
          == count(sentinel_circuit_breaker_state{component="upstream"})
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "No healthy upstreams"
```

## Grafana Dashboard

Key panels for a Sentinel dashboard:

1. **Request Rate** - `rate(sentinel_requests_total[5m])`
2. **Error Rate** - 5xx / total
3. **Latency P50/P95/P99** - histogram_quantile
4. **Active Requests** - `sentinel_active_requests`
5. **Upstream Health** - circuit breaker states
6. **Agent Latency** - agent_latency histogram
7. **Connection Pool** - size vs idle
8. **Memory/CPU** - system metrics

## See Also

- [Observability](../../features/observability/) - Logging and tracing
- [Error Codes](../error-codes/) - Error types and codes
