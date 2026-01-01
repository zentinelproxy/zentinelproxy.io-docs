+++
title = "Observability"
weight = 8
+++

Sentinel provides comprehensive observability through metrics, logging, and distributed tracing. All observability features are configured in the `observability` block.

## Basic Configuration

```kdl
observability {
    logging {
        level "info"
        format "json"

        access-log {
            enabled #true
            file "/var/log/sentinel/access.log"
            format "json"
        }

        error-log {
            enabled #true
            file "/var/log/sentinel/error.log"
            level "warn"
        }

        audit-log {
            enabled #true
            file "/var/log/sentinel/audit.log"
            log-blocked #true
            log-agent-decisions #true
            log-waf-events #true
        }
    }

    metrics {
        enabled #true
        address "0.0.0.0:9090"
        path "/metrics"
    }

    tracing {
        backend "otlp" {
            endpoint "http://jaeger:4317"
        }
        sampling-rate 0.01
        service-name "sentinel"
    }
}
```

## Logging

### Application Logging

Configure the main application log output:

```kdl
observability {
    logging {
        level "info"           // Log level
        format "json"          // Log format
        timestamps #true       // Include timestamps
        file "/var/log/sentinel/app.log"  // Optional file path
    }
}
```

#### Log Levels

| Level | Description |
|-------|-------------|
| `trace` | Very detailed debugging |
| `debug` | Debugging information |
| `info` | Informational messages (default) |
| `warn` | Warnings |
| `error` | Errors only |

#### Log Formats

| Format | Description |
|--------|-------------|
| `json` | Structured JSON (default, recommended for production) |
| `pretty` | Human-readable format |

### Access Log

HTTP request/response logging:

```kdl
observability {
    logging {
        access-log {
            enabled #true
            file "/var/log/sentinel/access.log"
            format "json"
            buffer-size 8192
            include-trace-id #true
        }
    }
}
```

#### Access Log Options

| Option | Default | Description |
|--------|---------|-------------|
| `enabled` | `true` | Enable access logging |
| `file` | `/var/log/sentinel/access.log` | Log file path |
| `format` | `json` | Log format (`json`, `combined`, `custom`) |
| `buffer-size` | `8192` | Write buffer size |
| `include-trace-id` | `true` | Include trace ID in logs |

#### Access Log Fields (JSON format)

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "trace_id": "2Kj8mNpQ3xR",
  "method": "GET",
  "path": "/api/v1/users",
  "status": 200,
  "duration_ms": 45,
  "bytes_sent": 1234,
  "client_ip": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "upstream": "api-backend",
  "upstream_addr": "10.0.1.5:8080",
  "upstream_duration_ms": 42,
  "cache_status": "HIT",
  "route_id": "api-users"
}
```

### Error Log

Error and warning logging:

```kdl
observability {
    logging {
        error-log {
            enabled #true
            file "/var/log/sentinel/error.log"
            level "warn"
            buffer-size 8192
        }
    }
}
```

#### Error Log Options

| Option | Default | Description |
|--------|---------|-------------|
| `enabled` | `true` | Enable error logging |
| `file` | `/var/log/sentinel/error.log` | Log file path |
| `level` | `warn` | Minimum level to log |
| `buffer-size` | `8192` | Write buffer size |

### Audit Log

Security-focused logging for compliance and forensics:

```kdl
observability {
    logging {
        audit-log {
            enabled #true
            file "/var/log/sentinel/audit.log"
            buffer-size 8192
            log-blocked #true
            log-agent-decisions #true
            log-waf-events #true
        }
    }
}
```

#### Audit Log Options

| Option | Default | Description |
|--------|---------|-------------|
| `enabled` | `true` | Enable audit logging |
| `file` | `/var/log/sentinel/audit.log` | Log file path |
| `buffer-size` | `8192` | Write buffer size |
| `log-blocked` | `true` | Log blocked requests |
| `log-agent-decisions` | `true` | Log agent allow/deny decisions |
| `log-waf-events` | `true` | Log WAF rule matches |

#### Audit Log Events

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "event_type": "request_blocked",
  "trace_id": "2Kj8mNpQ3xR",
  "client_ip": "192.168.1.100",
  "method": "POST",
  "path": "/api/v1/admin",
  "reason": "rate_limit_exceeded",
  "rule_id": "rate-limit-api",
  "action": "block",
  "metadata": {
    "limit": 100,
    "current": 101
  }
}
```

## Metrics

Prometheus-compatible metrics endpoint:

```kdl
observability {
    metrics {
        enabled #true
        address "0.0.0.0:9090"
        path "/metrics"
        high-cardinality #false
    }
}
```

### Metrics Options

| Option | Default | Description |
|--------|---------|-------------|
| `enabled` | `true` | Enable metrics endpoint |
| `address` | `0.0.0.0:9090` | Metrics server address |
| `path` | `/metrics` | Metrics endpoint path |
| `high-cardinality` | `false` | Include high-cardinality labels |

### Available Metrics

#### Request Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `sentinel_requests_total` | Counter | Total requests by route, method, status |
| `sentinel_request_duration_seconds` | Histogram | Request latency distribution |
| `sentinel_request_size_bytes` | Histogram | Request body size |
| `sentinel_response_size_bytes` | Histogram | Response body size |
| `sentinel_active_requests` | Gauge | Currently active requests |

