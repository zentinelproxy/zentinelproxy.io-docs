+++
title = "Agents"
weight = 9
+++

Agents are external processes that extend Sentinel's functionality. They handle security policies, authentication, rate limiting, and custom business logic. The `agents` block configures how Sentinel connects to and communicates with these agents.

## Basic Configuration

```kdl
agents {
    agent "waf-agent" type="waf" {
        unix-socket "/var/run/sentinel/waf.sock"
        events "request_headers" "request_body"
        timeout-ms 200
        failure-mode "closed"
    }

    agent "auth-agent" type="auth" {
        grpc "http://localhost:50051"
        events "request_headers"
        timeout-ms 100
        failure-mode "closed"
        circuit-breaker {
            failure-threshold 5
            timeout-seconds 30
        }
    }
}
```

## Agent Types

| Type | Description |
|------|-------------|
| `waf` | Web Application Firewall |
| `auth` | Authentication and authorization |
| `rate_limit` | Rate limiting decisions |
| `custom` | Custom agent type (specify name) |

## Transports

### Unix Socket

Low-latency local communication:

```kdl
agent "local-agent" type="auth" {
    unix-socket "/var/run/sentinel/agent.sock"
    events "request_headers"
    timeout-ms 100
}
```

### gRPC

Remote agent over HTTP/2:

```kdl
agent "remote-agent" type="waf" {
    grpc "http://waf-service:50051"
    events "request_headers" "request_body"
    timeout-ms 200
}
```

With TLS:

```kdl
agent "secure-agent" type="auth" {
    grpc "https://auth-service:50051" {
        ca-cert "/etc/sentinel/ca.crt"
        client-cert "/etc/sentinel/client.crt"
        client-key "/etc/sentinel/client.key"
    }
    events "request_headers"
}
```

### HTTP

REST API agent:

```kdl
agent "http-agent" type="custom" {
    http "http://policy-service:8080/check" {
        tls-insecure  // Skip TLS verification (dev only)
    }
    events "request_headers"
    timeout-ms 150
}
```

## Events

Specify which lifecycle events the agent handles:

```kdl
agent "waf-agent" type="waf" {
    unix-socket "/var/run/sentinel/waf.sock"
    events "request_headers" "request_body" "response_headers"
}
```

| Event | Description |
|-------|-------------|
| `request_headers` | HTTP request headers received |
| `request_body` | Request body chunks |
| `response_headers` | Upstream response headers received |
| `response_body` | Response body chunks |
| `log` | Request complete (for logging) |
| `websocket_frame` | WebSocket frames (after upgrade) |

## Failure Handling

### Failure Mode

Configure behavior when the agent is unavailable:

```kdl
agent "auth-agent" type="auth" {
    failure-mode "closed"   // Block requests if agent fails
}

agent "analytics-agent" type="custom" {
    failure-mode "open"     // Allow requests if agent fails
}
```

| Mode | Behavior |
|------|----------|
| `closed` | Block requests when agent unavailable (security-first) |
| `open` | Allow requests through when agent unavailable (availability-first) |

### Circuit Breaker

Prevent cascading failures with circuit breakers:

```kdl
agent "waf-agent" type="waf" {
    circuit-breaker {
        failure-threshold 5         // Open after 5 failures
        success-threshold 2         // Close after 2 successes
        timeout-seconds 30          // Wait before half-open
        half-open-max-requests 1    // Requests in half-open state
    }
}
```

| Option | Default | Description |
|--------|---------|-------------|
| `failure-threshold` | `5` | Failures to open circuit |
| `success-threshold` | `2` | Successes to close circuit |
| `timeout-seconds` | `30` | Seconds before half-open |
| `half-open-max-requests` | `1` | Test requests in half-open |

Circuit breaker states:
- **Closed**: Normal operation
- **Open**: Agent bypassed (fails immediately)
- **Half-Open**: Testing if agent recovered

## Timeouts

```kdl
agent "waf-agent" type="waf" {
    timeout-ms 200         // Total call timeout
    chunk-timeout-ms 5000  // Per-chunk timeout (streaming)
}
```

## Body Processing

### Body Size Limits

```kdl
agent "waf-agent" type="waf" {
    max-request-body-bytes 10485760   // 10MB
    max-response-body-bytes 5242880   // 5MB
}
```

