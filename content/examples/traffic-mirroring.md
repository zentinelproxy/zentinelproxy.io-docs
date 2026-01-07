+++
title = "Traffic Mirroring"
weight = 80
+++

This guide demonstrates how to use Sentinel's traffic mirroring (shadow traffic) feature for safe canary deployments and testing.

## Overview

Traffic mirroring duplicates live requests to a shadow upstream for testing purposes, while clients receive responses from the primary upstream. This enables:

- **Safe canary deployments** - Test new versions with real traffic without user impact
- **Performance testing** - Validate new infrastructure under production load
- **Debug/replay** - Capture and test specific request patterns
- **Data collection** - Gather metrics from shadow deployments

## Architecture

```
┌─────────┐
│ Client  │
└────┬────┘
     │ Request
     ▼
┌────────────────┐
│   Sentinel     │
└────┬───────┬───┘
     │       │
     │       └─────► Shadow Request (async, fire-and-forget)
     │                     │
     │                     ▼
     │              ┌──────────────┐
     │              │    Canary    │
     │              │  Upstream    │
     │              └──────────────┘
     │
     │ Primary Request
     ▼
┌──────────────┐
│ Production   │
│  Upstream    │
└──────────────┘
     │
     │ Response
     ▼
┌─────────┐
│ Client  │
└─────────┘
```

**Key points:**
- Shadow requests are fire-and-forget (non-blocking)
- Client receives response only from primary upstream
- Shadow failures don't affect client response
- Zero latency impact on primary request

## Quick Start

### 1. Create Configuration

Create `shadow-test.kdl`:

```kdl
schema-version "1.0"

system {
    worker-threads 2
    max-connections 1000
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

upstreams {
    upstream "production" {
        target "127.0.0.1:9001" weight=100
        health-check {
            path "/health"
            interval-secs 10
        }
    }

    upstream "canary" {
        target "127.0.0.1:9002" weight=100
        health-check {
            path "/health"
            interval-secs 10
        }
    }
}

routes {
    route "api" {
        matches {
            path-prefix "/api/"
        }
        upstream "production"

        // Mirror 100% of traffic to canary
        shadow {
            upstream "canary"
            percentage 100.0
            timeout-ms 5000
        }
    }
}
```

### 2. Start Upstreams

For testing, you can use simple HTTP servers or Docker containers:

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  production:
    image: nginx:alpine
    ports:
      - "9001:80"
    volumes:
      - ./nginx-production.conf:/etc/nginx/conf.d/default.conf

  canary:
    image: nginx:alpine
    ports:
      - "9002:80"
    volumes:
      - ./nginx-canary.conf:/etc/nginx/conf.d/default.conf
```

**nginx-production.conf:**
```nginx
system {
    listen 80;
    location /health {
        return 200 '{"status":"healthy","upstream":"production"}\n';
        add_header Content-Type application/json;
    }
    location /api/ {
        return 200 '{"message":"Production upstream","path":"$request_uri"}\n';
        add_header Content-Type application/json;
        add_header X-Upstream-Name production;
    }
}
```

**nginx-canary.conf:**
```nginx
system {
    listen 80;
    location /health {
        return 200 '{"status":"healthy","upstream":"canary"}\n';
        add_header Content-Type application/json;
    }
    location /api/ {
        return 200 '{"message":"Canary upstream (v2.0)","path":"$request_uri"}\n';
        add_header Content-Type application/json;
        add_header X-Upstream-Name canary;
        add_header X-Version v2.0;
    }
}
```

### 3. Start Services

```bash
# Start upstreams
docker compose up -d

# Start Sentinel
sentinel -c shadow-test.kdl
```

### 4. Test Traffic Mirroring

```bash
# Make a request
curl http://localhost:8080/api/users

# Response from production:
# {"message":"Production upstream","path":"/api/users"}

# The same request was also sent to canary (asynchronously)
# but the canary response was not returned to the client
```

### 5. Monitor Metrics

```bash
# Check shadow metrics
curl http://localhost:9090/metrics | grep shadow_

