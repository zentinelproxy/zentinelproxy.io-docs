+++
title = "Request Lifecycle"
weight = 5
+++

This page details the complete lifecycle of an HTTP request through Sentinel, from client connection to response delivery.

## Overview

```
┌────────┐                                                           ┌──────────┐
│ Client │                                                           │ Upstream │
└───┬────┘                                                           └────┬─────┘
    │                                                                     │
    │  1. TCP Connect                                                     │
    │────────────────────▶┌─────────────────────────────────┐             │
    │                     │                                 │             │
    │  2. TLS Handshake   │         Sentinel Proxy          │             │
    │────────────────────▶│                                 │             │
    │                     │  ┌───────────────────────────┐  │             │
    │  3. HTTP Request    │  │     Request Pipeline      │  │             │
    │────────────────────▶│  │                           │  │             │
    │                     │  │  Parse → Route → Filter   │  │             │
    │                     │  │    → Agents → Forward     │  │  4. Forward │
    │                     │  └───────────────────────────┘  │────────────▶│
    │                     │                                 │             │
    │                     │  ┌───────────────────────────┐  │  5. Response│
    │                     │  │    Response Pipeline      │  │◀────────────│
    │  6. HTTP Response   │  │                           │  │             │
    │◀────────────────────│  │  Filter → Headers → Send  │  │             │
    │                     │  └───────────────────────────┘  │             │
    │                     │                                 │             │
    │                     └─────────────────────────────────┘             │
    │                                                                     │
```

## Phase 1: Connection Establishment

### TCP Accept

When a client connects, Pingora's listener accepts the TCP connection:

```
Client                          Sentinel
   │                                │
   │──── TCP SYN ─────────────────▶│
   │◀─── TCP SYN-ACK ──────────────│
   │──── TCP ACK ─────────────────▶│
   │                                │
   │      Connection established    │
```

**What happens:**
1. Pingora accepts connection from the listener socket
2. Connection is assigned to a worker thread
3. Client address is captured for logging and rate limiting

### TLS Handshake (HTTPS only)

For HTTPS listeners, TLS negotiation occurs:

```
Client                          Sentinel
   │                                │
   │──── ClientHello ─────────────▶│  Supported ciphers, SNI
   │◀─── ServerHello ──────────────│  Selected cipher, certificate
   │──── Key Exchange ────────────▶│
   │◀─── Finished ─────────────────│
   │                                │
   │      TLS session established   │
```

**Configuration impact:**
- TLS versions allowed (1.2, 1.3)
- Cipher suite selection
- Certificate chain validation
- SNI-based certificate selection

## Phase 2: Request Reception

### HTTP Parsing

Sentinel parses the incoming HTTP request:

```
┌─────────────────────────────────────────────────────────────┐
│                      HTTP Request                            │
├─────────────────────────────────────────────────────────────┤
│  POST /api/users HTTP/1.1                    ◀── Request Line│
│  Host: api.example.com                       ◀── Headers     │
│  Content-Type: application/json                              │
│  Authorization: Bearer eyJ...                                │
│  X-Request-Id: abc-123                                       │
│                                                              │
│  {"name": "Alice", "email": "alice@..."}     ◀── Body       │
└─────────────────────────────────────────────────────────────┘
```

**Extracted information:**
- Method (GET, POST, etc.)
- Path and query string
- Host header
- All request headers
- Content-Length or Transfer-Encoding

### Limit Enforcement

Before processing, hard limits are checked:

```rust
// Header count limit
if headers.len() > config.limits.max_header_count {
    return Error::TooManyHeaders;  // 400 Bad Request
}

// Header size limit
let total_size: usize = headers.iter()
    .map(|(k, v)| k.len() + v.len())
    .sum();

if total_size > config.limits.max_header_size_bytes {
    return Error::HeadersTooLarge;  // 431 Request Header Fields Too Large
}
```

| Limit | Default | Purpose |
|-------|---------|---------|
| `max_header_count` | 100 | Prevent header flooding |
| `max_header_size_bytes` | 8KB | Prevent memory exhaustion |
| `max_body_size_bytes` | 10MB | Prevent large payload attacks |

