+++
title = "Agents"
weight = 9
updated = 2026-10-20
+++

Agents are external processes that extend Zentinel's functionality. They handle security policies, authentication, rate limiting, and custom business logic. The `agents` block configures how Zentinel connects to and communicates with these agents.

## Basic Configuration

```kdl
agents {
    agent "waf-agent" type="waf" {
        unix-socket "/var/run/zentinel/waf.sock"
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
    unix-socket "/var/run/zentinel/agent.sock"
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

<!-- fragment,kdl: zentinel lint (26.10_3) wrongly reports ca-cert/client-cert/client-key/tls-insecure directly under grpc/http as ignored; parse_agent_tls in crates/config/src/kdl/mod.rs reads exactly this form. -->
```fragment,kdl
agent "secure-agent" type="auth" {
    grpc "https://auth-service:50051" {
        ca-cert "/etc/zentinel/ca.crt"
        client-cert "/etc/zentinel/client.crt"
        client-key "/etc/zentinel/client.key"
    }
    events "request_headers"
}
```

### HTTP

REST API agent using JSON over HTTP. This is the simplest transport option, making it easy to build agents in any language with HTTP support.

#### Basic HTTP

```kdl
agent "http-agent" type="custom" {
    http "http://policy-service:8080/agent"
    events "request_headers"
    timeout-ms 150
}
```

#### HTTPS with TLS

<!-- fragment,kdl: zentinel lint (26.10_3) wrongly reports ca-cert/client-cert/client-key/tls-insecure directly under grpc/http as ignored; parse_agent_tls in crates/config/src/kdl/mod.rs reads exactly this form. -->
```fragment,kdl
agent "secure-http-agent" type="auth" {
    http "https://auth-service:8443/agent" {
        ca-cert "/etc/zentinel/certs/ca.crt"
    }
    events "request_headers"
    timeout-ms 100
}
```

#### HTTPS with mTLS

<!-- fragment,kdl: zentinel lint (26.10_3) wrongly reports ca-cert/client-cert/client-key/tls-insecure directly under grpc/http as ignored; parse_agent_tls in crates/config/src/kdl/mod.rs reads exactly this form. -->
```fragment,kdl
agent "mtls-agent" type="waf" {
    http "https://waf-service:8443/agent" {
        ca-cert "/etc/zentinel/certs/ca.crt"
        client-cert "/etc/zentinel/certs/client.crt"
        client-key "/etc/zentinel/certs/client.key"
    }
    events "request_headers" "request_body"
    timeout-ms 200
}
```

#### HTTP Protocol

Zentinel sends events as JSON POST requests:

```http
POST /agent HTTP/1.1
Host: policy-service:8080
Content-Type: application/json
X-Zentinel-Protocol-Version: 1