### Body Streaming Modes

Control how bodies are sent to agents:

```kdl
// Buffer entire body (default)
agent "waf-agent" type="waf" {
    request-body-mode "buffer"
    response-body-mode "buffer"
}

// Stream chunks as they arrive
agent "streaming-agent" type="custom" {
    request-body-mode "stream"
    chunk-timeout-ms 5000
}

// Hybrid: buffer small, stream large
agent "hybrid-agent" type="custom" {
    request-body-mode "hybrid:65536"   // Buffer up to 64KB
}
```

| Mode | Description |
|------|-------------|
| `buffer` | Collect entire body before sending (default) |
| `stream` | Send chunks as they arrive |
| `hybrid:<bytes>` | Buffer up to threshold, then stream |

## WAF Body Inspection

For WAF agents that need to inspect request bodies, Sentinel provides a dedicated body inspection pipeline with security controls.

### WAF Configuration Block

Configure body inspection globally via the `waf` block:

```kdl
waf {
    body-inspection {
        inspect-request-body #true
        inspect-response-body #false
        max-body-inspection-bytes 1048576   // 1MB
        content-types "application/json" "application/x-www-form-urlencoded" "text/xml"
        decompress #true
        max-decompression-ratio 100.0
    }
}
```

### Body Inspection Options

| Option | Default | Description |
|--------|---------|-------------|
| `inspect-request-body` | `false` | Enable request body inspection |
| `inspect-response-body` | `false` | Enable response body inspection |
| `max-body-inspection-bytes` | `1048576` | Max bytes to buffer for inspection |
| `content-types` | See below | Content types eligible for inspection |
| `decompress` | `false` | Decompress bodies before inspection |
| `max-decompression-ratio` | `100.0` | Max compression ratio (zip bomb protection) |

Default content types for inspection:
- `application/json`
- `application/x-www-form-urlencoded`
- `text/xml`
- `application/xml`
- `text/plain`

### Body Decompression

When `decompress` is enabled, Sentinel automatically decompresses request bodies before sending them to WAF agents. This allows WAF rules to inspect the actual content of compressed payloads.

**Supported encodings:**
- `gzip` - Most common compression
- `deflate` - Raw deflate compression
- `br` - Brotli compression

**Security protections:**

| Protection | Default | Description |
|------------|---------|-------------|
| Max ratio | 100x | Prevents zip bombs (rejects if decompressed/compressed > ratio) |
| Max output size | 10MB | Hard limit on decompressed size |
| Fail mode | Route setting | Uses route's `failure-mode` for decompression errors |

```kdl
waf {
    body-inspection {
        decompress #true
        max-decompression-ratio 50.0    // Stricter limit for sensitive routes
    }
}
```

### Decompression Behavior

| Scenario | fail-open | fail-closed |
|----------|-----------|-------------|
| Decompression succeeds | Inspect decompressed body | Inspect decompressed body |
| Ratio exceeded | Inspect compressed body | Block with 400 |
| Size exceeded | Inspect compressed body | Block with 400 |
| Invalid data | Inspect compressed body | Block with 400 |

### Metrics

Decompression operations are tracked via Prometheus metrics:

| Metric | Labels | Description |
|--------|--------|-------------|
| `sentinel_decompression_total` | `encoding`, `result` | Total decompression operations |
| `sentinel_decompression_ratio` | `encoding` | Histogram of compression ratios |

Result labels: `success`, `ratio_exceeded`, `size_exceeded`, `invalid_data`, `io_error`

### Complete WAF Example

```kdl
waf {
    body-inspection {
        inspect-request-body #true
        max-body-inspection-bytes 1048576
        content-types "application/json" "application/xml" "text/plain"
        decompress #true
        max-decompression-ratio 100.0
    }
}

agents {
    agent "modsecurity" type="waf" {
        unix-socket "/var/run/sentinel/modsec.sock"
        events "request_headers" "request_body"
        timeout-ms 200
        failure-mode "closed"
        request-body-mode "buffer"
        circuit-breaker {
            failure-threshold 10
            timeout-seconds 60
        }
        config {
            rules-path "/etc/modsecurity/crs"
            paranoia-level 2
        }
    }
}

routes {
    route "api" {
        matches { path-prefix "/api/" }
        upstream "backend"
        policies {
            failure-mode "closed"   // Used for decompression errors
        }
        filters "waf-filter"
    }
}

filters {
    filter "waf-filter" {
        type "agent"
        agent "modsecurity"
        phase "request"
        failure-mode "closed"
    }
}
```