### Trace ID Assignment

Every request gets a correlation ID for distributed tracing:

```
┌──────────────────────────────────────────────────────────────┐
│                    Trace ID Sources                           │
├──────────────────────────────────────────────────────────────┤
│  1. Incoming header (X-Request-Id, X-Correlation-Id)         │
│     └─▶ Reuse existing ID from upstream services             │
│                                                              │
│  2. Generate new ID if not present                           │
│     ├─▶ UUID v4: 550e8400-e29b-41d4-a716-446655440000       │
│     └─▶ UUID v7: 018f6b1c-8a1d-7000-8000-000000000000       │
└──────────────────────────────────────────────────────────────┘
```

The trace ID propagates through:
- Request headers to upstream
- Response headers to client
- All log entries
- Metrics labels
- Agent requests

## Phase 3: Route Matching

### Route Selection

Sentinel matches the request against compiled routes:

```
Request: POST /api/users/123/profile
         Host: api.example.com

                    │
                    ▼
         ┌──────────────────┐
         │  Compiled Routes │
         │  (sorted by      │
         │   priority)      │
         └────────┬─────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
    ▼             ▼             ▼
┌────────┐   ┌────────┐   ┌────────┐
│Route A │   │Route B │   │Route C │
│pri: 100│   │pri: 50 │   │pri: 10 │
│        │   │        │   │        │
│ path:  │   │ path:  │   │ path:  │
│ /api/* │   │ /api/  │   │ /*     │
│        │   │ users/*│   │        │
└────────┘   └────────┘   └────────┘
     │            │
     │       ✓ MATCH (more specific)
     │
     ✓ MATCH (lower priority)

Winner: Route B (highest priority match)
```

### Match Criteria

Routes can match on multiple criteria:

| Criteria | Example | Evaluation |
|----------|---------|------------|
| **Path exact** | `/api/health` | String equality |
| **Path prefix** | `/api/` | Starts with |
| **Path regex** | `/users/\d+` | Regex match |
| **Host** | `api.example.com` | Host header match |
| **Method** | `GET`, `POST` | Method in list |
| **Header** | `X-Api-Version: 2` | Header exists/equals |
| **Query param** | `?version=2` | Param exists/equals |

### No Route Found

If no route matches:

```
┌─────────────────────────────────────────┐
│           No Matching Route             │
├─────────────────────────────────────────┤
│  Status: 404 Not Found                  │
│                                         │
│  Response:                              │
│  {                                      │
│    "error": "no_route",                 │
│    "message": "No route matched",       │
│    "path": "/unknown/path",             │
│    "trace_id": "abc-123"                │
│  }                                      │
└─────────────────────────────────────────┘
```

## Phase 4: Service Type Handling

Based on the matched route's service type, different handlers take over:

```
                    Route Matched
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │  Static  │   │  Builtin │   │   Proxy  │
    │  Files   │   │ Handlers │   │ (Web/API)│
    └────┬─────┘   └────┬─────┘   └────┬─────┘
         │              │              │
         ▼              ▼              ▼
    Serve from      Handle         Continue to
    filesystem      internally     agent processing
```

### Static File Serving

For `service_type = "static"`:

```
Request: GET /assets/logo.png

    │
    ▼
┌────────────────────────┐
│ Resolve file path      │
│ root + request_path    │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Security checks:       │
│ • Path traversal       │
│ • Symlink validation   │
│ • Extension allowlist  │
└───────────┬────────────┘
            │
    ┌───────┴───────┐
    │               │
    ▼               ▼
  Found         Not Found
    │               │
    ▼               ▼
 Stream file    Try index.html
 with correct   or return 404
 Content-Type
```

### Builtin Handlers

For `service_type = "builtin"`:

| Handler | Path | Response |
|---------|------|----------|
| `health` | `/-/health` | `{"status": "healthy"}` |
| `ready` | `/-/ready` | `{"status": "ready"}` |
| `metrics` | `/-/metrics` | Prometheus metrics |
| `version` | `/-/version` | Build info |

## Phase 5: Agent Processing