# Example output:
# shadow_requests_total{route="api",upstream="canary",result="success"} 1
# shadow_latency_seconds_bucket{route="api",upstream="canary",le="0.1"} 1
```

## Configuration Patterns

### Pattern 1: Full Shadow (100% Mirrored)

Use for initial canary testing with comprehensive coverage:

```kdl
route "api-full" {
    matches {
        path-prefix "/api/v1"
    }
    upstream "production"

    shadow {
        upstream "canary"
        percentage 100.0
        timeout-ms 5000
    }
}
```

**When to use:**
- Initial canary deployment
- Validating stability before production rollout
- Short-term testing with small traffic volumes

### Pattern 2: Partial Shadow (Sampled)

Use for gradual rollout with lower shadow load:

```kdl
route "api-sampled" {
    matches {
        path-prefix "/api/v2"
    }
    upstream "production"

    shadow {
        upstream "canary"
        percentage 10.0  // Mirror 10% of requests
        timeout-ms 5000
    }
}
```

**When to use:**
- High-traffic APIs where 100% would overload shadow
- Long-running canary deployments
- Representative sampling for metrics collection

### Pattern 3: Header-Based Shadow

Use for targeted testing with specific requests:

```kdl
route "api-debug" {
    matches {
        path-prefix "/api/v3"
    }
    upstream "production"

    shadow {
        upstream "canary"
        percentage 100.0
        sample-header "X-Debug-Shadow" "true"
        timeout-ms 5000
    }
}
```

**When to use:**
- Developer/QA testing
- Beta user testing
- Debugging specific user flows
- Testing with internal traffic only

**Example usage:**
```bash
# Without header - NOT mirrored
curl http://localhost:8080/api/v3/users

# With header - mirrored to canary
curl -H "X-Debug-Shadow: true" http://localhost:8080/api/v3/users
```

### Pattern 4: Multi-Environment Shadow

Shadow to staging for internal testing:

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

upstreams {
    upstream "production" { /* ... */ }
    upstream "canary" { /* ... */ }
    upstream "staging" { /* ... */ }
}

routes {
    // External traffic: production → canary (10% sample)
    route "public-api" {
        matches {
            path-prefix "/api/"
            header name="X-Internal-Test" invert=#true
        }
        upstream "production"

        shadow {
            upstream "canary"
            percentage 10.0
        }
    }

    // Internal traffic: production → staging (100%)
    route "internal-api" {
        matches {
            path-prefix "/api/"
            header name="X-Internal-Test" value="enabled"
        }
        upstream "production"

        shadow {
            upstream "staging"
            percentage 100.0
            timeout-ms 3000
        }
    }
}

```

### Pattern 5: POST/PUT with Body Buffering

Mirror requests with body inspection:

```kdl
route "api-with-body" {
    matches {
        path "/api/users"
        method "POST" "PUT"
    }
    upstream "production"

    shadow {
        upstream "canary"
        percentage 100.0
        buffer-body #true
        max-body-bytes 1048576  // 1MB limit
        timeout-ms 5000
    }
}
```

⚠️ **Warning**: Body buffering increases memory usage and adds latency. Use only when necessary and enforce strict size limits.

## Monitoring and Observability

### Prometheus Metrics

Sentinel exposes the following metrics for shadow traffic:

```prometheus
# Total shadow requests (labels: route, upstream, result)
shadow_requests_total{route="api",upstream="canary",result="success"} 1234
shadow_requests_total{route="api",upstream="canary",result="error"} 5

# Shadow errors by type (labels: route, upstream, error_type)
shadow_errors_total{route="api",upstream="canary",error_type="timeout"} 3
shadow_errors_total{route="api",upstream="canary",error_type="connect_failed"} 2

# Shadow latency histogram (labels: route, upstream)
shadow_latency_seconds_bucket{route="api",upstream="canary",le="0.05"} 800
shadow_latency_seconds_bucket{route="api",upstream="canary",le="0.1"} 980
shadow_latency_seconds_bucket{route="api",upstream="canary",le="0.5"} 1200
shadow_latency_seconds_bucket{route="api",upstream="canary",le="1.0"} 1230
shadow_latency_seconds_sum{route="api",upstream="canary"} 98.5
shadow_latency_seconds_count{route="api",upstream="canary"} 1234
```

