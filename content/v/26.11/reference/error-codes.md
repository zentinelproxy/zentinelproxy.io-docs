+++
title = "Error Codes"
weight = 3
updated = 2026-10-20
+++

HTTP status codes and error responses returned by Zentinel.

## HTTP Status Codes

### Client Errors (4xx)

| Code | Error Type | Description |
|------|------------|-------------|
| 400 | `RequestValidation` | Malformed request or invalid input |
| 400 | `Parse` | Request parsing failed |
| 401 | `AuthenticationFailed` | Authentication required or invalid credentials |
| 403 | `AuthorizationFailed` | Insufficient permissions |
| 403 | `WafBlocked` | Request blocked by WAF rules |
| 404 | — | No route matches the request |
| 413 | — | Request body over the effective `max-body-size` (from 26.10_5; `500` before) |
| 429 | `LimitExceeded` | Rate limit or resource limit exceeded |
| 429 | `RateLimit` | Rate limit exceeded |
| 495 | `Tls` | TLS/SSL certificate error |

### Server Errors (5xx)

| Code | Error Type | Description |
|------|------------|-------------|
| 500 | `Config` | Configuration error |
| 500 | `Agent` | Agent communication error |
| 500 | `Internal` | Internal server error |
| 500 | `Io` | I/O operation failed |
| 502 | `Upstream` | Upstream server error |
| 502 | `ResponseValidation` | Invalid response from upstream |
| 503 | `ServiceUnavailable` | Service temporarily unavailable |
| 503 | `CircuitBreakerOpen` | Circuit breaker tripped |
| 503 | `NoHealthyUpstream` | No healthy upstream servers |
| 504 | `Timeout` | Gateway timeout |

## Error Response Format

The body depends on where the error came from; see
[Error Pages](/configuration/routes/#error-pages) for the full table. From
26.10_6 a route can set its own page for chosen statuses with `error-pages`,
which replaces both the upstream's and the proxy's response for that status.
From 26.10_7 it also replaces the proxy's refusals on that route (rate limits,
`max-in-flight-requests`, geo and prompt-injection blocks, WebSocket not
enabled, no usable upstream, agent blocks without their own body), keeping
their `Retry-After` and `X-RateLimit-*` headers.
Without a page, errors the proxy generates itself (unreachable upstream,
timeout, no healthy target, no matching route, request body too large) look the
same on every route type:

```http
HTTP/1.1 503 Service Unavailable
Content-Type: application/json
X-Correlation-Id: V9ZSZT2h6Ug

{"error":"503 Service Unavailable","trace_id":"V9ZSZT2h6Ug"}
```

The `error` field is the status code followed by its standard reason phrase,
for example `"404 Not Found"` or `"413 Payload Too Large"`. The no-route `404`
carries a trace ID like every other error. Before 26.10_5, statuses other than
400, 502, 503 and 504 were labelled "Internal Server Error" (`"404 Internal
Server Error"`), and the no-route `404` had an empty `trace_id`.

A rate-limit filter answers `429` with `Content-Type: text/plain; charset=utf-8`,
the body `Rate limit exceeded`, and `X-RateLimit-Limit`, `X-RateLimit-Remaining`,
`X-RateLimit-Reset` and `Retry-After` headers. A request over
`max-in-flight-requests` gets the JSON body above with status `503` and
`Retry-After: 1`. An agent that blocks with a body of its own sends that body
as `text/plain`, whatever the route's pages say.

When the upstream itself answers `4xx`/`5xx`, the client gets the upstream's
response unchanged: status, headers including `Content-Type`, and body. Before
26.10_5 the body was kept but `Content-Type` was replaced
(`text/html; charset=utf-8` on web routes).

## Error Types

### Configuration Errors

**Config**
```
Configuration error: {message}
```
HTTP 500. Invalid or missing configuration. Check config file syntax and validation.

### Upstream Errors

**Upstream**
```
Upstream error: {upstream} - {message}
```
HTTP 502. Failed to connect to or receive response from upstream.

**NoHealthyUpstream**
```
No healthy upstream available
```
HTTP 503. Every target of the upstream is failing its health check, so none is
in rotation. From 26.10_5; before, failing targets kept receiving traffic.

### Agent Errors

**Agent**
```
Agent error: {agent} - {message}
```
HTTP 500. Agent communication failed. Check agent is running and accessible.

### Validation Errors

**RequestValidation**
```
Request validation failed: {reason}
```
HTTP 400. Invalid request format, headers, or body.

**ResponseValidation**
```
Response validation failed: {reason}
```
HTTP 502. Upstream returned invalid response.

