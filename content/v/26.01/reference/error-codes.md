+++
title = "Error Codes"
weight = 3
+++

HTTP status codes and error responses returned by Sentinel.

## HTTP Status Codes

### Client Errors (4xx)

| Code | Error Type | Description |
|------|------------|-------------|
| 400 | `RequestValidation` | Malformed request or invalid input |
| 400 | `Parse` | Request parsing failed |
| 401 | `AuthenticationFailed` | Authentication required or invalid credentials |
| 403 | `AuthorizationFailed` | Insufficient permissions |
| 403 | `WafBlocked` | Request blocked by WAF rules |
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

### JSON Format (API routes)

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded",
    "correlation_id": "2kF8xQw4BnM",
    "retry_after": 60
  }
}
```

### HTML Format (Web routes)

```html
<!DOCTYPE html>
<html>
<head><title>429 Too Many Requests</title></head>
<body>
<h1>Too Many Requests</h1>
<p>Rate limit exceeded. Please retry after 60 seconds.</p>
<p>Request ID: 2kF8xQw4BnM</p>
</body>
</html>
```

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
HTTP 503. All upstream servers failed health checks.

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
grep "2kF8xQw4BnM" /var/log/sentinel/access.log
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
sentinel_requests_total{route="api", status="502"}
sentinel_upstream_failures_total{upstream="backend", reason="connection_refused"}
sentinel_blocked_requests_total{reason="waf"}
sentinel_circuit_breaker_state{component="upstream", route="api"}
```

## See Also

- [Metrics Reference](../metrics/) - Prometheus metrics
- [Limits Configuration](../../configuration/limits/) - Configure limits