### Example Queries

**Shadow error rate:**
```promql
rate(shadow_errors_total[5m]) / rate(shadow_requests_total[5m])
```

**Shadow success rate:**
```promql
rate(shadow_requests_total{result="success"}[5m]) / rate(shadow_requests_total[5m])
```

**Shadow p99 latency:**
```promql
histogram_quantile(0.99, rate(shadow_latency_seconds_bucket[5m]))
```

### Alerting

Set up alerts for shadow failures:

```yaml
# shadow-alerts.yml
groups:
  - name: shadow_traffic
    rules:
      - alert: HighShadowErrorRate
        expr: |
          rate(shadow_errors_total[5m]) / rate(shadow_requests_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High shadow error rate ({{ $value }}%)"
          description: "Shadow upstream {{ $labels.upstream }} has >10% error rate"

      - alert: ShadowTimeoutRate
        expr: |
          rate(shadow_errors_total{error_type="timeout"}[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Shadow timeouts detected"
          description: "Shadow upstream {{ $labels.upstream }} experiencing timeouts"
```

## Testing Scenarios

### Scenario 1: Canary Deployment Validation

**Goal**: Validate a new service version before promoting to production.

**Setup:**
```kdl
route "api" {
    upstream "production"  // v1.0

    shadow {
        upstream "canary"  // v2.0
        percentage 100.0
    }
}
```

**Test plan:**
1. Deploy canary v2.0
2. Enable shadow at 10%
3. Monitor canary metrics (errors, latency, logs)
4. Gradually increase to 50%, then 100%
5. Compare canary vs production metrics
6. If stable, promote canary to production

### Scenario 2: Performance Testing

**Goal**: Validate infrastructure can handle production load.

**Setup:**
```kdl
route "api" {
    upstream "current-infra"

    shadow {
        upstream "new-infra"
        percentage 100.0
    }
}
```

**Metrics to compare:**
- Request latency (p50, p95, p99)
- Error rates
- Resource usage (CPU, memory, connections)
- Database query performance

### Scenario 3: API Refactoring Validation

**Goal**: Ensure refactored API produces same responses.

**Setup:**
```kdl
route "api-v1" {
    upstream "legacy-api"

    shadow {
        upstream "refactored-api"
        percentage 100.0
        buffer-body #true
        max-body-bytes 1048576
    }
}
```

**Validation approach:**
1. Enable shadow to refactored API
2. Log responses from both upstreams
3. Compare response bodies for discrepancies
4. Identify and fix differences
5. Switch traffic to refactored API when validated

## Best Practices

### 1. Start Small

Begin with low sampling percentages:

```kdl
shadow {
    upstream "canary"
    percentage 1.0  // Start with 1%
}
```

Gradually increase after validating stability.

### 2. Configure Appropriate Timeouts

Shadow timeouts should be **shorter** than primary timeouts:

```kdl
route "api" {
    policies {
        timeout-secs 30  // Primary timeout
    }

    shadow {
        upstream "canary"
        timeout-ms 20000  // 20s shadow timeout (shorter)
    }
}
```

### 3. Monitor Shadow Health

Don't deploy blindly - monitor shadow metrics:

```bash
# Check shadow success rate
curl -s http://localhost:9090/metrics | grep 'shadow_requests_total{result="success"}'

# Check shadow error rate
curl -s http://localhost:9090/metrics | grep 'shadow_errors_total'
```

### 4. Use Header-Based Filtering

For controlled testing:

