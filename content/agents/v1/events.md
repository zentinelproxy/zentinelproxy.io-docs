+++
title = "Events & Hooks"
weight = 2
+++

Agents receive events at key points in the request/response lifecycle. Each event carries relevant data and expects a response with a decision and optional mutations.

## Event Overview

| Event | Phase | Can Block | Can Mutate | Use Cases |
|-------|-------|-----------|------------|-----------|
| `configure` | Startup | Yes | None | Agent configuration |
| `request_headers` | Request | Yes | Request headers | Auth, routing, early blocking |
| `request_body` | Request | Yes | Request headers | WAF inspection, content validation |
| `response_headers` | Response | No | Response headers | Header injection, caching hints |
| `response_body` | Response | No | Response headers | Content filtering, transformation |
| `request_complete` | Logging | No | None | Audit logging, metrics |

## Event Lifecycle

```
┌─────────────────────────────────────────────────────────────────────┐
│                        REQUEST PHASE                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Client ──▶ [request_headers] ──▶ [request_body] ──▶ Upstream       │
│                    │                    │                            │
│               Decision:            Decision:                         │
│            ALLOW/BLOCK/REDIRECT   ALLOW/BLOCK                        │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                       RESPONSE PHASE                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Client ◀── [response_headers] ◀── [response_body] ◀── Upstream     │
│                    │                    │                            │
│               Mutations:           Mutations:                        │
│            Add/Set/Remove headers  Add/Set/Remove headers            │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                        LOGGING PHASE                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│              [request_complete] ──▶ Audit Log                        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Configure Event

**Event Type:** `configure`

Sent once when the agent connects to the proxy, before any request events. This allows agents to receive configuration from the KDL config file instead of relying solely on CLI arguments.

### Payload

```rust
struct ConfigureEvent {
    agent_id: String,           // Agent identifier from config
    config: serde_json::Value,  // Configuration as JSON object
}
```

### Configuration Source

The configuration comes from the `config` block in KDL:

```kdl
agent "waf" type="waf" {
    unix-socket "/var/run/sentinel/waf.sock"
    events "request_headers" "request_body"
    config {
        paranoia-level 2
        sqli #true
        xss #true
        exclude-paths "/health" "/metrics"
    }
}
```

This becomes:

```json
{
  "agent_id": "waf",
  "config": {
    "paranoia-level": 2,
    "sqli": true,
    "xss": true,
    "exclude-paths": ["/health", "/metrics"]
  }
}
```

### Use Cases

- **Dynamic Configuration:** Apply settings without restarting the agent
- **Centralized Config:** Keep all configuration in one KDL file
- **Environment-Specific Settings:** Different configs for dev/staging/prod

### Example Response

```json
{
  "version": 1,
  "decision": {"allow": {}},
  "audit": {
    "tags": ["configured"],
    "custom": {"paranoia_level": "2"}
  }
}
```

### Rejecting Configuration

If the configuration is invalid, the agent can reject it:

```json
{
  "version": 1,
  "decision": {
    "block": {
      "status": 500,
      "body": "Invalid config: paranoia-level must be 1-4"
    }
  }
}
```

When configuration is rejected, the proxy will not start routing traffic to that agent.

### KDL to JSON Conversion

| KDL | JSON |
|-----|------|
| `paranoia-level 2` | `{"paranoia-level": 2}` |
| `sqli #true` | `{"sqli": true}` |
| `paths "/a" "/b"` | `{"paths": ["/a", "/b"]}` |
| `nested { key "val" }` | `{"nested": {"key": "val"}}` |

## Request Headers Event

**Event Type:** `request_headers`

The most commonly used event. Sent when HTTP headers are received from the client, before the body is read.

### Payload