For routes with configured agents, external processing occurs:

```
                    Request
                       │
                       ▼
              ┌────────────────┐
              │ Agent Manager  │
              └───────┬────────┘
                      │
       ┌──────────────┼──────────────┐
       │              │              │
       ▼              ▼              ▼
  ┌─────────┐   ┌─────────┐   ┌─────────┐
  │  Auth   │   │   WAF   │   │  Rate   │
  │  Agent  │   │  Agent  │   │  Limit  │
  └────┬────┘   └────┬────┘   └────┬────┘
       │              │              │
       ▼              ▼              ▼
   Decision       Decision       Decision
       │              │              │
       └──────────────┼──────────────┘
                      │
                      ▼
              ┌────────────────┐
              │   Aggregate    │
              │   Decisions    │
              └───────┬────────┘
                      │
         ┌────────────┼────────────┐
         │            │            │
         ▼            ▼            ▼
      ALLOW        BLOCK       REDIRECT
         │            │            │
         ▼            ▼            ▼
     Continue     Return       Return
     to upstream  error        redirect
```

### Agent Request

```json
{
  "event_type": "request_headers",
  "correlation_id": "abc-123",
  "request_id": "req-456",
  "metadata": {
    "client_ip": "192.168.1.100",
    "client_port": 54321,
    "method": "POST",
    "path": "/api/users",
    "host": "api.example.com"
  },
  "headers": [
    {"name": "content-type", "value": "application/json"},
    {"name": "authorization", "value": "Bearer eyJ..."}
  ]
}
```

### Agent Response

```json
{
  "decision": "allow",
  "header_mutations": {
    "request": {
      "set": {"X-User-Id": "user-789"},
      "remove": ["Authorization"]
    },
    "response": {
      "set": {"X-RateLimit-Remaining": "99"}
    }
  },
  "metadata": {
    "auth_method": "jwt",
    "user_role": "admin"
  },
  "audit": {
    "rules_matched": ["auth-jwt-valid"],
    "processing_time_us": 1234
  }
}
```

### Timeout and Failure Handling

```
Agent call started
       │
       ├─── timeout_ms exceeded ───▶ Timeout!
       │                                 │
       │                         ┌───────┴───────┐
       │                         │               │
       ▼                         ▼               ▼
   Response               fail-closed       fail-open
   received                    │               │
       │                       ▼               ▼
       │                  Block request   Allow request
       │                  (503 error)     (continue)
       │
       ▼
  Process decision
```

## Phase 6: Upstream Selection

### Load Balancing

Sentinel selects a backend server from the upstream pool:

```
Upstream Pool: "backend"
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Server A   │  │  Server B   │  │  Server C   │         │
│  │ 10.0.0.1:80 │  │ 10.0.0.2:80 │  │ 10.0.0.3:80 │         │
│  │             │  │             │  │             │         │
│  │ weight: 5   │  │ weight: 3   │  │ weight: 2   │         │
│  │ healthy: ✓  │  │ healthy: ✓  │  │ healthy: ✗  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│        │                │                                   │
│        └────────────────┘                                   │
│               │                                             │
│               ▼                                             │
│      Load Balancer (round_robin)                           │
│               │                                             │
│               ▼                                             │
│         Selected: Server A                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Health Filtering

Unhealthy servers are excluded:

| Check Type | Mechanism | Action |
|------------|-----------|--------|
| **Active** | Periodic HTTP probes | Mark unhealthy after N failures |
| **Passive** | Real traffic errors | Mark unhealthy on connection failures |
| **Circuit Breaker** | Error rate threshold | Temporarily exclude |

### Connection Pooling

Sentinel reuses connections to upstreams:

```
┌────────────────────────────────────────┐
│          Connection Pool               │
│  ┌──────────────────────────────────┐  │
│  │  Idle Connections                │  │
│  │  ┌────┐ ┌────┐ ┌────┐           │  │
│  │  │Conn│ │Conn│ │Conn│           │  │
│  │  │ #1 │ │ #2 │ │ #3 │           │  │
│  │  └────┘ └────┘ └────┘           │  │
│  └──────────────────────────────────┘  │
│                                        │
│  Request arrives:                      │
│  1. Check for idle connection          │
│  2. If available, reuse               │
│  3. If not, create new (up to limit)  │
│  4. If at limit, queue or reject      │
└────────────────────────────────────────┘
```

## Phase 7: Upstream Communication

### Request Forwarding

The request is sent to the selected upstream:

```
Original Request          Modified Request (to upstream)
┌──────────────────┐      ┌──────────────────────────────┐
│ POST /api/users  │      │ POST /api/users HTTP/1.1     │
│ Host: api.ex.com │  ──▶ │ Host: api.example.com        │
│ Auth: Bearer ... │      │ X-Correlation-Id: abc-123    │
└──────────────────┘      │ X-Forwarded-For: 192.168.1.1 │
                          │ X-Forwarded-Proto: https     │
                          │ X-Forwarded-By: Sentinel     │
                          │ X-User-Id: user-789          │ ◀── From agent
                          │ Content-Type: application/json│
                          │                              │
                          │ {"name": "Alice", ...}       │
                          └──────────────────────────────┘