```kdl
shadow {
    upstream "canary"
    sample-header "X-User-Tier" "beta"  // Only beta users
}
```

### 5. Body Buffering Hygiene

Only buffer when necessary:

```kdl
shadow {
    upstream "canary"
    buffer-body #true
    max-body-bytes 524288  // 512KB limit (strict)
}
```

Avoid buffering for:
- File uploads
- Streaming APIs
- High-throughput endpoints

### 6. Security and Compliance

For sensitive data:

```kdl
// Exclude PII-heavy endpoints
route "user-data" {
    matches {
        path-prefix "/api/users/"
    }
    upstream "production"
    // NO shadow block - don't mirror PII
}

// Mirror only non-sensitive endpoints
route "public-data" {
    matches {
        path-prefix "/api/public/"
    }
    upstream "production"

    shadow {
        upstream "canary"
        percentage 10.0
    }
}
```

## Troubleshooting

### Shadow Requests Not Sent

**Check:**
1. Shadow upstream health: `curl http://localhost:9090/metrics | grep upstream_health`
2. Sampling percentage: Ensure > 0
3. Header conditions: Verify `sample-header` matches requests
4. Metrics: `shadow_requests_total` should be incrementing

### High Shadow Error Rate

**Check:**
1. Shadow upstream logs for errors
2. Network connectivity: Can Sentinel reach shadow upstream?
3. Timeout settings: Are shadow timeouts too short?
4. Resource limits: Is shadow upstream under-provisioned?

### Memory Issues

**Check:**
1. Body buffering: Is `buffer-body` enabled unnecessarily?
2. `max-body-bytes`: Reduce limit
3. Sampling: Reduce `percentage` to lower load

## Complete Example

Full configuration with production best practices:

```kdl
schema-version "1.0"

system {
    worker-threads 4
    max-connections 10000
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
        request-timeout-secs 60
    }
}

upstreams {
    upstream "production" {
        target "prod-api-1.internal:8000" weight=100
        target "prod-api-2.internal:8000" weight=100
        load-balancing "round-robin"
        health-check {
            path "/health"
            interval-secs 10
            timeout-secs 2
            healthy-threshold 2
            unhealthy-threshold 3
        }
    }

    upstream "canary" {
        target "canary-api-1.internal:8000" weight=100
        health-check {
            path "/health"
            interval-secs 10
            timeout-secs 2
        }
    }
}

routes {
    // Health check (no shadow)
    route "health" {
        priority 1000
        matches {
            path "/health"
        }
        service-type "builtin"
        builtin-handler "health"
    }

    // API v2 with gradual canary rollout
    route "api-v2" {
        priority 200
        matches {
            path-prefix "/api/v2/"
            method "GET" "POST" "PUT" "DELETE"
        }
        upstream "production"

        // Shadow 10% to canary
        shadow {
            upstream "canary"
            percentage 10.0
            timeout-ms 25000
            buffer-body #false
        }

        filters "auth" "rate-limit"

        retry-policy {
            max-attempts 3
            retryable-status-codes 502 503 504
        }

        policies {
            timeout-secs 30
            max-body-size "10MB"
        }
    }

    // Beta users - 100% shadow
    route "api-beta" {
        priority 250
        matches {
            path-prefix "/api/v2/"
            header name="X-User-Tier" value="beta"
        }
        upstream "production"

        shadow {
            upstream "canary"
            percentage 100.0
            sample-header "X-Enable-Shadow" "true"
            timeout-ms 25000
        }
    }
}

observability {
    metrics {
        enabled #true
        port 9090
    }

    logging {
        level "info"
        format "json"
    }
}
```

## Next Steps

- [Routes Configuration](../../configuration/routes/) - Detailed route configuration reference
- [Upstreams Configuration](../../configuration/upstreams/) - Upstream pools and health checks
- [Observability](../../configuration/observability/) - Metrics and logging setup
- [Prometheus Example](../prometheus/) - Metrics collection and visualization
