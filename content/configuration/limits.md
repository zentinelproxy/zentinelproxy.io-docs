+++
title = "Limits"
weight = 6
updated = 2026-08-23
+++

The `limits` block configures request/response limits, connection limits, and rate limiting. These settings are critical for predictable behavior, resource protection, and "sleepable operations."

## Basic Configuration

```kdl
limits {
    max-header-size-bytes 8192
    max-header-count 100
    max-body-size-bytes 10485760  // 10MB
}
```

## Header Limits

```kdl
limits {
    max-header-size-bytes 8192     // Total headers size
    max-header-count 100           // Maximum header count
    max-header-name-bytes 256      // Per-header name size
    max-header-value-bytes 4096    // Per-header value size
}
```

| Setting | Default | Description |
|---------|---------|-------------|
| `max-header-size-bytes` | `8192` (8KB) | Total size of all headers |
| `max-header-count` | `100` | Maximum number of headers |
| `max-header-name-bytes` | `256` | Maximum header name length |
| `max-header-value-bytes` | `4096` (4KB) | Maximum header value length |

**Security note:** Large header limits can be exploited for denial-of-service. Keep defaults unless you have specific requirements.

### Recommended Header Limits

| Environment | header-size | header-count | header-value |
|-------------|-------------|--------------|--------------|
| Production | 4096-8192 | 50-100 | 2048-4096 |
| Development | 16384 | 200 | 8192 |
| API Gateway | 8192 | 100 | 4096 |

## Body Limits

```kdl
limits {
    max-body-size-bytes 10485760       // 10MB - maximum request body
    max-body-buffer-bytes 1048576      // 1MB - buffer for inspection
    max-body-inspection-bytes 1048576  // 1MB - bytes sent to agents
}
```

| Setting | Default | Description |
|---------|---------|-------------|
| `max-body-size-bytes` | `10485760` (10MB) | Maximum request body size |
| `max-body-buffer-bytes` | `1048576` (1MB) | Maximum buffered body size |
| `max-body-inspection-bytes` | `1048576` (1MB) | Maximum body sent to agents |

### Body Size Guidelines

| Use Case | Recommended Size |
|----------|------------------|
| API endpoints | 1-10 MB |
| File uploads | 100 MB - 1 GB |
| JSON APIs | 1-5 MB |
| Form submissions | 1-10 MB |

**Memory impact:** `max-body-buffer-bytes × max-in-flight-requests` = potential memory usage for body buffering.

### Per-Route Body Limits

Override body limits on specific routes:

```kdl
routes {
    route "upload" {
        matches {
            path-prefix "/upload/"
        }
        upstream "storage"
        policies {
            max-body-size "500MB"
        }
    }

    route "api" {
        matches {
            path-prefix "/api/"
        }
        upstream "backend"
        policies {
            max-body-size "1MB"
        }
    }
}
```

## Decompression Limits

Protect against decompression bombs:

```kdl
limits {
    max-decompression-ratio 100.0       // Max 100:1 compression ratio
    max-decompressed-size-bytes 104857600  // 100MB decompressed
}
```

| Setting | Default | Description |
|---------|---------|-------------|
| `max-decompression-ratio` | `100.0` | Maximum compression ratio allowed |
| `max-decompressed-size-bytes` | `104857600` (100MB) | Maximum decompressed size |

**Security note:** Compression bombs (zip bombs) can use 1KB of compressed data to expand to gigabytes. These limits prevent resource exhaustion.

## Connection Limits

```kdl
limits {
    max-connections-per-client 100
    max-connections-per-route 1000
    max-total-connections 10000
    max-idle-connections-per-upstream 100
}
```

| Setting | Default | Description |
|---------|---------|-------------|
| `max-connections-per-client` | `100` | Per-client connection limit |
| `max-connections-per-route` | `1000` | Per-route connection limit |
| `max-total-connections` | `10000` | Global connection limit |
| `max-idle-connections-per-upstream` | `100` | Idle connections per upstream |