```rust
struct RequestHeadersEvent {
    metadata: RequestMetadata,
    method: String,         // "GET", "POST", etc.
    uri: String,            // "/api/users?page=1"
    headers: HashMap<String, Vec<String>>,
}

struct RequestMetadata {
    correlation_id: String,   // Unique request identifier
    request_id: String,       // Internal request ID
    client_ip: String,        // Client IP address
    client_port: u16,         // Client port
    server_name: Option<String>,  // SNI or Host header
    protocol: String,         // "HTTP/1.1", "HTTP/2"
    tls_version: Option<String>,  // "TLSv1.3"
    tls_cipher: Option<String>,   // Cipher suite
    route_id: Option<String>,     // Matched route ID
    upstream_id: Option<String>,  // Target upstream
    timestamp: String,        // RFC3339 timestamp
}
```

### Use Cases

- **Authentication:** Validate JWT tokens, API keys, session cookies
- **Authorization:** Check permissions based on path and headers
- **Rate Limiting:** Count requests per client/route
- **Routing Decisions:** Modify routing metadata
- **Early Blocking:** Reject malformed or suspicious requests

### Example Response

```json
{
  "version": 1,
  "decision": {"allow": {}},
  "request_headers": [
    {"set": {"name": "X-User-Id", "value": "user-123"}},
    {"set": {"name": "X-Authenticated", "value": "true"}}
  ],
  "audit": {
    "tags": ["auth", "jwt"],
    "custom": {"user_id": "user-123"}
  }
}
```

## Request Body Event

**Event Type:** `request_body`

Sent when request body chunks are received. Requires `request_body` in the agent's event list and appropriate body limits configured.

### Payload

```rust
struct RequestBodyChunkEvent {
    correlation_id: String,
    data: String,           // Body chunk (base64 for binary)
    is_last: bool,          // True if final chunk
    total_size: Option<usize>,  // Total body size if known
}
```

### Configuration

```kdl
agent "waf" type="waf" {
    grpc "http://localhost:50051"
    events "request_headers" "request_body"
    max-request-body-bytes 1048576  // Limit to 1MB
}
```

### Use Cases

- **WAF Inspection:** Scan for SQL injection, XSS, command injection
- **Content Validation:** Verify JSON schema, file types
- **Size Limits:** Enforce body size restrictions
- **Malware Scanning:** Check uploaded files

### Body Decompression

When `decompress: true` is set in the WAF `body-inspection` config, Sentinel automatically decompresses request bodies before sending to agents:

```kdl
waf {
    body-inspection {
        inspect-request-body #true
        decompress #true
        max-decompression-ratio 100.0  // Zip bomb protection
    }
}
```

Supported encodings: `gzip`, `deflate`, `br` (Brotli)

The decompression ratio limit protects against zip bombs by rejecting payloads where the decompressed size exceeds the compressed size by more than the configured ratio.

### Important Notes

- Body inspection adds latency - use only when necessary
- Set `max-request-body-bytes` to limit memory usage
- Streaming bodies may arrive in multiple chunks
- Enable `decompress` to inspect compressed payloads (e.g., gzipped JSON)
- Use `max-decompression-ratio` to protect against zip bomb attacks

## Response Headers Event

**Event Type:** `response_headers`

Sent when response headers are received from the upstream, before the body.

### Payload

```rust
struct ResponseHeadersEvent {
    correlation_id: String,
    status: u16,            // HTTP status code
    headers: HashMap<String, Vec<String>>,
}
```

### Use Cases

- **Header Injection:** Add security headers, CORS headers
- **Caching Hints:** Modify cache-control headers
- **Response Logging:** Record upstream response status
- **Header Removal:** Strip internal headers

### Example Response

```json
{
  "version": 1,
  "decision": {"allow": {}},
  "response_headers": [
    {"set": {"name": "X-Frame-Options", "value": "DENY"}},
    {"set": {"name": "X-Content-Type-Options", "value": "nosniff"}},
    {"remove": {"name": "X-Powered-By"}}
  ]
}
```

## Response Body Event

**Event Type:** `response_body`