### Limit Errors

**LimitExceeded**
```
Limit exceeded: {limit_type} - Current value {current} exceeds limit {limit}
```
HTTP 429. Request exceeded configured limits.

Limit types:
- `header_size` - Total headers too large
- `header_count` - Too many headers
- `body_size` - Request body too large
- `request_rate` - Rate limit exceeded
- `connection_count` - Connection limit reached
- `in_flight_requests` - Too many concurrent requests
- `decompression_size` - Decompressed body too large
- `buffer_size` - Buffer limit exceeded
- `queue_depth` - Request queue full

These are the error type's categories. A request body over `max-body-size` is
answered `413 Payload Too Large`. From 26.10_6 a request over
`max-in-flight-requests` is answered `503` with `Retry-After: 1`, and a
connection over a connection limit is closed (see
[Limits](/configuration/limits/#concurrency-limits)).

**RateLimit**
```
Rate limit exceeded: {message}
```
HTTP 429. Rate limit exceeded with retry information.

### Timeout Errors

**Timeout**
```
Timeout: {operation} after {duration}ms
```
HTTP 504. Operation timed out.

### Circuit Breaker Errors

**CircuitBreakerOpen**
```
Circuit breaker open: {component}
```
HTTP 503. Circuit breaker tripped due to consecutive failures.

### Security Errors

**WafBlocked**
```
WAF blocked request: {reason}
```
HTTP 403. Request blocked by WAF rules.

**AuthenticationFailed**
```
Authentication failed: {reason}
```
HTTP 401. Invalid or missing authentication.

**AuthorizationFailed**
```
Authorization failed: {reason}
```
HTTP 403. Insufficient permissions.

### TLS Errors

**Tls**
```
TLS error: {message}
```
HTTP 495. TLS handshake or certificate error.

### Service Unavailable

**ServiceUnavailable**
```
Service unavailable: {service}
```
HTTP 503. Service temporarily unavailable.

## Response Headers

Error responses include these headers:

| Header | Description |
|--------|-------------|
| `X-Correlation-Id` | Request correlation ID for debugging |
| `Retry-After` | Seconds to wait before retrying (rate limits) |
| `X-RateLimit-Limit` | Request limit per window |
| `X-RateLimit-Remaining` | Remaining requests in window |
| `X-RateLimit-Reset` | Unix timestamp when limit resets |

## Correlation IDs

Every request receives a correlation ID for tracing:

- Appears in `X-Correlation-Id` response header
- Included in error responses
- Logged with all related log entries
- Passed to upstream servers

Use correlation IDs when reporting issues:

```bash
curl -i https://api.example.com/endpoint
# X-Correlation-Id: 2kF8xQw4BnM

# Search logs by correlation ID
grep "2kF8xQw4BnM" /var/log/zentinel/access.log
```

## Client-Safe Messages

Error responses to clients are sanitized to avoid leaking internal details:

| Internal Error | Client Message |
|----------------|----------------|
| Database connection failed | Internal server error |
| Agent timeout on auth check | Internal server error |
| Upstream SSL verification failed | Bad gateway |
| Config parsing failed | Internal server error |

Full error details appear in server logs with the correlation ID.

## Retry Behavior

Errors that may be retried:

| Error Type | Retryable | Notes |
|------------|-----------|-------|
| Upstream (retryable flag) | Yes | Connection errors, 502/503/504 |
| Timeout | Yes | Retry with backoff |
| ServiceUnavailable | Yes | Check Retry-After header |
| RateLimit | Yes | Wait for Retry-After |
| CircuitBreakerOpen | No | Wait for circuit to close |
| RequestValidation | No | Fix request |
| AuthenticationFailed | No | Fix credentials |

## Logging

Errors are logged with structured fields:

```json
{
  "level": "ERROR",
  "timestamp": "2025-01-15T10:30:00Z",
  "correlation_id": "2kF8xQw4BnM",
  "error_type": "Upstream",
  "http_status": 502,
  "message": "Upstream error: backend - connection refused",
  "upstream": "backend",
  "route": "api",
  "client_ip": "10.0.0.5",
  "duration_ms": 5023
}
```

## Metrics

Error-related metrics:

```
zentinel_requests_total{route="api", status="502"}
zentinel_upstream_failures_total{upstream="backend", reason="connection_refused"}
zentinel_blocked_requests_total{reason="waf"}
zentinel_circuit_breaker_state{component="upstream", route="api"}
```

## See Also

- [Metrics Reference](../metrics/) - Prometheus metrics
- [Limits Configuration](../../configuration/limits/) - Configure limits