### Connection Limit Sizing

| Deployment | per-client | per-route | total |
|------------|------------|-----------|-------|
| Small | 50 | 500 | 5000 |
| Medium | 100 | 1000 | 10000 |
| Large | 200 | 2000 | 50000 |
| API Gateway | 100 | 5000 | 100000 |

**Formula:** `max-total-connections` should be less than or equal to OS file descriptor limit minus a safety margin.

Check your limits:
```bash
ulimit -n  # Current soft limit
cat /proc/sys/fs/file-max  # System limit
```

## Request Limits

```kdl
limits {
    max-in-flight-requests 10000
    max-in-flight-requests-per-worker 1000
    max-queued-requests 1000
}
```

| Setting | Default | Description |
|---------|---------|-------------|
| `max-in-flight-requests` | `10000` | Total concurrent requests |
| `max-in-flight-requests-per-worker` | `1000` | Per-worker concurrent requests |
| `max-queued-requests` | `1000` | Pending requests in queue |

When limits are reached:
- New requests receive `503 Service Unavailable`
- `Retry-After` header indicates when to retry

## Agent Limits

```kdl
limits {
    max-agent-queue-depth 100
    max-agent-body-bytes 1048576     // 1MB to agents
    max-agent-response-bytes 10240   // 10KB from agents
}
```

| Setting | Default | Description |
|---------|---------|-------------|
| `max-agent-queue-depth` | `100` | Pending requests per agent |
| `max-agent-body-bytes` | `1048576` (1MB) | Request body sent to agents |
| `max-agent-response-bytes` | `10240` (10KB) | Response size from agents |

These limits protect the proxy from misbehaving agents and ensure bounded memory usage.

## Rate Limiting

### Global Rate Limits

```kdl
limits {
    max-requests-per-second-global 10000
}
```

Global limit applies across all clients and routes.

### Per-Client Rate Limits

```kdl
limits {
    max-requests-per-second-per-client 100
}
```

Limits requests per unique client IP address.

### Per-Route Rate Limits

```kdl
limits {
    max-requests-per-second-per-route 1000
}
```

Limits total requests to each route.

### Rate Limit Behavior

Rate limiting uses token bucket algorithm:
- **Burst capacity:** 10× the per-second limit
- **Refill rate:** Continuous refill at configured rate
- **Response:** `429 Too Many Requests` with `Retry-After` header

Example:
```kdl
limits {
    max-requests-per-second-per-client 100
}
```
- Burst: 1000 requests
- Sustained: 100 requests/second
- Over limit: 429 response, retry in ~1 second

### Route-Level Rate Limits

For fine-grained control, configure rate limits per route:

```kdl
routes {
    route "api" {
        matches {
            path-prefix "/api/"
        }
        upstream "backend"
        policies {
            rate-limit {
                requests-per-second 100
                burst 500
                key "client_ip"  // or "header:X-API-Key"
            }
        }
    }
}
```

Rate limit keys:
- `client_ip` - Client IP address
- `header:X-API-Key` - Header value
- `path` - Request path
- `route` - Route ID

## Memory Limits

```kdl
limits {
    max-memory-bytes 2147483648     // 2GB hard limit
    max-memory-percent 80.0         // 80% of system memory
}
```

| Setting | Default | Description |
|---------|---------|-------------|
| `max-memory-bytes` | None | Absolute memory limit |
| `max-memory-percent` | None | Percentage of system memory |

When memory limits are reached:
1. New connections are rejected
2. Request queues are flushed
3. Alert is raised via metrics/logs

## Profile Presets

### Development

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

limits {
    // Permissive for testing
    max-header-size-bytes 16384
    max-header-count 200
    max-body-size-bytes 104857600  // 100MB
    max-in-flight-requests 100000

    // No rate limits
    max-requests-per-second-global #null
    max-requests-per-second-per-client #null
}