Sent when response body chunks are received from the upstream.

### Payload

```rust
struct ResponseBodyChunkEvent {
    correlation_id: String,
    data: String,           // Body chunk (base64 for binary)
    is_last: bool,
    total_size: Option<usize>,
}
```

### Configuration

```kdl
agent "content-filter" type="custom" {
    unix-socket "/tmp/filter.sock"
    events "response_body"
    max-response-body-bytes 5242880  // Limit to 5MB
}
```

### Use Cases

- **Content Filtering:** Redact sensitive data
- **Response Transformation:** Modify response content
- **DLP (Data Loss Prevention):** Detect sensitive data leakage
- **Logging:** Record response content for audit

## Request Complete Event

**Event Type:** `request_complete` (also known as `log`)

Sent after the response has been sent to the client. This is a **fire-and-forget** event for logging and audit purposes.

### Payload

```rust
struct RequestCompleteEvent {
    correlation_id: String,
    status: u16,                // Final HTTP status
    duration_ms: u64,           // Total request duration
    request_body_size: usize,   // Bytes received
    response_body_size: usize,  // Bytes sent
    upstream_attempts: u32,     // Retry count
    error: Option<String>,      // Error message if failed
}
```

### Use Cases

- **Audit Logging:** Record all requests for compliance
- **Metrics Collection:** Track latency, status codes, sizes
- **Alerting:** Trigger alerts on errors or anomalies
- **Analytics:** Feed data to analytics systems

### Example Response

The response decision is ignored for this event, but audit metadata is still collected:

```json
{
  "version": 1,
  "decision": {"allow": {}},
  "audit": {
    "tags": ["api", "success"],
    "rule_ids": [],
    "custom": {
      "response_time_bucket": "fast",
      "cache_hit": "false"
    }
  }
}
```

## Agent Decisions

Agents return one of these decisions:

| Decision | Description | Applicable Events |
|----------|-------------|-------------------|
| `allow` | Continue processing | All |
| `block` | Reject with status code and optional body | `request_headers`, `request_body` |
| `redirect` | Redirect to URL | `request_headers` |
| `challenge` | Present challenge (CAPTCHA, etc.) | `request_headers` |

### Block Response

```json
{
  "decision": {
    "block": {
      "status": 403,
      "body": "Access Denied",
      "headers": {"X-Block-Reason": "rate-limit"}
    }
  }
}
```

### Redirect Response

```json
{
  "decision": {
    "redirect": {
      "url": "https://login.example.com/auth",
      "status": 302
    }
  }
}
```

## Header Mutations

Agents can mutate headers using these operations:

| Operation | Description |
|-----------|-------------|
| `set` | Set header value (replaces if exists) |
| `add` | Add header value (appends if exists) |
| `remove` | Remove header entirely |

```json
{
  "request_headers": [
    {"set": {"name": "X-Forwarded-User", "value": "alice"}},
    {"add": {"name": "X-Request-Tag", "value": "processed"}},
    {"remove": {"name": "X-Internal-Token"}}
  ],
  "response_headers": [
    {"set": {"name": "Cache-Control", "value": "no-store"}}
  ]
}
```

## Audit Metadata

Every response can include audit metadata for logging and observability:

```json
{
  "audit": {
    "tags": ["waf", "blocked", "sqli"],
    "rule_ids": ["942100", "942110"],
    "confidence": 0.95,
    "reason_codes": ["SQL_INJECTION_DETECTED"],
    "custom": {
      "matched_pattern": "' OR 1=1",
      "source_field": "query_param:id"
    }
  }
}
```

| Field | Description |
|-------|-------------|
| `tags` | Searchable tags for filtering logs |
| `rule_ids` | IDs of rules that matched (e.g., CRS rules) |
| `confidence` | Confidence score (0.0 - 1.0) |
| `reason_codes` | Machine-readable reason codes |
| `custom` | Arbitrary key-value metadata |