{
  "version": 1,
  "event_type": "request_headers",
  "payload": {
    "metadata": {
      "correlation_id": "abc123",
      "request_id": "req-456",
      "client_ip": "192.168.1.100",
      "route_id": "api-route"
    },
    "method": "POST",
    "uri": "/api/users",
    "headers": {
      "content-type": ["application/json"],
      "authorization": ["Bearer token..."]
    }
  }
}
```

Agents respond with JSON:

```json
{
  "version": 1,
  "decision": "allow",
  "request_headers": [
    {"set": {"name": "X-User-ID", "value": "user-123"}}
  ],
  "audit": {
    "tags": ["authenticated"],
    "rule_ids": ["auth-001"]
  }
}
```

#### When to Use HTTP

| Use Case | Recommended Transport |
|----------|----------------------|
| Simple agents in any language | HTTP |
| High-throughput, low-latency | Unix Socket |
| Binary protocol, streaming | gRPC |
| Cross-network, load-balanced | HTTP or gRPC |
| Development/prototyping | HTTP |

HTTP advantages:
- Works with any language/framework that handles HTTP
- Easy to debug with curl or browser tools
- Simple JSON payloads
- Standard load balancers and proxies work out of the box

HTTP trade-offs:
- Higher overhead than Unix sockets
- No streaming (full request/response per call)
- JSON parsing overhead vs binary protocols

## Events

Specify which lifecycle events the agent handles:

```kdl
agent "waf-agent" type="waf" {
    unix-socket "/var/run/zentinel/waf.sock"
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

### Request vs Response Phase

Events are processed in two phases:

- **Request phase** (`request_headers`, `request_body`): Before the request is forwarded to the upstream. The agent can allow, block, or modify the request.
- **Response phase** (`response_headers`, `response_body`): After the upstream responds. The agent can inspect and modify response headers and body.

An agent that needs both phases (e.g. image optimization) must subscribe to events from both:

```kdl
agent "image-optimizer" type="custom" {
    unix-socket "/var/run/zentinel/image-opt.sock"
    events "request_headers" "response_headers" "response_body"
    timeout-ms 5000
    failure-mode "open"
}
```

In the request phase, the agent receives the client's `Accept` header to negotiate the output format. In the response phase, it receives the upstream's response headers (to check `Content-Type`) and the response body (to perform the conversion).

### Response Header Modifications

When an agent subscribes to `response_headers`, its Decision can include `response_headers` operations that modify headers before they are sent to the client:

```json
{
  "decision": "allow",
  "response_headers": [
    {"set": {"name": "content-type", "value": "image/avif"}},
    {"set": {"name": "vary", "value": "Accept"}},
    {"remove": {"name": "content-length"}}
  ],
  "needs_more": true
}
```

Setting `needs_more: true` tells the proxy that the agent expects to receive subsequent events (e.g. response body chunks).

### Response Body Mutations

When an agent subscribes to `response_body`, it receives body chunks (base64-encoded) and can return a `BodyMutation` to replace the body:

```json
{
  "decision": "allow",
  "response_body_mutation": {
    "data": "<base64-encoded replacement body>"
  }
}
```

| `data` value | Behavior |
|--------------|----------|
| `null` / absent | Pass through original body |
| `""` (empty) | Drop the chunk |
| `"<base64>"` | Replace body with decoded content |

When response body processing is active, the proxy automatically sets `Connection: close` and removes the original `Content-Length` header since the body size may change.

## Failure Handling

### Failure Mode

Configure behavior when the agent is unavailable:

```kdl
agent "auth-agent" type="auth" {
    unix-socket "/var/run/zentinel/auth.sock"
    failure-mode "closed"   // Block requests if agent fails
}

agent "analytics-agent" type="custom" {
    unix-socket "/var/run/zentinel/analytics.sock"
    failure-mode "open"     // Allow requests if agent fails
}
```

| Mode | Behavior |
|------|----------|
| `closed` | Block requests when agent unavailable (security-first) |
| `open` | Allow requests through when agent unavailable (availability-first) |

{% callout(type="warning") %}
What decides a request when an agent is unavailable during the request-headers
call is the `failure-mode` on the **filter** that calls the agent, then the
route's `policies { failure-mode }`, and otherwise `closed`. The value on the
`agent` block does not decide that call; it applies to request bodies,
responses and WebSocket frames. Set `failure-mode` on the filter, as in
[Your First Agent](/getting-started/first-agent/#6-stop-the-agent).

From 26.10_5, `zentinel test` and `lint` report an agent block's
`failure-mode` when a filter using that agent sets none, and an unrecognised
filter value such as `"fail-open"` (which means the route's mode, `closed` by
default). Before 26.10_5 neither was reported
([#529](https://github.com/zentinelproxy/zentinel/issues/529)).
{% end %}

### Circuit Breaker

Prevent cascading failures with circuit breakers:

```kdl
agent "waf-agent" type="waf" {
    unix-socket "/var/run/zentinel/waf.sock"
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
    unix-socket "/var/run/zentinel/waf.sock"
    timeout-ms 200         // Total call timeout
    chunk-timeout-ms 5000  // Per-chunk timeout (streaming)
}
```

## Body Processing

### Body Size Limits

```kdl
agent "waf-agent" type="waf" {
    unix-socket "/var/run/zentinel/waf.sock"
    max-request-body-bytes 10485760   // 10MB
    max-response-body-bytes 5242880   // 5MB
}
```

### Body Streaming Modes

Control how bodies are sent to agents:

```kdl
// Buffer entire body (default)
agent "waf-agent" type="waf" {
    unix-socket "/var/run/zentinel/waf.sock"
    request-body-mode "buffer"
    response-body-mode "buffer"
}

// Stream chunks as they arrive
agent "streaming-agent" type="custom" {
    unix-socket "/var/run/zentinel/streaming.sock"
    request-body-mode "stream"
    chunk-timeout-ms 5000
}

// Hybrid: buffer small, stream large
agent "hybrid-agent" type="custom" {
    unix-socket "/var/run/zentinel/hybrid.sock"
    request-body-mode "hybrid:65536"   // Buffer up to 64KB
}
```

| Mode | Description |
|------|-------------|
| `buffer` | Collect entire body before sending (default) |
| `stream` | Send chunks as they arrive |
| `hybrid:<bytes>` | Buffer up to threshold, then stream |

## WAF Body Inspection

For WAF agents that need to inspect request bodies, Zentinel provides a dedicated body inspection pipeline with security controls.

### WAF Configuration Block

Configure body inspection globally via the `waf` block. Only `body-inspection`
is used from that block, and the block must set `mode "off"`: any other mode
fails validation because no WAF engine runs in the proxy itself (see
[WAF](../waf/)).

```kdl
waf {
    mode "off"   // required; inspection is done by the agents
    body-inspection {
        inspect-request-body #true
        inspect-response-body #false
        max-inspection-bytes 1048576   // 1MB
        content-types "application/json" "application/x-www-form-urlencoded" "text/xml"
        decompress #true
        max-decompression-ratio 100
    }
}
```

### Body Inspection Options

| Option | Default | Description |
|--------|---------|-------------|
| `inspect-request-body` | `true` | Enable request body inspection (without a `waf` block, bodies are not inspected) |
| `inspect-response-body` | `false` | Enable response body inspection |
| `max-inspection-bytes` | `1048576` | Max bytes to buffer for inspection |
| `content-types` | See below | Content types eligible for inspection |
| `decompress` | `false` | Decompress bodies before inspection |
| `max-decompression-ratio` | `100` | Max compression ratio (zip bomb protection; an integer) |

Default content types for inspection:
- `application/x-www-form-urlencoded`
- `multipart/form-data`
- `application/json`
- `application/xml`
- `text/xml`

### Body Decompression

When `decompress` is enabled, Zentinel automatically decompresses request bodies before sending them to WAF agents. This allows WAF rules to inspect the actual content of compressed payloads.

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
    mode "off"
    body-inspection {
        decompress #true
        max-decompression-ratio 50    // Stricter limit
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
| `zentinel_decompression_total` | `encoding`, `result` | Total decompression operations |
| `zentinel_decompression_ratio` | `encoding` | Histogram of compression ratios |

Result labels: `success`, `ratio_exceeded`, `size_exceeded`, `invalid_data`, `io_error`

### Complete WAF Example

```kdl
waf {
    mode "off"   // body inspection only; the agent does the WAF work
    body-inspection {
        inspect-request-body #true
        max-inspection-bytes 1048576
        content-types "application/json" "application/xml" "text/plain"
        decompress #true
        max-decompression-ratio 100
    }
}

agents {
    agent "modsecurity" type="waf" {
        unix-socket "/var/run/zentinel/modsec.sock"
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
        failure-mode "closed"
    }
}
```

## Agent-Specific Configuration

Pass configuration to agents via the `config` block:

```kdl
agent "waf-agent" type="waf" {
    unix-socket "/var/run/zentinel/waf.sock"
    config {
        rules-path "/etc/zentinel/waf-rules"
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
        matches { path-prefix "/api/" }
        upstream "backend"
        filters "waf-filter"   // Filter referencing agent
    }
}

filters {
    filter "waf-filter" {
        type "agent"
        agent "waf-agent"
        timeout-ms 200
        failure-mode "closed"
    }
}
```

A filter's `timeout-ms` applies to its `request_headers` call and can only
shorten the agent's `timeout-ms`; the shorter of the two is used. `phase` is
not read on an agent filter (the agent's `events` decide what it receives) and
is reported as ignored. Both from 26.10_6; before, the filter's `timeout-ms`
was not read either. See [Filters: Agent Filter](../filters/#agent-filter).

## Complete Examples

### WAF Agent

```kdl
agents {
    agent "modsecurity" type="waf" {
        unix-socket "/var/run/zentinel/modsec.sock"
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

### Response Processing Agent (Image Optimization)

```kdl
agents {
    agent "image-optimizer" type="custom" {
        unix-socket "/var/run/zentinel/image-opt.sock"
        events "request_headers" "response_headers" "response_body"
        timeout-ms 5000
        failure-mode "open"
        response-body-mode "buffer"
        max-response-body-bytes 10485760    // 10MB
    }
}

filters {
    filter "image-optimization" {
        type "agent"
        agent "image-optimizer"
        timeout-ms 5000
        failure-mode "open"
    }
}

routes {
    route "images" {
        matches { path-prefix "/images/" }
        upstream "backend"
        filters "image-optimization"
    }
}
```

The agent receives `request_headers` to extract the client's `Accept` header, `response_headers` to check the upstream's `Content-Type` and set output headers, and `response_body` to perform the image conversion.

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

Secure gRPC connections to agents with TLS and mutual TLS (mTLS).

### TLS Options

| Option | Description |
|--------|-------------|
| `ca-cert` | Path to CA certificate for verifying the agent's server certificate |
| `client-cert` | Path to client certificate for mTLS authentication |
| `client-key` | Path to client private key for mTLS authentication |
| `tls-insecure` | Skip certificate verification (development only) |

### Server TLS (One-Way)

Verify the agent's identity using TLS:

<!-- fragment,kdl: zentinel lint (26.10_3) wrongly reports ca-cert/client-cert/client-key/tls-insecure directly under grpc/http as ignored; parse_agent_tls in crates/config/src/kdl/mod.rs reads exactly this form. -->
```fragment,kdl
agent "secure-agent" type="auth" {
    grpc "https://auth-service.internal:50051" {
        ca-cert "/etc/zentinel/certs/ca.crt"
    }
    events "request_headers"
    timeout-ms 100
}
```

This configuration:
- Encrypts traffic between Zentinel and the agent
- Verifies the agent's certificate against the provided CA
- Automatically extracts domain name for SNI from the address

### Mutual TLS (mTLS)

For bidirectional authentication where both Zentinel and the agent verify each other:

<!-- fragment,kdl: zentinel lint (26.10_3) wrongly reports ca-cert/client-cert/client-key/tls-insecure directly under grpc/http as ignored; parse_agent_tls in crates/config/src/kdl/mod.rs reads exactly this form. -->
```fragment,kdl
agent "secure-waf" type="waf" {
    grpc "https://waf-service.internal:50051" {
        ca-cert "/etc/zentinel/certs/ca.crt"
        client-cert "/etc/zentinel/certs/zentinel-client.crt"
        client-key "/etc/zentinel/certs/zentinel-client.key"
    }
    events "request_headers" "request_body"
    timeout-ms 200
    failure-mode "closed"
}
```

This configuration:
- Encrypts traffic with TLS
- Verifies the agent's certificate against the CA
- Presents Zentinel's client certificate to the agent for verification
- Provides strong mutual authentication for security-sensitive agents

### Using System CA Store

When no `ca-cert` is specified, Zentinel uses the system's native certificate store for server verification:

```kdl
agent "public-agent" type="custom" {
    grpc "https://agent.example.com:50051"
    events "request_headers"
}
```

This works well for agents using certificates from public CAs (Let's Encrypt, DigiCert, etc.).

### Skip Verification (Development Only)

**Warning:** Only use this for local development. Never use in production.

<!-- fragment,kdl: zentinel lint (26.10_3) wrongly reports ca-cert/client-cert/client-key/tls-insecure directly under grpc/http as ignored; parse_agent_tls in crates/config/src/kdl/mod.rs reads exactly this form. -->
```fragment,kdl
agent "dev-agent" type="custom" {
    grpc "https://localhost:50051" {
        tls-insecure
    }
    events "request_headers"
}
```

When enabled, Zentinel logs a security warning:
```
WARN: TLS certificate verification disabled for agent connection
```

### Certificate Setup

#### Generate CA and Certificates

```bash
# Create CA
openssl genrsa -out ca.key 4096
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt \
    -subj "/CN=Zentinel Agent CA"

# Create agent server certificate
openssl genrsa -out agent.key 2048
openssl req -new -key agent.key -out agent.csr \
    -subj "/CN=waf-service.internal"
openssl x509 -req -days 365 -in agent.csr -CA ca.crt -CAkey ca.key \
    -CAcreateserial -out agent.crt

# Create Zentinel client certificate (for mTLS)
openssl genrsa -out zentinel-client.key 2048
openssl req -new -key zentinel-client.key -out zentinel-client.csr \
    -subj "/CN=zentinel-proxy"
openssl x509 -req -days 365 -in zentinel-client.csr -CA ca.crt -CAkey ca.key \
    -CAcreateserial -out zentinel-client.crt
```

#### File Permissions

```bash
# Secure the private keys
chmod 600 /etc/zentinel/certs/*.key
chown zentinel:zentinel /etc/zentinel/certs/*
```

### Complete Secure Agent Example

<!-- fragment,kdl: zentinel lint (26.10_3) wrongly reports ca-cert/client-cert/client-key/tls-insecure directly under grpc/http as ignored; parse_agent_tls in crates/config/src/kdl/mod.rs reads exactly this form. -->
```fragment,kdl
agents {
    // WAF with mTLS - highest security
    agent "modsecurity" type="waf" {
        grpc "https://waf.internal:50051" {
            ca-cert "/etc/zentinel/certs/ca.crt"
            client-cert "/etc/zentinel/certs/zentinel-client.crt"
            client-key "/etc/zentinel/certs/zentinel-client.key"
        }
        events "request_headers" "request_body"
        timeout-ms 200
        failure-mode "closed"
        circuit-breaker {
            failure-threshold 10
            timeout-seconds 60
        }
    }

    // Auth with server-only TLS
    agent "jwt-auth" type="auth" {
        grpc "https://auth.internal:50051" {
            ca-cert "/etc/zentinel/certs/ca.crt"
        }
        events "request_headers"
        timeout-ms 50
        failure-mode "closed"
    }

    // Rate limiter - internal network, no TLS
    agent "rate-limiter" type="rate_limit" {
        grpc "http://ratelimit.internal:50051"
        events "request_headers"
        timeout-ms 20
        failure-mode "open"
    }
}
```

### Troubleshooting TLS

| Error | Cause | Solution |
|-------|-------|----------|
| `certificate verify failed` | CA doesn't match agent cert | Verify CA certificate is correct |
| `certificate has expired` | Agent cert expired | Renew agent certificate |
| `handshake failure` | TLS version mismatch | Check both ends support TLS 1.2+ |
| `unknown ca` | Missing CA cert | Add `ca-cert` option |
| `bad certificate` | Client cert rejected | Verify client cert signed by agent's CA |

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
| `zentinel_agent_requests_total` | Agent calls by agent and status |
| `zentinel_agent_duration_seconds` | Agent call latency |
| `zentinel_agent_errors_total` | Agent errors |
| `zentinel_agent_timeouts_total` | Agent timeouts |
| `zentinel_agent_circuit_breaker_state` | Circuit breaker state |

## Configuration Validation

Zentinel validates agent configuration at startup:

### Transport Validation

| Transport | Validation |
|-----------|------------|
| Unix Socket | The socket's parent directory exists (the socket itself is not checked) |
| gRPC | Valid URL format (http/https with host) |
| HTTP | Valid URL format |

Example validation errors:

```
Agent 'auth' unix socket path parent directory doesn't exist: "/var/run/zentinel/auth.sock"
```

A socket that does not exist yet, or a gRPC agent that is not running, passes
`zentinel test`; use `zentinel validate` (below) to check that agents are
reachable.

### Pre-flight Checks

Run validation before deployment:

```bash
zentinel validate --config zentinel.kdl
```

This checks:
- All referenced agents exist
- Transport paths/URLs are valid
- Timeout values are within bounds
- Circuit breaker thresholds are valid

> **Note:** Agent TLS (configured in this section) secures the connection between Zentinel and the agent process. This is separate from **upstream TLS**, which secures the connection between Zentinel and your backend servers. If your backend serves HTTPS, see [Upstream TLS](/configuration/upstreams/#upstream-tls).

## Next Steps

- [Agent Protocol](/agents/v2/protocol/) - Wire protocol specification
- [Building Agents](/agents/v2/api/) - Creating custom agents
- [Filters](../filters/) - Using agents in filter chains