routes {
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        target "127.0.0.1:3000"
    }
}
```

### Production (Conservative)

```kdl
limits {
    // Restrictive headers
    max-header-size-bytes 4096
    max-header-count 50
    max-header-name-bytes 128
    max-header-value-bytes 2048

    // Limited body
    max-body-size-bytes 1048576  // 1MB
    max-body-buffer-bytes 524288 // 512KB

    // Connection protection
    max-connections-per-client 50
    max-total-connections 5000
    max-in-flight-requests 5000

    // Rate limiting
    max-requests-per-second-global 10000
    max-requests-per-second-per-client 100

    // Memory protection
    max-memory-percent 80.0
}
```

### High-Traffic API

```kdl
limits {
    // Standard headers
    max-header-size-bytes 8192
    max-header-count 100

    // JSON payloads
    max-body-size-bytes 10485760  // 10MB

    // High throughput
    max-connections-per-client 200
    max-connections-per-route 5000
    max-total-connections 50000
    max-in-flight-requests 50000
    max-in-flight-requests-per-worker 5000

    // Rate limiting
    max-requests-per-second-global 100000
    max-requests-per-second-per-client 1000
}
```

## Complete Example

```kdl
limits {
    // Headers
    max-header-size-bytes 8192
    max-header-count 100
    max-header-name-bytes 256
    max-header-value-bytes 4096

    // Bodies
    max-body-size-bytes 10485760
    max-body-buffer-bytes 1048576
    max-body-inspection-bytes 1048576

    // Decompression protection
    max-decompression-ratio 100.0
    max-decompressed-size-bytes 104857600

    // Connections
    max-connections-per-client 100
    max-connections-per-route 1000
    max-total-connections 10000
    max-idle-connections-per-upstream 100

    // Requests
    max-in-flight-requests 10000
    max-in-flight-requests-per-worker 1000
    max-queued-requests 1000

    // Agents
    max-agent-queue-depth 100
    max-agent-body-bytes 1048576
    max-agent-response-bytes 10240

    // Rate limiting
    max-requests-per-second-global 10000
    max-requests-per-second-per-client 100
    max-requests-per-second-per-route 1000

    // Memory
    max-memory-percent 80.0
}
```

## Bounds Outside the `limits` Block

The `limits` block above bounds individual requests and connections. Several
other resource bounds live elsewhere in the config — in `system`, in an
upstream's `connection-pool`, and on each agent. They are easy to overlook
precisely because they are not in `limits`, and they are the ones that decide
how the proxy behaves when it runs out of something.

```kdl
system {
    max-connections 10000
    route-cache-size 1000
}

upstreams {
    upstream "backend" {
        target "10.0.0.1:8080"
        connection-pool {
            max-connections 100
            max-idle 20
        }
    }
}