## Agent-Specific Configuration

Pass configuration to agents via the `config` block:

```kdl
agent "waf-agent" type="waf" {
    unix-socket "/var/run/sentinel/waf.sock"
    config {
        rules-path "/etc/sentinel/waf-rules"
        paranoia-level 2
        block-suspicious #true
    }
}
```

The configuration is passed to the agent when it connects.

## Attaching Agents to Routes

Reference agents in route configuration:

```kdl
routes {
    // Via filters
    route "api" {
        filters "waf-filter"   // Filter referencing agent
    }
}

filters {
    filter "waf-filter" {
        type "agent"
        agent "waf-agent"
        phase "request"
        timeout-ms 200
        failure-mode "closed"
    }
}
```

## Complete Examples

### WAF Agent

```kdl
agents {
    agent "modsecurity" type="waf" {
        unix-socket "/var/run/sentinel/modsec.sock"
        events "request_headers" "request_body"
        timeout-ms 200
        failure-mode "closed"
        max-request-body-bytes 1048576    // 1MB for inspection
        request-body-mode "buffer"
        circuit-breaker {
            failure-threshold 10
            timeout-seconds 60
        }
        config {
            rules-path "/etc/modsecurity/crs"
            paranoia-level 1
        }
    }
}
```

### Authentication Agent

```kdl
agents {
    agent "jwt-auth" type="auth" {
        grpc "http://auth-service:50051"
        events "request_headers"
        timeout-ms 50
        failure-mode "closed"
        circuit-breaker {
            failure-threshold 5
            timeout-seconds 30
        }
        config {
            issuer "https://auth.example.com"
            audience "api.example.com"
        }
    }
}
```

### Rate Limiting Agent

```kdl
agents {
    agent "rate-limiter" type="rate_limit" {
        grpc "http://ratelimit-service:50051"
        events "request_headers"
        timeout-ms 20
        failure-mode "open"    // Allow through if service down
        circuit-breaker {
            failure-threshold 3
            timeout-seconds 15
        }
    }
}
```

### Logging/Analytics Agent

```kdl
agents {
    agent "analytics" type="custom" {
        http "http://analytics:8080/log"
        events "log"           // Only receive completion events
        timeout-ms 1000
        failure-mode "open"    // Don't block requests for logging
    }
}
```

## TLS Configuration

### gRPC with mTLS

```kdl
agent "secure-agent" type="waf" {
    grpc "https://waf-service:50051" {
        ca-cert "/etc/sentinel/ca.crt"
        client-cert "/etc/sentinel/client.crt"
        client-key "/etc/sentinel/client.key"
    }
}
```

### Skip Verification (Development Only)

```kdl
agent "dev-agent" type="custom" {
    grpc "https://localhost:50051" {
        tls-insecure
    }
}
```

## Default Values

| Setting | Default |
|---------|---------|
| `timeout-ms` | `1000` (1 second) |
| `failure-mode` | `open` |
| `chunk-timeout-ms` | `5000` (5 seconds) |
| `request-body-mode` | `buffer` |
| `response-body-mode` | `buffer` |
| `circuit-breaker.failure-threshold` | `5` |
| `circuit-breaker.success-threshold` | `2` |
| `circuit-breaker.timeout-seconds` | `30` |
| `circuit-breaker.half-open-max-requests` | `1` |

## Metrics

Agent-related metrics:

| Metric | Description |
|--------|-------------|
| `sentinel_agent_requests_total` | Agent calls by agent and status |
| `sentinel_agent_duration_seconds` | Agent call latency |
| `sentinel_agent_errors_total` | Agent errors |
| `sentinel_agent_timeouts_total` | Agent timeouts |
| `sentinel_agent_circuit_breaker_state` | Circuit breaker state |

## Next Steps

- [Agent Protocol](../../agents/protocol/) - Wire protocol specification
- [Building Agents](../../agents/building/) - Creating custom agents
- [Filters](../filters/) - Using agents in filter chains
