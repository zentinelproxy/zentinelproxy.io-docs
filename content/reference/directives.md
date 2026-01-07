+++
title = "Directive Index"
weight = 1
description = "Complete reference for all Sentinel configuration directives"
+++

Complete reference for all Sentinel configuration directives. Each entry includes syntax, context, default values, and usage examples.

---

### `add`

Adds a header to the request or response without removing existing values. If the header already exists, the new value is appended.

**Context:** `request-headers`, `response-headers`

```kdl
policies {
    request-headers {
        add { "X-Request-ID" "abc123" }
    }
    response-headers {
        add { "X-Served-By" "sentinel" }
    }
}
```

See also: [`set`](#set), [`remove`](#remove)

---

### `address`

Specifies the network address to bind (for listeners) or connect to (for upstream targets). Format is `host:port` where host can be an IP address or `0.0.0.0` to bind all interfaces.

**Context:** `listener`, `target`

```kdl
listener "http" {
    address "0.0.0.0:8080"
}

target {
    address "10.0.1.5:3000"
}
```

---

### `agent`

Defines an external processing agent that can intercept and modify requests/responses. Agents communicate via Unix sockets or gRPC and can implement authentication, rate limiting, WAF, or custom logic.

**Context:** `agents`

```kdl
agents {
    agent "auth" {
        type "auth"
        transport "unix_socket" { path "/var/run/auth-agent.sock" }
        timeout-ms 50
        failure-mode "closed"
        events "on_request_headers"
    }
}
```

See: [Agent Configuration](@/configuration/agents.md)

---

### `agents`

Top-level block containing all agent definitions. Agents are external services that process requests at various lifecycle points.

**Context:** root

```kdl
agents {
    agent "auth" { }
    agent "ratelimit" { }
}
```

---

### `auto-reload`

When enabled, Sentinel watches the configuration file for changes and automatically reloads when modifications are detected. Uses filesystem notifications for efficiency.

**Context:** `system`
**Default:** `#false`

```kdl
system {
    auto-reload #true
}
```

---

### `backoff-base-ms`

Initial delay in milliseconds before the first retry attempt. Subsequent retries use exponential backoff starting from this value.

**Context:** `retry-policy`
**Default:** `100`

```kdl
retry-policy {
    backoff-base-ms 200
    backoff-max-ms 5000
}
```

---

### `backoff-max-ms`

Maximum delay in milliseconds between retry attempts. The exponential backoff will not exceed this value regardless of retry count.

**Context:** `retry-policy`
**Default:** `10000`

```kdl
retry-policy {
    backoff-base-ms 100
    backoff-max-ms 3000
}
```

---

### `buffer-requests`

When enabled, Sentinel reads the entire request body into memory before forwarding to the upstream. Required for request body inspection or when the upstream doesn't support chunked encoding.

**Context:** `policies`
**Default:** `#false`

```kdl
policies {
    buffer-requests #true
    max-body-size "5MB"
}
```

---

### `buffer-responses`

When enabled, Sentinel reads the entire response body into memory before sending to the client. Useful for response transformation or when consistent Content-Length headers are required.

**Context:** `policies`
**Default:** `#false`

```kdl
policies {
    buffer-responses #true
}
```

---

### `builtin-handler`

Specifies a built-in handler for the route instead of proxying to an upstream. Available handlers: `health` (health check endpoint), `metrics` (Prometheus metrics), `ready` (readiness probe).

**Context:** `route`

```kdl
route "health" {
    matches { path "/health" }
    service-type "builtin"
    builtin-handler "health"
}
```

---

### `burst`

Maximum number of requests allowed to exceed the rate limit in a short period. Allows temporary spikes while maintaining the average rate over time.

**Context:** `rate-limit`
**Default:** `0`

```kdl
rate-limit {
    requests-per-second 100
    burst 500
    key "client_ip"
}
```

---

### `ca-cert`

Path to CA certificate file for verifying upstream server certificates. Used when connecting to upstreams over TLS with custom or private CAs.

**Context:** `tls` (upstream)

```kdl
upstream "backend" {
    tls {
        ca-cert "/etc/sentinel/ca.pem"
    }
}
```

---

### `ca-file`

Path to CA certificate file for verifying client certificates. Required when `client-auth` is enabled for mutual TLS (mTLS) authentication.

**Context:** `tls` (listener)

```kdl
listener "https" {
    tls {
        cert-file "/etc/sentinel/server.crt"
        key-file "/etc/sentinel/server.key"
        ca-file "/etc/sentinel/client-ca.pem"
        client-auth #true
    }
}
```

---

### `cache-control`

Sets the Cache-Control header for static file responses. Controls browser and CDN caching behavior for served files.

**Context:** `static-files`

```kdl
static-files {
    root "/var/www"
    cache-control "public, max-age=86400, immutable"
}
```

---

### `cert-file`

Path to the TLS certificate file in PEM format. For certificate chains, the file should contain the server certificate followed by intermediate certificates.

**Context:** `tls` (listener)

```kdl
listener "https" {
    address "0.0.0.0:443"
    protocol "https"
    tls {
        cert-file "/etc/sentinel/server.crt"
        key-file "/etc/sentinel/server.key"
    }
}
```

---

### `cipher-suites`

Restricts the allowed TLS cipher suites. If not specified, Sentinel uses secure defaults. Format varies by TLS implementation.

**Context:** `tls` (listener)

```kdl
tls {
    cipher-suites "TLS_AES_256_GCM_SHA384,TLS_CHACHA20_POLY1305_SHA256"
}
```

---

### `circuit-breaker`

Configures circuit breaker behavior to prevent cascading failures. When failure threshold is reached, the circuit opens and requests fail fast without attempting the upstream.

**Context:** `route`, `agent`

```kdl
circuit-breaker {
    failure-threshold 5
    success-threshold 2
    timeout-seconds 30
    half-open-max-requests 3
}
```

---

### `client-auth`

Enables mutual TLS (mTLS) requiring clients to present valid certificates signed by the configured CA. Essential for zero-trust architectures.

**Context:** `tls` (listener)
**Default:** `#false`

```kdl
tls {
    cert-file "/etc/sentinel/server.crt"
    key-file "/etc/sentinel/server.key"
    ca-file "/etc/sentinel/client-ca.pem"
    client-auth #true
}
```

---

### `client-cert`

Path to client certificate for mTLS when connecting to upstream servers that require client authentication.

**Context:** `tls` (upstream)

```kdl
upstream "secure-backend" {
    tls {
        client-cert "/etc/sentinel/client.crt"
        client-key "/etc/sentinel/client.key"
    }
}
```

---

### `client-key`

Path to client private key for mTLS when connecting to upstream servers. Must correspond to the `client-cert` certificate.

**Context:** `tls` (upstream)

```kdl
upstream "secure-backend" {
    tls {
        client-cert "/etc/sentinel/client.crt"
        client-key "/etc/sentinel/client.key"
    }
}
```

---

### `compress`

Enables automatic compression (gzip, brotli) for static file responses based on client Accept-Encoding headers and file types.

**Context:** `static-files`
**Default:** `#true`

```kdl
static-files {
    root "/var/www"
    compress #true
}
```

---

### `connect-secs`

Maximum time in seconds to establish a connection to an upstream target. Connections taking longer are aborted and the next target is tried.

**Context:** `timeouts`
**Default:** `10`

```kdl
timeouts {
    connect-secs 5
    request-secs 30
}
```

---

### `connection-pool`

Configures connection pooling to upstream targets. Reusing connections reduces latency and resource usage for high-throughput scenarios.

**Context:** `upstream`

```kdl
upstream "backend" {
    connection-pool {
        max-connections 100
        max-idle 20
        idle-timeout-secs 60
        max-lifetime-secs 3600
    }
}
```

---

### `daemon`

When enabled, Sentinel forks to the background after startup. Typically used with `pid-file` for process management in production deployments.

**Context:** `system`
**Default:** `#false`

```kdl
system {
    daemon #true
    pid-file "/var/run/sentinel.pid"
}
```

---

### `default-format`

Sets the default response format for error pages when the client's Accept header doesn't indicate a preference.

**Context:** `error-pages`
**Default:** `json`

```kdl
error-pages {
    default-format "json"
}
```

---

### `default-route`

Specifies a fallback route ID when no other routes match the request. Useful for catch-all error handling or default backends.

**Context:** `listener`

```kdl
listener "http" {
    address "0.0.0.0:8080"
    protocol "http"
    default-route "fallback"
}
```

---

### `directory-listing`

When enabled, requests to directories without an index file return an HTML directory listing. Generally disabled for security in production.

**Context:** `static-files`
**Default:** `#false`

```kdl
static-files {
    root "/var/www"
    directory-listing #false
}
```

---

### `error-pages`

Configures custom error responses for specific HTTP status codes. Supports JSON, HTML templates, or static files.

**Context:** `route`

```kdl
error-pages {
    default-format "json"
    pages {
        "404" { format "json" message "Resource not found" }
        "500" { format "html" template "/errors/500.html" }
    }
}
```

---

### `events`

Specifies which request lifecycle events the agent should receive. Multiple events can be listed to process requests at different stages.

**Context:** `agent`

Available events: `on_request_headers`, `on_request_body`, `on_response_headers`, `on_response_body`

```kdl
agent "logger" {
    events "on_request_headers" "on_response_headers"
}
```

---

### `expected-status`

The HTTP status code that indicates a healthy upstream. Health checks receiving different status codes mark the target as unhealthy.

**Context:** `health-check` (http)
**Default:** `200`

```kdl
health-check {
    type "http" {
        path "/health"
        expected-status 200
    }
}
```

---

### `failure-mode`

Determines behavior when an agent fails or times out. `closed` rejects the request (fail-safe), `open` allows the request to proceed (fail-open).

**Context:** `policies`, `agent`
**Default:** `closed`

```kdl
agent "ratelimit" {
    failure-mode "open"
}

policies {
    failure-mode "closed"
}
```

---

### `failure-threshold`

Number of consecutive failures before the circuit breaker opens. Once open, requests fail immediately without attempting the upstream.

**Context:** `circuit-breaker`
**Default:** `5`

```kdl
circuit-breaker {
    failure-threshold 10
    timeout-seconds 60
}
```

---

### `fallback`

File to serve when a requested static file doesn't exist. Essential for single-page applications (SPAs) that handle routing client-side.

**Context:** `static-files`

```kdl
static-files {
    root "/var/www/app"
    fallback "index.html"
}
```

---

### `filters`

List of filter IDs to apply to the route in order. Filters can modify requests/responses or short-circuit processing.

**Context:** `route`

```kdl
route "api" {
    filters "auth" "ratelimit" "logging"
    upstream "backend"
}
```

---

### `format`

Response format for an error page. Supports `json` for API responses or `html` for browser-friendly pages.

**Context:** error page entry

```kdl
error-pages {
    pages {
        "404" { format "json" message "Not found" }
    }
}
```

---

### `graceful-shutdown-timeout-secs`

Maximum time in seconds to wait for in-flight requests to complete during shutdown. After this timeout, remaining connections are forcibly closed.

**Context:** `system`
**Default:** `30`

```kdl
system {
    graceful-shutdown-timeout-secs 60
}
```

---

### `group`

Unix group to switch to after binding privileged ports. Used with `user` for dropping privileges in production deployments.

**Context:** `system`

```kdl
system {
    user "sentinel"
    group "sentinel"
}
```

---

### `half-open-max-requests`

Number of requests allowed through when the circuit breaker is in half-open state. Successful requests close the circuit; failures re-open it.

**Context:** `circuit-breaker`
**Default:** `1`

```kdl
circuit-breaker {
    failure-threshold 5
    half-open-max-requests 3
}
```

---

### `header`

Matches requests containing a specific header with an optional value pattern. Useful for routing based on API versions, authentication tokens, or custom headers.

**Context:** `matches`

```kdl
matches {
    header name="X-API-Version" value="v2"
    header name="Authorization"
}
```

---

### `health-check`

Configures active health checking for upstream targets. Unhealthy targets are removed from load balancing until they recover.

**Context:** `upstream`

```kdl
health-check {
    type "http" {
        path "/health"
        expected-status 200
        host "backend.internal"
    }
    interval-secs 10
    timeout-secs 5
    healthy-threshold 2
    unhealthy-threshold 3
}
```

---

### `healthy-threshold`

Number of consecutive successful health checks required to mark an unhealthy target as healthy again.

**Context:** `health-check`
**Default:** `2`

```kdl
health-check {
    healthy-threshold 3
    unhealthy-threshold 2
}
```

---

### `host`

Matches requests with a specific Host header. Supports exact matches and wildcard patterns for multi-tenant or domain-based routing.

**Context:** `matches`

```kdl
matches {
    host "api.example.com"
}

matches {
    host "*.example.com"
}
```

---

### `idle-timeout-secs`

Maximum time in seconds a connection can remain idle in the pool before being closed. Prevents stale connections from consuming resources.

**Context:** `connection-pool`
**Default:** `60`

```kdl
connection-pool {
    max-idle 20
    idle-timeout-secs 120
}
```

---

### `index`

Filename to serve when a directory is requested. Multiple index files can be specified in priority order.

**Context:** `static-files`
**Default:** `index.html`

```kdl
static-files {
    root "/var/www"
    index "index.html"
}
```

---

### `insecure-skip-verify`

Disables TLS certificate verification for upstream connections. **Security risk** — only use for development or when certificates are managed externally.

**Context:** `tls` (upstream)
**Default:** `#false`

```kdl
upstream "dev-backend" {
    tls {
        insecure-skip-verify #true
    }
}
```

---

### `interval-secs`

Time in seconds between health check probes. Shorter intervals detect failures faster but increase network overhead.

**Context:** `health-check`
**Default:** `10`

```kdl
health-check {
    interval-secs 5
    timeout-secs 2
}
```

---

### `keepalive-timeout-secs`

Maximum time in seconds to keep an idle client connection open. Balances connection reuse against resource consumption.

**Context:** `listener`
**Default:** `75`

```kdl
listener "http" {
    keepalive-timeout-secs 120
}
```

---

### `key`

Determines how rate limits are applied. Common keys: `client_ip` (per-IP), `header:X-User-ID` (per-user), or combinations for granular control.

**Context:** `rate-limit`
**Default:** `client_ip`

```kdl
rate-limit {
    requests-per-second 10
    key "client_ip"
}

rate-limit {
    requests-per-second 100
    key "header:X-API-Key"
}
```

---

### `key-file`

Path to the TLS private key file in PEM format. Must be kept secure with restricted file permissions.

**Context:** `tls` (listener)

```kdl
tls {
    cert-file "/etc/sentinel/server.crt"
    key-file "/etc/sentinel/server.key"
}
```

---

### `limits`

Top-level block for global resource limits. Protects against resource exhaustion from malicious or misconfigured clients.

**Context:** root

```kdl
limits {
    max-body-size-bytes 10485760
    max-header-size-bytes 8192
    max-connections-per-client 100
}
```

See: [Limits Configuration](@/configuration/limits.md)

---

### `listener`

Defines a network endpoint that accepts incoming connections. Each listener has its own address, protocol, and TLS configuration.

**Context:** `listeners`

```kdl
listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
    listener "https" {
        address "0.0.0.0:443"
        protocol "https"
        tls {
            cert-file "/etc/sentinel/server.crt"
            key-file "/etc/sentinel/server.key"
        }
    }
}
```

---

### `listeners`

Top-level block containing all listener definitions. At least one listener is required for Sentinel to accept traffic.

**Context:** root

```kdl
listeners {
    listener "main" { }
}
```

---

### `load-balancing`

Algorithm for distributing requests across upstream targets. Choice depends on workload characteristics and backend capabilities.

**Context:** `upstream`
**Default:** `round_robin`

Available: `round_robin`, `least_connections`, `random`, `ip_hash`, `weighted`, `consistent_hash`, `power_of_two_choices`, `adaptive`

```kdl
upstream "backend" {
    load-balancing "least_connections"
}
```

See: [Load Balancing](@/configuration/upstreams.md#load-balancing)

---

### `matches`

Defines conditions for routing requests to this route. Multiple conditions are combined with AND logic; use multiple routes for OR logic.

**Context:** `route`

```kdl
route "api-v2" {
    matches {
        path-prefix "/api/"
        header name="X-API-Version" value="v2"
    }
    upstream "backend-v2"
}
```

---

### `max-attempts`

Maximum number of times to attempt a request including the initial try. Set to 1 to disable retries.

**Context:** `retry-policy`
**Default:** `3`

```kdl
retry-policy {
    max-attempts 5
    retryable-status-codes 502 503 504
}
```

---

### `max-body-bytes`

Maximum request body size in bytes that will be sent to the agent. Larger bodies are truncated or rejected depending on agent configuration.

**Context:** `agent`
**Default:** `1048576` (1MB)

```kdl
agent "waf" {
    max-body-bytes 5242880
}
```

---

### `max-body-size`

Maximum allowed request body size for this route. Requests exceeding this limit receive a 413 Payload Too Large response.

**Context:** `policies`

```kdl
policies {
    max-body-size "10MB"
}
```

---

### `max-body-size-bytes`

Global maximum request body size in bytes. Applied before route-specific limits as a first line of defense.

**Context:** `limits`
**Default:** `10485760` (10MB)

```kdl
limits {
    max-body-size-bytes 52428800
}
```

---

### `max-concurrent-streams`

Maximum number of concurrent HTTP/2 streams per connection. Higher values improve multiplexing but increase memory usage.

**Context:** `listener`
**Default:** `100`

```kdl
listener "https" {
    protocol "h2"
    max-concurrent-streams 250
}
```

---

### `max-connections`

Maximum number of simultaneous connections. In `system` context, this is the global limit. In `connection-pool`, it's per-upstream.

**Context:** `system`, `connection-pool`

```kdl
system {
    max-connections 50000
}

connection-pool {
    max-connections 100
}
```

---

### `max-idle`

Maximum number of idle connections to keep in the pool. Idle connections are ready for immediate reuse without TCP handshake overhead.

**Context:** `connection-pool`
**Default:** `20`

```kdl
connection-pool {
    max-connections 100
    max-idle 30
}
```

---

### `max-lifetime-secs`

Maximum time in seconds a connection can exist before being closed, regardless of activity. Helps with connection rotation and memory management.

**Context:** `connection-pool`
**Default:** `3600` (1 hour)

```kdl
connection-pool {
    max-lifetime-secs 1800
}
```

---

### `max-requests`

Maximum requests to send through this target before rotating to another. Useful for graceful deployments or connection management.

**Context:** `target`

```kdl
target {
    address "10.0.1.1:8080"
    max-requests 10000
}
```

---

### `max-version`

Maximum TLS version to accept. Usually left unset to allow the highest supported version.

**Context:** `tls` (listener)

```kdl
tls {
    min-version "1.2"
    max-version "1.3"
}
```

---

### `message`

Custom message text for an error page. Returned in the response body for JSON format or as a template variable for HTML.

**Context:** error page entry

```kdl
error-pages {
    pages {
        "404" { format "json" message "The requested resource was not found" }
    }
}
```

---

### `metadata`

Key-value pairs attached to a target for use in load balancing decisions or logging. Enables zone-aware routing or custom selection logic.

**Context:** `target`

```kdl
target {
    address "10.0.1.1:8080"
    metadata { "zone" "us-east-1a" "version" "v2.1" }
}
```

---

### `method`

Matches requests using specific HTTP methods. Multiple methods can be specified to match any of them.

**Context:** `matches`

```kdl
matches {
    method "POST" "PUT" "PATCH"
    path-prefix "/api/"
}
```

---

### `min-version`

Minimum TLS version to accept. Setting to `1.2` or higher is recommended for security.

**Context:** `tls` (listener)
**Default:** `1.2`

```kdl
tls {
    min-version "1.2"
}
```

---

### `ocsp-stapling`

Enables OCSP stapling to prove certificate validity without clients contacting the CA. Improves TLS handshake performance and privacy.

**Context:** `tls` (listener)
**Default:** `#true`

```kdl
tls {
    ocsp-stapling #true
}
```

---

### `pages`

Container for individual error page configurations, keyed by HTTP status code.

**Context:** `error-pages`

```kdl
error-pages {
    pages {
        "400" { format "json" message "Bad request" }
        "404" { format "json" message "Not found" }
        "500" { format "html" template "/errors/500.html" }
    }
}
```

---

### `path`

Matches requests with an exact path. Use `path-prefix` for prefix matching or `path-regex` for patterns.

**Context:** `matches`, `health-check`

```kdl
matches {
    path "/api/v1/status"
}

health-check {
    type "http" { path "/health" }
}
```

---

### `path-prefix`

Matches requests where the path starts with the specified prefix. The most common matching type for API routing.

**Context:** `matches`

```kdl
matches {
    path-prefix "/api/v1/"
}
```

---

### `path-regex`

Matches requests where the path matches a regular expression. Most flexible but slowest matching type.

**Context:** `matches`

```kdl
matches {
    path-regex "^/users/[0-9]+/profile$"
}
```

---

### `pid-file`

Path to write the process ID file. Used for process management with systemd, init scripts, or monitoring tools.

**Context:** `system`

```kdl
system {
    daemon #true
    pid-file "/var/run/sentinel.pid"
}
```

---

### `policies`

Container for route-level policies including timeouts, headers, rate limiting, and failure behavior.

**Context:** `route`

```kdl
route "api" {
    policies {
        timeout-secs 30
        max-body-size "5MB"
        failure-mode "closed"
        rate-limit {
            requests-per-second 100
        }
    }
}
```

---

### `priority`

Numeric priority for route matching. Higher values are evaluated first. Routes with equal priority are evaluated in definition order.

**Context:** `route`
**Default:** `0`

```kdl
route "specific" {
    priority 100
    matches { path "/api/special" }
}

route "general" {
    priority 10
    matches { path-prefix "/api/" }
}
```

---

### `protocol`

Network protocol for the listener. Determines how connections are handled and what features are available.

**Context:** `listener`

Available: `http`, `https`, `h2` (HTTP/2 with TLS), `h3` (HTTP/3/QUIC)

```kdl
listener "secure" {
    protocol "https"
    tls { }
}
```

---

### `query-param`

Matches requests containing a specific query parameter with an optional value pattern.

**Context:** `matches`

```kdl
matches {
    query-param name="format" value="json"
    query-param name="debug"
}
```

---

### `rate-limit`

Configures rate limiting for the route. Protects backends from overload and ensures fair resource distribution.

**Context:** `policies`

```kdl
policies {
    rate-limit {
        requests-per-second 100
        burst 200
        key "client_ip"
    }
}
```

---

### `read-secs`

Maximum time in seconds to wait for response data from the upstream after the connection is established.

**Context:** `timeouts`
**Default:** `30`

```kdl
timeouts {
    read-secs 60
}
```

---

### `recovery-timeout-secs`

Time in seconds the circuit remains open before transitioning to half-open state to test if the upstream has recovered.

**Context:** `circuit-breaker` (agent)
**Default:** `30`

```kdl
agent "backend" {
    circuit-breaker {
        failure-threshold 5
        recovery-timeout-secs 60
    }
}
```

---

### `remove`

Removes a header from the request or response. Useful for stripping internal headers before forwarding.

**Context:** `request-headers`, `response-headers`

```kdl
policies {
    request-headers {
        remove "X-Internal-Token"
    }
    response-headers {
        remove "Server"
        remove "X-Powered-By"
    }
}
```

---

### `request-headers`

Container for request header manipulation rules. Modifications are applied before forwarding to the upstream.

**Context:** `policies`

```kdl
policies {
    request-headers {
        set { "X-Forwarded-Proto" "https" }
        add { "X-Request-Start" "$request_time" }
        remove "Cookie"
    }
}
```

---

### `request-secs`

Maximum total time in seconds for the complete request-response cycle with the upstream.

**Context:** `timeouts`
**Default:** `60`

```kdl
timeouts {
    connect-secs 5
    request-secs 120
}
```

---

### `request-timeout-secs`

Maximum time in seconds to wait for a complete request from the client. Protects against slow-loris attacks.

**Context:** `listener`
**Default:** `60`

```kdl
listener "http" {
    request-timeout-secs 30
}
```

---

### `requests-per-second`

Number of requests allowed per second for rate limiting. Requests exceeding this rate are rejected with 429 Too Many Requests.

**Context:** `rate-limit`

```kdl
rate-limit {
    requests-per-second 50
    burst 100
}
```

---

### `response-headers`

Container for response header manipulation rules. Modifications are applied before sending to the client.

**Context:** `policies`

```kdl
policies {
    response-headers {
        set { "X-Frame-Options" "DENY" }
        set { "X-Content-Type-Options" "nosniff" }
        remove "Server"
    }
}
```

---

### `retry-policy`

Configures automatic retry behavior for failed requests. Helps handle transient failures without client-side retry logic.

**Context:** `route`

```kdl
retry-policy {
    max-attempts 3
    timeout-ms 30000
    backoff-base-ms 100
    backoff-max-ms 5000
    retryable-status-codes 502 503 504
}
```

---

### `retryable-status-codes`

HTTP status codes that trigger an automatic retry. Typically includes gateway errors that indicate temporary upstream issues.

**Context:** `retry-policy`
**Default:** `502 503 504`

```kdl
retry-policy {
    retryable-status-codes 500 502 503 504 429
}
```

---

### `root`

Filesystem path to the directory containing static files. All file paths are resolved relative to this root.

**Context:** `static-files`

```kdl
static-files {
    root "/var/www/public"
    index "index.html"
}
```

---

### `route`

Defines a routing rule that matches requests and directs them to an upstream or built-in handler.

**Context:** `routes`

```kdl
routes {
    route "api" {
        priority 100
        matches { path-prefix "/api/" }
        upstream "backend"
        policies { timeout-secs 30 }
    }
}
```

---

### `routes`

Top-level block containing all route definitions. Routes are evaluated in priority order until a match is found.

**Context:** root

```kdl
routes {
    route "high-priority" { priority 100 }
    route "default" { priority 0 }
}
```

---

### `service`

gRPC service name for health checking. Uses the standard gRPC health checking protocol.

**Context:** `health-check` (grpc)

```kdl
health-check {
    type "grpc" {
        service "grpc.health.v1.Health"
    }
}
```

---

### `service-type`

Categorizes the route for specialized handling. Affects default behaviors and available options.

**Context:** `route`
**Default:** `web`

Available: `web`, `api`, `static`, `builtin`

```kdl
route "files" {
    service-type "static"
    static-files { root "/var/www" }
}
```

---

### `session-resumption`

Enables TLS session tickets for faster subsequent connections. Clients can resume sessions without full handshakes.

**Context:** `tls` (listener)
**Default:** `#true`

```kdl
tls {
    session-resumption #true
}
```

---

### `set`

Sets a header to a specific value, replacing any existing value. Use `add` to append without replacing.

**Context:** `request-headers`, `response-headers`

```kdl
policies {
    request-headers {
        set { "Host" "backend.internal" }
    }
    response-headers {
        set { "Cache-Control" "no-store" }
    }
}
```

---

### `sni`

Server Name Indication hostname to send when connecting to upstream over TLS. Required when the upstream uses virtual hosting.

**Context:** `tls` (upstream)

```kdl
upstream "backend" {
    tls {
        sni "api.backend.internal"
    }
}
```

---

### `static-files`

Configures static file serving for the route. Efficiently serves files with caching, compression, and range request support.

**Context:** `route`

```kdl
route "assets" {
    matches { path-prefix "/static/" }
    service-type "static"
    static-files {
        root "/var/www/assets"
        cache-control "public, max-age=31536000"
        compress #true
    }
}
```

---

### `success-threshold`

Number of consecutive successful requests required to close an open circuit breaker.

**Context:** `circuit-breaker`
**Default:** `2`

```kdl
circuit-breaker {
    failure-threshold 5
    success-threshold 3
}
```

---

### `system`

Top-level block for server-wide configuration including worker threads, connections, and process management.

**Context:** root

```kdl
system {
    worker-threads 0
    max-connections 50000
    graceful-shutdown-timeout-secs 60
}
```

---

### `target`

Defines an individual backend server within an upstream group. Multiple targets enable load balancing and failover.

**Context:** `targets`

```kdl
targets {
    target {
        address "10.0.1.1:8080"
        weight 3
    }
    target {
        address "10.0.1.2:8080"
        weight 1
    }
}
```

---

### `targets`

Container for upstream target definitions. At least one target is required for each upstream.

**Context:** `upstream`

```kdl
upstream "backend" {
    targets {
        target { address "10.0.1.1:8080" }
        target { address "10.0.1.2:8080" }
    }
}
```

---

### `template`

Path to an HTML template file for custom error pages. Templates can include variables for status code and message.

**Context:** error page entry

```kdl
error-pages {
    pages {
        "500" { format "html" template "/etc/sentinel/errors/500.html" }
    }
}
```

---

### `timeout-ms`

Maximum time in milliseconds to wait for an agent response. Agents exceeding this timeout trigger the `failure-mode` behavior.

**Context:** `agent`
**Default:** `100`

```kdl
agent "auth" {
    timeout-ms 50
    failure-mode "closed"
}
```

---

### `timeout-seconds`

Time in seconds the circuit breaker remains open before attempting recovery.

**Context:** `circuit-breaker`
**Default:** `30`

```kdl
circuit-breaker {
    failure-threshold 5
    timeout-seconds 60
}
```

---

### `timeout-secs`

Request timeout in seconds. Context determines whether this applies to client requests, upstream requests, or health checks.

**Context:** `policies`, `health-check`

```kdl
policies {
    timeout-secs 30
}

health-check {
    timeout-secs 5
}
```

---

### `timeouts`

Container for upstream timeout configuration. Controls connection, read, and write timeouts separately.

**Context:** `upstream`

```kdl
upstream "backend" {
    timeouts {
        connect-secs 5
        request-secs 60
        read-secs 30
        write-secs 30
    }
}
```

---

### `tls`

Configures TLS settings for secure connections. In listener context, configures server TLS. In upstream context, configures client TLS.

**Context:** `listener`, `upstream`

```kdl
listener "https" {
    tls {
        cert-file "/etc/sentinel/server.crt"
        key-file "/etc/sentinel/server.key"
        min-version "1.2"
    }
}

upstream "secure" {
    tls {
        ca-cert "/etc/sentinel/ca.pem"
        sni "backend.internal"
    }
}
```

---

### `trace-id-format`

Format for generated trace IDs in distributed tracing. Tinyflake IDs are smaller; UUIDs are more universally compatible.

**Context:** `system`
**Default:** `tinyflake`

Available: `tinyflake`, `uuid`

```kdl
system {
    trace-id-format "uuid"
}
```

---

### `transport`

Communication mechanism for agent connections. Unix sockets are faster for local agents; gRPC enables remote agents.

**Context:** `agent`

```kdl
agent "local-auth" {
    transport "unix_socket" {
        path "/var/run/auth.sock"
    }
}

agent "remote-waf" {
    transport "grpc" {
        address "waf-service:50051"
    }
}
```

---

### `type`

Specifies the type of agent or health check. Agent types affect default behaviors; health check types determine the protocol.

**Context:** `agent`, `health-check`

Agent types: `auth`, `rate_limit`, `waf`, `custom`

Health check types: `http`, `tcp`, `grpc`

```kdl
agent "auth" {
    type "auth"
}

health-check {
    type "http" { path "/health" }
}
```

---

### `unhealthy-threshold`

Number of consecutive failed health checks before marking a target as unhealthy and removing it from load balancing.

**Context:** `health-check`
**Default:** `3`

```kdl
health-check {
    unhealthy-threshold 2
    healthy-threshold 3
}
```

---

### `upstream`

Defines a group of backend servers or references an upstream by name in a route.

**Context:** `upstreams` (definition), `route` (reference)

```kdl
upstreams {
    upstream "backend" {
        targets {
            target { address "10.0.1.1:8080" }
        }
        load-balancing "round_robin"
    }
}

route "api" {
    upstream "backend"
}
```

---

### `upstreams`

Top-level block containing all upstream definitions. Upstreams are reusable groups of backend servers.

**Context:** root

```kdl
upstreams {
    upstream "primary" { }
    upstream "fallback" { }
}
```

---

### `user`

Unix user to switch to after binding privileged ports. Improves security by running with minimal privileges.

**Context:** `system`

```kdl
system {
    user "sentinel"
    group "sentinel"
}
```

---

### `waf-enabled`

Enables Web Application Firewall processing for the route. Requires a WAF agent to be configured.

**Context:** `route`
**Default:** `#false`

```kdl
route "api" {
    waf-enabled #true
    upstream "backend"
}
```

---

### `weight`

Relative weight for load balancing with weighted algorithms. Higher weights receive proportionally more traffic.

**Context:** `target`
**Default:** `1`

```kdl
targets {
    target { address "10.0.1.1:8080" weight=3 }
    target { address "10.0.1.2:8080" weight=1 }
}
```

---

### `worker-threads`

Number of worker threads for request processing. Set to 0 for automatic detection based on CPU cores.

**Context:** `system`
**Default:** `0` (auto)

```kdl
system {
    worker-threads 0
}
```

---

### `working-directory`

Directory to change to after startup. Affects relative path resolution for configuration files.

**Context:** `system`

```kdl
system {
    working-directory "/var/lib/sentinel"
}
```

---

### `write-secs`

Maximum time in seconds to wait for writing request data to the upstream.

**Context:** `timeouts`
**Default:** `30`

```kdl
timeouts {
    write-secs 60
}
```

---

## See Also

- [Configuration Schema](@/reference/config-schema.md) — Full configuration examples
- [CLI Reference](@/reference/cli.md) — Command-line options
- [Environment Variables](@/reference/env-vars.md) — Environment configuration