agents {
    agent "waf" {
        max-concurrent-calls 100
    }
}
```

| Setting | Block | Default | Bounds |
|---------|-------|---------|--------|
| `max-connections` | `system` | `10000` | Concurrent client connections |
| `route-cache-size` | `system` | `1000` | Cached route-match entries |
| `max-connections` | `connection-pool` | `100` | Connections per upstream target |
| `max-idle` | `connection-pool` | `20` | Idle connections kept per target |
| `max-concurrent-calls` | `agent` | `100` | In-flight calls to one agent |

**A `0` here means unbounded, not disabled.** `system.max-connections 0` accepts
connections without limit, and a `connection-pool` with `max-connections 0`
accumulates connections against a slow upstream until the process runs out of
them. If you want a component effectively off, give it a small number rather
than zero.

**`max-idle` above `max-connections` is unreachable.** The idle bound is capped
by the total, so the larger number silently has no effect.

## Checking Bounds with `zentinel lint`

`zentinel lint` inspects a config for bounds that are missing, unreachable, or
so generous they are indistinguishable from unbounded:

```bash
zentinel lint --config /etc/zentinel/zentinel.kdl
```

It reports, among other things:

| Condition | Why it is flagged |
|-----------|-------------------|
| `system.max-connections` is `0` | Accepts connections without limit; the process grows until it is killed |
| `system.max-connections` above `100000` | The file descriptor limit will be reached first — check `ulimit -n` |
| `route-cache-size` above `1000000` | Entries are keyed by method, host, path and any matched headers or query parameters, so a large cache on varied traffic holds a lot of memory for little hit rate |
| pool `max-connections` is `0` | The pool is unbounded against a slow upstream |
| pool `max-connections` above `10000` | More than most origins accept; the real limit becomes the origin's, and it surfaces as errors rather than backpressure |
| pool `max-idle` above `max-connections` | The idle bound can never be reached |
| `max-concurrent-calls` is `0` | Unbounded in-flight calls to a single agent |
| `max-concurrent-calls` above `10000` | Far past what an agent process will service |
| route `max-body-size` above 128 MB | With buffering that is held in memory per concurrent request |

These are warnings, not errors — a config that trips them still starts. They
mark places where behaviour under load will not match what the file appears to
say.

**Run it in CI.** The failure these catch shows up under load, which is the
worst time to find out. `zentinel test` validates that a config parses;
`zentinel lint` is what tells you whether its limits are meaningful.

## Default Values Summary

| Category | Setting | Default |
|----------|---------|---------|
| **Headers** | `max-header-size-bytes` | 8192 |
| | `max-header-count` | 100 |
| | `max-header-name-bytes` | 256 |
| | `max-header-value-bytes` | 4096 |
| **Bodies** | `max-body-size-bytes` | 10485760 (10MB) |
| | `max-body-buffer-bytes` | 1048576 (1MB) |
| | `max-body-inspection-bytes` | 1048576 (1MB) |
| **Decompression** | `max-decompression-ratio` | 100.0 |
| | `max-decompressed-size-bytes` | 104857600 (100MB) |
| **Connections** | `max-connections-per-client` | 100 |
| | `max-connections-per-route` | 1000 |
| | `max-total-connections` | 10000 |
| | `max-idle-connections-per-upstream` | 100 |
| **Requests** | `max-in-flight-requests` | 10000 |
| | `max-in-flight-requests-per-worker` | 1000 |
| | `max-queued-requests` | 1000 |
| **Agents** | `max-agent-queue-depth` | 100 |
| | `max-agent-body-bytes` | 1048576 (1MB) |
| | `max-agent-response-bytes` | 10240 (10KB) |
| **Rate Limits** | All rate limits | None (disabled) |
| **Memory** | Memory limits | None (disabled) |

## Monitoring Limits

### Metrics

Zentinel exposes limit-related metrics:

```
zentinel_header_size_exceeded_total
zentinel_body_size_exceeded_total
zentinel_connection_limit_reached_total
zentinel_rate_limit_exceeded_total
zentinel_memory_usage_bytes
zentinel_connections_active
zentinel_requests_in_flight
```

### Logging

Limit violations are logged at WARN level:

```json
{
  "level": "WARN",
  "message": "Request body size exceeded limit",
  "limit": 10485760,
  "actual": 15728640,
  "client_ip": "10.0.0.5",
  "trace_id": "2kF8xQw4BnM"
}
```

## Troubleshooting

### 413 Payload Too Large

Request body exceeds `max-body-size-bytes`:

```bash
# Check current limit
grep max-body-size zentinel.kdl

# Increase for specific route
route "upload" {
    policies {
        max-body-size "100MB"
    }
}
```

### 429 Too Many Requests

Rate limit exceeded:

```bash
# Check Retry-After header
curl -I https://api.example.com/endpoint
# Retry-After: 1

# Increase limits or implement client-side throttling
```

### 503 Service Unavailable (Connection Limit)

Connection or request limits reached:

1. Check current connections: `curl localhost:9090/admin/stats`
2. Review `max-total-connections` and `max-in-flight-requests`
3. Check for connection leaks in clients

## Next Steps

- [Server Configuration](../server/) - Worker threads and global settings
- [Upstreams](../upstreams/) - Connection pool settings