```

### Added Headers

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Correlation-Id` | Trace ID | Distributed tracing |
| `X-Forwarded-For` | Client IP | Original client address |
| `X-Forwarded-Proto` | `http`/`https` | Original protocol |
| `X-Forwarded-Host` | Original host | Original Host header |
| `X-Forwarded-By` | `Sentinel` | Proxy identification |

### Retry Logic

On upstream failure, retries may occur:

```
Attempt 1: Server A
     │
     ├─── Success ───▶ Continue to response
     │
     ├─── Failure (connection refused)
     │         │
     │         ▼
     │    Wait (exponential backoff)
     │    100ms × 2^(attempt-1)
     │         │
     │         ▼
Attempt 2: Server B (different server)
     │
     ├─── Success ───▶ Continue to response
     │
     ├─── Failure
     │         │
     │         ▼
Attempt 3: Server A (back to healthy server)
     │
     └─── Final failure ───▶ Return 502/504
```

**Retry configuration:**

```kdl
routes {
    route "api" {
        retry-policy {
            max-attempts 3
            retry-on "connection_error" "5xx"
            backoff-ms 100
        }
    }
}
```

## Phase 8: Response Processing

### Upstream Response Received

```
┌─────────────────────────────────────────────────────────────┐
│                    Upstream Response                         │
├─────────────────────────────────────────────────────────────┤
│  HTTP/1.1 200 OK                         ◀── Status Line    │
│  Content-Type: application/json          ◀── Headers        │
│  X-Request-Id: upstream-456                                 │
│  Cache-Control: no-cache                                    │
│                                                              │
│  {"id": 123, "name": "Alice", ...}       ◀── Body          │
└─────────────────────────────────────────────────────────────┘
```

### Response Filter

Sentinel processes the response before sending to client:

```rust
async fn response_filter(&self, upstream_response: &mut ResponseHeader) {
    // 1. Add security headers
    upstream_response.insert_header("X-Content-Type-Options", "nosniff");
    upstream_response.insert_header("X-Frame-Options", "DENY");
    upstream_response.insert_header("X-XSS-Protection", "1; mode=block");
    upstream_response.insert_header("Referrer-Policy", "strict-origin-when-cross-origin");

    // 2. Remove server identification
    upstream_response.remove_header("Server");
    upstream_response.remove_header("X-Powered-By");

    // 3. Add correlation ID
    upstream_response.insert_header("X-Correlation-Id", &ctx.trace_id);

    // 4. Apply agent response mutations
    for (name, value) in agent_response.header_mutations.response.set {
        upstream_response.insert_header(&name, &value);
    }
}
```

### Security Headers Added

| Header | Value | Protection |
|--------|-------|------------|
| `X-Content-Type-Options` | `nosniff` | MIME type sniffing |
| `X-Frame-Options` | `DENY` | Clickjacking |
| `X-XSS-Protection` | `1; mode=block` | XSS attacks |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Referrer leakage |

### Headers Removed