#### Upstream Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `sentinel_upstream_requests_total` | Counter | Requests to upstreams |
| `sentinel_upstream_duration_seconds` | Histogram | Upstream latency |
| `sentinel_upstream_healthy_backends` | Gauge | Healthy backends per upstream |
| `sentinel_upstream_connections` | Gauge | Active upstream connections |
| `sentinel_upstream_retries_total` | Counter | Retry attempts |

#### Cache Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `sentinel_cache_hits_total` | Counter | Cache hits |
| `sentinel_cache_misses_total` | Counter | Cache misses |
| `sentinel_cache_size_bytes` | Gauge | Current cache size |
| `sentinel_cache_entries` | Gauge | Number of cached entries |
| `sentinel_cache_evictions_total` | Counter | Cache evictions |

#### Rate Limiting Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `sentinel_rate_limit_hits_total` | Counter | Rate limit triggers |
| `sentinel_rate_limit_allowed_total` | Counter | Allowed requests |
| `sentinel_rate_limit_delayed_total` | Counter | Delayed requests |

#### Agent Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `sentinel_agent_requests_total` | Counter | Agent call count |
| `sentinel_agent_duration_seconds` | Histogram | Agent call latency |
| `sentinel_agent_errors_total` | Counter | Agent errors |
| `sentinel_agent_timeouts_total` | Counter | Agent timeouts |
| `sentinel_agent_circuit_breaker_state` | Gauge | Circuit breaker state (0=closed, 1=open, 2=half-open) |

#### Connection Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `sentinel_connections_total` | Counter | Total connections |
| `sentinel_active_connections` | Gauge | Current connections |
| `sentinel_connection_duration_seconds` | Histogram | Connection lifetime |
| `sentinel_tls_handshake_duration_seconds` | Histogram | TLS handshake time |

### Prometheus Scrape Config

```yaml
scrape_configs:
  - job_name: 'sentinel'
    static_configs:
      - targets: ['sentinel:9090']
    scrape_interval: 15s
    metrics_path: /metrics
```

## Distributed Tracing

OpenTelemetry-compatible distributed tracing:

```kdl
observability {
    tracing {
        backend "otlp" {
            endpoint "http://jaeger:4317"
        }
        sampling-rate 0.01     // 1% of requests
        service-name "sentinel"
    }
}
```

### Tracing Backends

#### OTLP (OpenTelemetry Protocol)

```kdl
tracing {
    backend "otlp" {
        endpoint "http://otel-collector:4317"
    }
}
```

#### Jaeger

```kdl
tracing {
    backend "jaeger" {
        endpoint "http://jaeger:14268/api/traces"
    }
}
```

#### Zipkin

```kdl
tracing {
    backend "zipkin" {
        endpoint "http://zipkin:9411/api/v2/spans"
    }
}
```

### Tracing Options

| Option | Default | Description |
|--------|---------|-------------|
| `sampling-rate` | `0.01` | Fraction of requests to trace (0.0-1.0) |
| `service-name` | `sentinel` | Service name in traces |

### Trace Context

Sentinel propagates W3C Trace Context headers:

| Header | Description |
|--------|-------------|
| `traceparent` | W3C trace context parent |
| `tracestate` | W3C trace context state |
| `X-Request-ID` | Sentinel's trace ID |

### Span Attributes

Each request span includes:

| Attribute | Description |
|-----------|-------------|
| `http.method` | HTTP method |
| `http.url` | Request URL |
| `http.status_code` | Response status |
| `http.route` | Route ID |
| `sentinel.upstream` | Upstream name |
| `sentinel.cache_status` | Cache hit/miss |

## Trace ID Format

Configure the format for request trace IDs:

```kdl
server {
    trace-id-format "tinyflake"   // or "uuid"
}
```

| Format | Example | Description |
|--------|---------|-------------|
| `tinyflake` | `2Kj8mNpQ3xR` | 11-char Base58, operator-friendly (default) |
| `uuid` | `550e8400-e29b-41d4-a716-446655440000` | 36-char UUID v4 |

## Complete Example

```kdl
server {
    worker-threads 0
    trace-id-format "tinyflake"
}

observability {
    logging {
        level "info"
        format "json"

        access-log {
            enabled #true
            file "/var/log/sentinel/access.log"
            format "json"
            include-trace-id #true
        }

        error-log {
            enabled #true
            file "/var/log/sentinel/error.log"
            level "warn"
        }

        audit-log {
            enabled #true
            file "/var/log/sentinel/audit.log"
            log-blocked #true
            log-agent-decisions #true
        }
    }

    metrics {
        enabled #true
        address "0.0.0.0:9090"
        path "/metrics"
    }

    tracing {
        backend "otlp" {
            endpoint "http://otel-collector:4317"
        }
        sampling-rate 0.05
        service-name "sentinel-prod"
    }
}
```

## Log Rotation

Sentinel logs are designed for external rotation. Use logrotate or similar:

```
/var/log/sentinel/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

## Best Practices

1. **Use JSON logging in production**: Enables log aggregation and analysis
2. **Set appropriate log levels**: `info` for production, `debug` for troubleshooting
3. **Enable audit logging**: Required for security compliance
4. **Configure sampling for tracing**: 1-5% is typical for production
5. **Use separate log files**: Easier rotation and analysis
6. **Monitor metrics endpoints**: Set up alerting on error rates and latencies

## Next Steps

- [Operations](../../operations/) - Operational procedures
- [Monitoring](../../deployment/monitoring/) - Monitoring setup
- [Troubleshooting](../../operations/troubleshooting/) - Debug procedures