| Header | Reason |
|--------|--------|
| `Server` | Hide upstream technology |
| `X-Powered-By` | Hide framework information |

## Phase 9: Response Delivery

### Streaming to Client

Responses are streamed as they arrive:

```
Upstream                    Sentinel                    Client
   │                           │                           │
   │── Headers ───────────────▶│                           │
   │                           │── Headers ───────────────▶│
   │                           │                           │
   │── Body chunk 1 ──────────▶│                           │
   │                           │── Body chunk 1 ──────────▶│
   │                           │                           │
   │── Body chunk 2 ──────────▶│                           │
   │                           │── Body chunk 2 ──────────▶│
   │                           │                           │
   │── Body chunk N (final) ──▶│                           │
   │                           │── Body chunk N (final) ──▶│
   │                           │                           │
```

This streaming approach:
- Minimizes memory usage (no full buffering)
- Reduces time-to-first-byte (TTFB)
- Handles large responses efficiently

### Error Responses

When errors occur, Sentinel generates appropriate responses:

| Condition | Status | Response |
|-----------|--------|----------|
| No route matched | 404 | Not Found |
| Agent blocked | 403 | Forbidden |
| Agent redirect | 302/307 | Redirect |
| Upstream timeout | 504 | Gateway Timeout |
| Upstream refused | 502 | Bad Gateway |
| All upstreams down | 503 | Service Unavailable |
| Rate limited | 429 | Too Many Requests |

## Phase 10: Logging and Metrics

### Access Log Entry

After the response is sent:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "trace_id": "abc-123",
  "instance_id": "sentinel-pod-xyz",
  "client_ip": "192.168.1.100",
  "method": "POST",
  "path": "/api/users",
  "query": "version=2",
  "host": "api.example.com",
  "status": 200,
  "body_bytes": 1234,
  "duration_ms": 45,
  "route_id": "api-users",
  "upstream": "backend",
  "upstream_attempts": 1,
  "user_agent": "Mozilla/5.0...",
  "referer": "https://example.com/"
}
```

### Metrics Updated

```
# Request counter
sentinel_requests_total{route="api-users",method="POST",status="200"} 1

# Latency histogram
sentinel_request_duration_seconds_bucket{route="api-users",le="0.05"} 1
sentinel_request_duration_seconds_bucket{route="api-users",le="0.1"} 1

# Upstream metrics
sentinel_upstream_requests_total{upstream="backend",status="200"} 1
sentinel_upstream_latency_seconds_bucket{upstream="backend",le="0.05"} 1

# Agent metrics
sentinel_agent_requests_total{agent="auth-agent",decision="allow"} 1
sentinel_agent_latency_seconds_bucket{agent="auth-agent",le="0.01"} 1
```

### Request Complete

Finally, the reload coordinator is notified:

```rust
// In logging() callback
self.reload_coordinator.dec_requests();
```

This enables graceful shutdown - Sentinel waits for all in-flight requests to complete before stopping.

## Complete Timeline

```
Time    Event
─────   ─────────────────────────────────────────────────
0ms     TCP connection accepted
2ms     TLS handshake complete (HTTPS)
3ms     HTTP request headers received
3ms     Trace ID assigned: abc-123
4ms     Limits checked (headers count, size)
4ms     Route matched: api-users
5ms     Agent: auth-agent called
15ms    Agent: auth-agent responded (ALLOW)
16ms    Agent: waf-agent called
25ms    Agent: waf-agent responded (ALLOW)
26ms    Upstream selected: backend-1 (10.0.0.1:80)
27ms    Connection acquired from pool
28ms    Request forwarded to upstream
65ms    Upstream response headers received
66ms    Security headers added
66ms    Response headers sent to client
70ms    Response body streamed
75ms    Response complete
75ms    Access log written
75ms    Metrics updated
75ms    Request counter decremented
─────   ─────────────────────────────────────────────────
Total:  75ms (client perspective)
```

## Next Steps

- [Routing System](../routing/) - Deep dive into route matching
- [Pingora Foundation](../pingora/) - Underlying framework
- [Agents](/agents/) - External processing details
