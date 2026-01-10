+++
title = "Directive Index"
weight = 1
description = "Complete reference for all Sentinel configuration directives"
+++

Complete reference for all Sentinel configuration directives, verified against the source code. Each entry includes syntax, context, default values, and usage examples.

---

## Root-Level Blocks
<small class="source-ref">[`crates/config/src/lib.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/lib.rs)</small>

### `schema-version`

Configuration schema version for compatibility checking. Sentinel validates that the config matches the expected schema version.

**Context:** root
**Default:** `"1.0"`

```kdl
schema-version "1.0"
```

---

### `system`

Top-level block for server-wide configuration including worker threads, connections, and process management. The older name `server` is deprecated but still supported.

**Context:** root

```kdl
system {
    worker-threads 4
    max-connections 10000
    graceful-shutdown-timeout-secs 30
    auto-reload #true
}
```

---

### `listeners`

Top-level block containing all listener definitions. At least one listener is required for Sentinel to accept traffic.

**Context:** root

```kdl
listeners {
    listener "http" {
        address "0.0.0.0:8080"
    }
}
```

---

### `routes`

Top-level block containing all route definitions. Routes are evaluated in priority order until a match is found. At least one route is required.

**Context:** root

```kdl
routes {
    route "api" {
        matches { path-prefix "/api/" }
        upstream "backend"
    }
}
```

---

### `upstreams`

Top-level block containing all upstream definitions. Upstreams are reusable groups of backend servers.

**Context:** root

```kdl
upstreams {
    upstream "backend" {
        targets {
            target { address "10.0.1.1:8080" }
        }
    }
}
```

---

### `agents`

Top-level block containing all agent definitions. Agents are external services that process requests at various lifecycle points.

**Context:** root

```kdl
agents {
    agent "auth" {
        type "auth"
        transport {
            type "unix_socket"
            path "/var/run/auth.sock"
        }
    }
}
```

---

### `filters`

Top-level block containing filter definitions. Filters modify requests/responses and can be applied to routes.

**Context:** root

```kdl
filters {
    filter "rate-limit" {
        type "rate-limit"
        max-rps 100
        burst 200
    }
}
```

---

### `waf`

Top-level block for Web Application Firewall configuration.

**Context:** root

```kdl
waf {
    engine "coraza"
    mode "prevention"
    audit-log #true
    ruleset {
        crs-version "3.3.4"
        paranoia-level 1
    }
}
```

---

### `limits`

Top-level block for global resource limits. Protects against resource exhaustion.

**Context:** root

```kdl
limits {
    max-body-size-bytes 10485760
    max-header-size-bytes 8192
    max-header-count 100
    max-connections-per-client 100
}
```

---

### `cache`

Top-level block for global HTTP response caching configuration.

**Context:** root

```kdl
cache {
    enabled #true
    backend "memory"
    max-size-bytes 104857600
}
```

---

### `observability`

Top-level block for metrics, logging, and tracing configuration.

**Context:** root

```kdl
observability {
    metrics {
        enabled #true
        address "0.0.0.0:9090"
        path "/metrics"
    }
    logging {
        level "info"
        format "json"
    }
}
```

---

### `rate-limits`

Top-level block for global rate limiting defaults.

**Context:** root

```kdl
rate-limits {
    default-rps 100
    default-burst 200
    key "client-ip"
}
```

---

### `namespaces`

Top-level block for namespace-based configuration isolation.

**Context:** root

```kdl
namespaces {
    namespace "api" {
        routes { }
        upstreams { }
    }
}
```

---

## System Directives
<small class="source-ref">[`crates/config/src/server.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/server.rs)</small>

### `worker-threads`

Number of worker threads for request processing. Set to 0 for automatic detection based on CPU cores.

**Context:** `system`
**Default:** `0` (auto-detect)

```kdl
system {
    worker-threads 4
}
```

---

### `max-connections`

Maximum number of simultaneous connections server-wide.

**Context:** `system`
**Default:** `10000`

```kdl
system {
    max-connections 50000
}
```

---

### `graceful-shutdown-timeout-secs`

Maximum time in seconds to wait for in-flight requests to complete during shutdown.

**Context:** `system`
**Default:** `30`

```kdl
system {
    graceful-shutdown-timeout-secs 60
}
```

---

### `daemon`

When enabled, Sentinel forks to the background after startup.

**Context:** `system`
**Default:** `#false`

```kdl
system {
    daemon #true
    pid-file "/var/run/sentinel.pid"
}
```

---

### `pid-file`

Path to write the process ID file for process management.

**Context:** `system`

```kdl
system {
    pid-file "/var/run/sentinel.pid"
}
```

---

### `user`

Unix user to switch to after binding privileged ports.

**Context:** `system`

```kdl
system {
    user "sentinel"
    group "sentinel"
}
```

---

### `group`

Unix group to switch to after binding privileged ports.

**Context:** `system`

```kdl
system {
    user "sentinel"
    group "sentinel"
}
```

---

### `working-directory`

Directory to change to after startup.

**Context:** `system`

```kdl
system {
    working-directory "/var/lib/sentinel"
}
```

---

### `trace-id-format`

Format for generated trace IDs. Options: `"tinyflake"` (smaller) or `"uuid"` (more compatible).

**Context:** `system`
**Default:** `"tinyflake"`

```kdl
system {
    trace-id-format "uuid"
}
```

---

### `auto-reload`

When enabled, Sentinel watches the configuration file for changes and automatically reloads.

**Context:** `system`
**Default:** `#false`

```kdl
system {
    auto-reload #true
}
```

---

## Listener Directives
<small class="source-ref">[`crates/config/src/server.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/server.rs)</small>

### `listener`

Defines a network endpoint that accepts incoming connections.

**Context:** `listeners`

```kdl
listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}
```

---

### `address`

Socket address to bind (listeners) or connect to (upstream targets). Format: `host:port`.

**Context:** `listener`, `target`
**Required**

```kdl
listener "http" {
    address "0.0.0.0:8080"
}
```

---

### `protocol`

Network protocol for the listener. Options: `"http"`, `"https"`, `"h2"` (HTTP/2), `"h3"` (HTTP/3/QUIC).

**Context:** `listener`
**Default:** `"http"`

```kdl
listener "secure" {
    address "0.0.0.0:443"
    protocol "https"
}
```

---

### `request-timeout-secs`

Maximum time in seconds to wait for a complete request from the client.

**Context:** `listener`
**Default:** `60`

```kdl
listener "http" {
    request-timeout-secs 30
}
```

---

### `keepalive-timeout-secs`

Maximum time in seconds to keep an idle client connection open.

**Context:** `listener`
**Default:** `75`

```kdl
listener "http" {
    keepalive-timeout-secs 120
}
```

---

### `max-concurrent-streams`

Maximum number of concurrent HTTP/2 streams per connection.

**Context:** `listener`
**Default:** `100`

```kdl
listener "h2" {
    protocol "h2"
    max-concurrent-streams 250
}
```

---

### `default-route`

Fallback route ID when no other routes match the request.

**Context:** `listener`

```kdl
listener "http" {
    default-route "not-found"
}
```

---

## Listener TLS Directives
<small class="source-ref">[`crates/config/src/server.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/server.rs)</small>

### `tls`

Configures TLS settings for secure connections.

**Context:** `listener`, `upstream`

```kdl
listener "https" {
    tls {
        cert-file "/etc/sentinel/server.crt"
        key-file "/etc/sentinel/server.key"
    }
}
```

---

### `cert-file`

Path to the TLS certificate file in PEM format.

**Context:** `tls` (listener)
**Required for HTTPS**

```kdl
tls {
    cert-file "/etc/sentinel/server.crt"
    key-file "/etc/sentinel/server.key"
}
```

---

### `key-file`

Path to the TLS private key file in PEM format.

**Context:** `tls` (listener)
**Required for HTTPS**

```kdl
tls {
    cert-file "/etc/sentinel/server.crt"
    key-file "/etc/sentinel/server.key"
}
```

---

### `ca-file`

Path to CA certificate file for verifying client certificates (mTLS).

**Context:** `tls` (listener)

```kdl
tls {
    ca-file "/etc/sentinel/client-ca.pem"
    client-auth #true
}
```

---

### `min-version`

Minimum TLS version to accept. Options: `"TLS1.2"`, `"TLS1.3"`.

**Context:** `tls` (listener)
**Default:** `"TLS1.2"`

```kdl
tls {
    min-version "TLS1.2"
}
```

---

### `max-version`

Maximum TLS version to accept.

**Context:** `tls` (listener)

```kdl
tls {
    min-version "TLS1.2"
    max-version "TLS1.3"
}
```

---

### `client-auth`

Enables mutual TLS (mTLS) requiring client certificates.

**Context:** `tls` (listener)
**Default:** `#false`

```kdl
tls {
    ca-file "/etc/sentinel/client-ca.pem"
    client-auth #true
}
```

---

### `ocsp-stapling`

Enables OCSP stapling for certificate validation.

**Context:** `tls` (listener)
**Default:** `#true`

```kdl
tls {
    ocsp-stapling #true
}
```

---

### `session-resumption`

Enables TLS session tickets for faster subsequent connections.

**Context:** `tls` (listener)
**Default:** `#true`

```kdl
tls {
    session-resumption #true
}
```

---

### `cipher-suites`

Restricts allowed TLS cipher suites. Empty uses secure defaults.

**Context:** `tls` (listener)

```kdl
tls {
    cipher-suites "TLS_AES_256_GCM_SHA384" "TLS_CHACHA20_POLY1305_SHA256"
}
```

---

### `sni`

SNI-based certificate selection block within TLS configuration.

**Context:** `tls` (listener)

```kdl
tls {
    cert-file "/etc/certs/default.crt"
    key-file "/etc/certs/default.key"
    sni {
        hostnames "example.com" "*.example.com"
        cert-file "/etc/certs/example.crt"
        key-file "/etc/certs/example.key"
    }
}
```

---

## Route Directives
<small class="source-ref">[`crates/config/src/routes.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/routes.rs)</small>

### `route`

Defines a routing rule that matches requests and directs them to an upstream or handler.

**Context:** `routes`

```kdl
routes {
    route "api" {
        matches { path-prefix "/api/" }
        upstream "backend"
    }
}
```

---

### `priority`

Route evaluation priority. Options: `"high"`, `"normal"`, `"low"`.

**Context:** `route`
**Default:** `"normal"`

```kdl
route "specific" {
    priority "high"
    matches { path "/api/special" }
}
```

---

### `service-type`

Categorizes the route for specialized handling. Options: `"web"`, `"api"`, `"static"`, `"builtin"`.

**Context:** `route`
**Default:** `"web"`

```kdl
route "files" {
    service-type "static"
    static-files { root "/var/www" }
}
```

---

### `upstream`

Target upstream pool ID for proxied requests.

**Context:** `route`

```kdl
route "api" {
    upstream "backend"
}
```

---

### `builtin-handler`

Built-in handler instead of proxying. Options: `"status"`, `"health"`, `"metrics"`, `"config"`, `"upstreams"`, `"cache-purge"`, `"cache-stats"`, `"not-found"`.

**Context:** `route`

```kdl
route "health" {
    matches { path "/health" }
    service-type "builtin"
    builtin-handler "health"
}
```

---

### `waf-enabled`

Enables WAF processing for this route.

**Context:** `route`
**Default:** `#false`

```kdl
route "api" {
    waf-enabled #true
}
```

---

### `websocket`

Enables WebSocket upgrade support.

**Context:** `route`
**Default:** `#false`

```kdl
route "ws" {
    websocket #true
}
```

---

### `websocket-inspection`

Enables WebSocket frame inspection.

**Context:** `route`
**Default:** `#false`

```kdl
route "ws" {
    websocket #true
    websocket-inspection #true
}
```

---

### `filters`

List of filter IDs to apply to the route in order.

**Context:** `route`

```kdl
route "api" {
    filters "rate-limit" "cors" "logging"
}
```

---

## Route Matching Directives
<small class="source-ref">[`crates/config/src/routes.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/routes.rs)</small>

### `matches`

Defines conditions for routing requests. Multiple conditions use AND logic.

**Context:** `route`

```kdl
route "api-v2" {
    matches {
        path-prefix "/api/"
        header "X-API-Version" "v2"
    }
}
```

---

### `path-prefix`

Matches requests where the path starts with the specified prefix.

**Context:** `matches`

```kdl
matches {
    path-prefix "/api/v1/"
}
```

---

### `path`

Matches requests with an exact path.

**Context:** `matches`

```kdl
matches {
    path "/api/v1/status"
}
```

---

### `host`

Matches requests with a specific Host header. Supports wildcards.

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

### `method`

Matches requests using specific HTTP methods.

**Context:** `matches`

```kdl
matches {
    method "GET" "POST"
}
```

---

### `header`

Matches requests containing a specific header with optional value.

**Context:** `matches`

```kdl
matches {
    header "X-API-Version" "v2"
    header "Authorization"
}
```

---

### `query-param`

Matches requests containing a specific query parameter with optional value.

**Context:** `matches`

```kdl
matches {
    query-param "format" "json"
    query-param "debug"
}
```

---

## Route Policies Directives
<small class="source-ref">[`crates/config/src/routes.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/routes.rs)</small>

### `policies`

Container for route-level policies including timeouts, headers, and rate limiting.

**Context:** `route`

```kdl
route "api" {
    policies {
        timeout-secs 30
        max-body-size "5MB"
    }
}
```

---

### `timeout-secs`

Request timeout in seconds.

**Context:** `policies`, `health-check`

```kdl
policies {
    timeout-secs 30
}
```

---

### `max-body-size`

Maximum allowed request body size for this route.

**Context:** `policies`

```kdl
policies {
    max-body-size "10MB"
}
```

---

### `failure-mode`

Behavior when agent/upstream fails. Options: `"open"` (allow), `"closed"` (reject).

**Context:** `policies`, `agent`
**Default:** `"closed"`

```kdl
policies {
    failure-mode "open"
}
```

---

### `buffer-requests`

When enabled, reads entire request body into memory before forwarding.

**Context:** `policies`
**Default:** `#false`

```kdl
policies {
    buffer-requests #true
}
```

---

### `buffer-responses`

When enabled, reads entire response body into memory before sending to client.

**Context:** `policies`
**Default:** `#false`

```kdl
policies {
    buffer-responses #true
}
```

---

### `request-headers`

Container for request header manipulation rules.

**Context:** `policies`

```kdl
policies {
    request-headers {
        set { "X-Forwarded-Proto" "https" }
        add { "X-Request-ID" "abc123" }
        remove "Cookie"
    }
}
```

---

### `response-headers`

Container for response header manipulation rules.

**Context:** `policies`

```kdl
policies {
    response-headers {
        set { "X-Frame-Options" "DENY" }
        remove "Server"
    }
}
```

---

### `set`

Sets a header value, replacing any existing value.

**Context:** `request-headers`, `response-headers`

```kdl
request-headers {
    set { "Host" "backend.internal" }
}
```

---

### `add`

Adds a header value without removing existing values.

**Context:** `request-headers`, `response-headers`

```kdl
response-headers {
    add { "X-Served-By" "sentinel" }
}
```

---

### `remove`

Removes a header.

**Context:** `request-headers`, `response-headers`

```kdl
request-headers {
    remove "X-Internal-Token"
}
```

---

### `rate-limit`

Configures rate limiting for the route.

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

### `requests-per-second`

Number of requests allowed per second.

**Context:** `rate-limit`

```kdl
rate-limit {
    requests-per-second 100
}
```

---

### `burst`

Maximum requests allowed to exceed the rate limit temporarily.

**Context:** `rate-limit`
**Default:** `10`

```kdl
rate-limit {
    requests-per-second 100
    burst 500
}
```

---

### `key`

Determines how rate limits are applied. Options: `"client_ip"`, `"header:name"`, `"path"`, `"route"`.

**Context:** `rate-limit`
**Default:** `"client_ip"`

```kdl
rate-limit {
    key "header:X-API-Key"
}
```

---

## Route Cache Directives
<small class="source-ref">[`crates/config/src/routes.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/routes.rs)</small>

### `cache`

Configures response caching for the route.

**Context:** `policies`

```kdl
policies {
    cache {
        enabled #true
        default-ttl-secs 3600
    }
}
```

---

### `enabled`

Enables or disables caching.

**Context:** `cache`
**Default:** `#false`

```kdl
cache {
    enabled #true
}
```

---

### `default-ttl-secs`

Default cache TTL in seconds when not specified by response headers.

**Context:** `cache`
**Default:** `3600`

```kdl
cache {
    default-ttl-secs 7200
}
```

---

### `max-size-bytes`

Maximum size of a cached response.

**Context:** `cache`

```kdl
cache {
    max-size-bytes 10485760
}
```

---

### `cache-private`

Whether to cache responses with Cache-Control: private.

**Context:** `cache`
**Default:** `#false`

```kdl
cache {
    cache-private #true
}
```

---

### `stale-while-revalidate-secs`

Serve stale content while revalidating in background.

**Context:** `cache`

```kdl
cache {
    stale-while-revalidate-secs 60
}
```

---

### `stale-if-error-secs`

Serve stale content if upstream returns error.

**Context:** `cache`

```kdl
cache {
    stale-if-error-secs 300
}
```

---

### `cacheable-methods`

HTTP methods eligible for caching.

**Context:** `cache`

```kdl
cache {
    cacheable-methods "GET" "HEAD"
}
```

---

### `cacheable-status-codes`

HTTP status codes eligible for caching.

**Context:** `cache`

```kdl
cache {
    cacheable-status-codes 200 203 204 206 300 301 308 404 410
}
```

---

### `vary-headers`

Headers to include in cache key.

**Context:** `cache`

```kdl
cache {
    vary-headers "Accept" "Accept-Encoding"
}
```

---

### `ignore-query-params`

Query parameters to exclude from cache key.

**Context:** `cache`

```kdl
cache {
    ignore-query-params "utm_source" "utm_medium"
}
```

---

## Static Files Directives
<small class="source-ref">[`crates/config/src/routes.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/routes.rs)</small>

### `static-files`

Configures static file serving for the route.

**Context:** `route`

```kdl
route "assets" {
    service-type "static"
    static-files {
        root "/var/www/public"
        index "index.html"
    }
}
```

---

### `root`

Filesystem path to the static files directory.

**Context:** `static-files`
**Required**

```kdl
static-files {
    root "/var/www/public"
}
```

---

### `index`

Filename to serve for directory requests.

**Context:** `static-files`
**Default:** `"index.html"`

```kdl
static-files {
    index "index.html"
}
```

---

### `directory-listing`

Enable HTML directory listing.

**Context:** `static-files`
**Default:** `#false`

```kdl
static-files {
    directory-listing #true
}
```

---

### `cache-control`

Cache-Control header for static responses.

**Context:** `static-files`

```kdl
static-files {
    cache-control "public, max-age=86400"
}
```

---

### `compress`

Enable automatic compression (gzip, brotli).

**Context:** `static-files`
**Default:** `#true`

```kdl
static-files {
    compress #true
}
```

---

### `fallback`

File to serve when requested file doesn't exist (SPA support).

**Context:** `static-files`

```kdl
static-files {
    root "/var/www/app"
    fallback "index.html"
}
```

---

### `mime-types`

Custom MIME type mappings.

**Context:** `static-files`

```kdl
static-files {
    mime-types {
        ".wasm" "application/wasm"
    }
}
```

---

## Circuit Breaker Directives
<small class="source-ref">[`crates/config/src/routes.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/routes.rs)</small>

### `circuit-breaker`

Configures circuit breaker to prevent cascading failures.

**Context:** `route`, `agent`

```kdl
circuit-breaker {
    failure-threshold 5
    success-threshold 2
    timeout-seconds 30
}
```

---

### `failure-threshold`

Consecutive failures before circuit opens.

**Context:** `circuit-breaker`
**Default:** `5`

```kdl
circuit-breaker {
    failure-threshold 10
}
```

---

### `success-threshold`

Consecutive successes to close circuit.

**Context:** `circuit-breaker`
**Default:** `2`

```kdl
circuit-breaker {
    success-threshold 3
}
```

---

### `timeout-seconds`

Time circuit remains open before half-open test.

**Context:** `circuit-breaker`
**Default:** `30`

```kdl
circuit-breaker {
    timeout-seconds 60
}
```

---

### `half-open-max-requests`

Requests allowed in half-open state.

**Context:** `circuit-breaker`
**Default:** `3`

```kdl
circuit-breaker {
    half-open-max-requests 5
}
```

---

## Retry Policy Directives
<small class="source-ref">[`crates/config/src/routes.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/routes.rs)</small>

### `retry-policy`

Configures automatic retry behavior for failed requests.

**Context:** `route`

```kdl
retry-policy {
    max-attempts 3
    backoff-base-ms 100
    retryable-status-codes 502 503 504
}
```

---

### `max-attempts`

Maximum retry attempts including initial try.

**Context:** `retry-policy`
**Default:** `3`

```kdl
retry-policy {
    max-attempts 5
}
```

---

### `timeout-ms`

Total timeout for all retry attempts.

**Context:** `retry-policy`
**Default:** `5000`

```kdl
retry-policy {
    timeout-ms 30000
}
```

---

### `backoff-base-ms`

Initial retry delay in milliseconds.

**Context:** `retry-policy`
**Default:** `100`

```kdl
retry-policy {
    backoff-base-ms 200
}
```

---

### `backoff-max-ms`

Maximum retry delay.

**Context:** `retry-policy`
**Default:** `2000`

```kdl
retry-policy {
    backoff-max-ms 5000
}
```

---

### `retryable-status-codes`

HTTP status codes that trigger retries.

**Context:** `retry-policy`
**Default:** `502 503 504`

```kdl
retry-policy {
    retryable-status-codes 500 502 503 504
}
```

---

## Shadow/Traffic Mirroring Directives
<small class="source-ref">[`crates/config/src/routes.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/routes.rs)</small>

### `shadow`

Configures traffic mirroring to a shadow upstream.

**Context:** `route`

```kdl
shadow {
    upstream "shadow-backend"
    percentage 10.0
}
```

---

### `percentage`

Percentage of traffic to mirror (0.0 to 100.0).

**Context:** `shadow`
**Default:** `100.0`

```kdl
shadow {
    percentage 50.0
}
```

---

### `sample-header`

Only mirror requests with this header/value.

**Context:** `shadow`

```kdl
shadow {
    sample-header "X-Canary" "true"
}
```

---

### `buffer-body`

Buffer request body for mirroring.

**Context:** `shadow`
**Default:** `#true`

```kdl
shadow {
    buffer-body #true
    max-body-bytes 1048576
}
```

---

## Error Pages Directives
<small class="source-ref">[`crates/config/src/routes.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/routes.rs)</small>

### `error-pages`

Configures custom error responses.

**Context:** `route`

```kdl
error-pages {
    default-format "json"
    pages {
        "404" { format "json" message "Not found" }
    }
}
```

---

### `default-format`

Default response format. Options: `"html"`, `"json"`, `"text"`, `"xml"`.

**Context:** `error-pages`
**Default:** `"json"`

```kdl
error-pages {
    default-format "html"
}
```

---

### `include-stack-trace`

Include stack traces in error responses.

**Context:** `error-pages`
**Default:** `#false`

```kdl
error-pages {
    include-stack-trace #true
}
```

---

### `template-dir`

Directory containing error page templates.

**Context:** `error-pages`

```kdl
error-pages {
    template-dir "/etc/sentinel/templates"
}
```

---

### `pages`

Individual error page configurations by status code.

**Context:** `error-pages`

```kdl
pages {
    "404" {
        format "html"
        template "/templates/404.html"
    }
    "500" {
        format "json"
        message "Internal server error"
    }
}
```

---

## Upstream Directives
<small class="source-ref">[`crates/config/src/upstreams.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/upstreams.rs)</small>

### `upstream`

Defines a group of backend servers.

**Context:** `upstreams`

```kdl
upstreams {
    upstream "backend" {
        targets { }
        load-balancing "round_robin"
    }
}
```

---

### `load-balancing`

Algorithm for distributing requests. Options: `"round_robin"`, `"least_connections"`, `"ip_hash"`, `"consistent_hash"`, `"random"`.

**Context:** `upstream`
**Default:** `"round_robin"`

```kdl
upstream "backend" {
    load-balancing "least_connections"
}
```

---

### `targets`

Container for upstream target definitions.

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

### `target`

Defines an individual backend server.

**Context:** `targets`

```kdl
target {
    address "10.0.1.1:8080"
    weight 1
}
```

---

### `weight`

Relative weight for load balancing.

**Context:** `target`
**Default:** `1`

```kdl
target {
    address "10.0.1.1:8080"
    weight 3
}
```

---

### `max-requests`

Maximum requests through this target before rotation.

**Context:** `target`

```kdl
target {
    address "10.0.1.1:8080"
    max-requests 10000
}
```

---

### `metadata`

Key-value pairs for load balancing decisions.

**Context:** `target`

```kdl
target {
    address "10.0.1.1:8080"
    metadata { "zone" "us-east-1a" }
}
```

---

## Health Check Directives
<small class="source-ref">[`crates/config/src/upstreams.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/upstreams.rs)</small>

### `health-check`

Configures active health checking for upstream targets.

**Context:** `upstream`

```kdl
health-check {
    type "http"
    path "/health"
    interval-secs 10
}
```

---

### `type`

Health check protocol. Options: `"http"`, `"tcp"`.

**Context:** `health-check`
**Default:** `"http"`

```kdl
health-check {
    type "tcp"
}
```

---

### `interval-secs`

Time between health check probes.

**Context:** `health-check`
**Default:** `10`

```kdl
health-check {
    interval-secs 5
}
```

---

### `healthy-threshold`

Successful checks to mark target healthy.

**Context:** `health-check`
**Default:** `2`

```kdl
health-check {
    healthy-threshold 3
}
```

---

### `unhealthy-threshold`

Failed checks to mark target unhealthy.

**Context:** `health-check`
**Default:** `3`

```kdl
health-check {
    unhealthy-threshold 2
}
```

---

### `expected-status`

HTTP status indicating healthy (for HTTP checks).

**Context:** `health-check`
**Default:** `200`

```kdl
health-check {
    type "http"
    path "/health"
    expected-status 200
}
```

---

## Connection Pool Directives
<small class="source-ref">[`crates/config/src/upstreams.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/upstreams.rs)</small>

### `connection-pool`

Configures connection pooling to upstream targets.

**Context:** `upstream`

```kdl
connection-pool {
    max-connections 100
    max-idle 20
    idle-timeout-secs 60
}
```

---

### `max-idle`

Maximum idle connections to keep in pool.

**Context:** `connection-pool`
**Default:** `20`

```kdl
connection-pool {
    max-idle 30
}
```

---

### `idle-timeout-secs`

Time before idle connection is closed.

**Context:** `connection-pool`
**Default:** `60`

```kdl
connection-pool {
    idle-timeout-secs 120
}
```

---

### `max-lifetime-secs`

Maximum connection lifetime.

**Context:** `connection-pool`
**Default:** `300`

```kdl
connection-pool {
    max-lifetime-secs 3600
}
```

---

## Upstream Timeouts Directives
<small class="source-ref">[`crates/config/src/upstreams.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/upstreams.rs)</small>

### `timeouts`

Container for upstream timeout configuration.

**Context:** `upstream`

```kdl
timeouts {
    connect-secs 10
    request-secs 60
    read-secs 30
    write-secs 30
}
```

---

### `connect-secs`

Maximum time to establish connection.

**Context:** `timeouts`
**Default:** `10`

```kdl
timeouts {
    connect-secs 5
}
```

---

### `request-secs`

Maximum time for complete request-response cycle.

**Context:** `timeouts`
**Default:** `60`

```kdl
timeouts {
    request-secs 120
}
```

---

### `read-secs`

Maximum time waiting for response data.

**Context:** `timeouts`
**Default:** `30`

```kdl
timeouts {
    read-secs 60
}
```

---

### `write-secs`

Maximum time writing request data.

**Context:** `timeouts`
**Default:** `30`

```kdl
timeouts {
    write-secs 60
}
```

---

## Upstream TLS Directives
<small class="source-ref">[`crates/config/src/upstreams.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/upstreams.rs)</small>

### `sni`

SNI hostname for upstream TLS connections.

**Context:** `tls` (upstream)

```kdl
upstream "backend" {
    tls {
        sni "api.backend.internal"
    }
}
```

---

### `insecure-skip-verify`

Disables TLS certificate verification. **Security risk**.

**Context:** `tls` (upstream)
**Default:** `#false`

```kdl
tls {
    insecure-skip-verify #true
}
```

---

### `client-cert`

Path to client certificate for mTLS to upstream.

**Context:** `tls` (upstream)

```kdl
tls {
    client-cert "/etc/sentinel/client.crt"
    client-key "/etc/sentinel/client.key"
}
```

---

### `client-key`

Path to client private key for mTLS.

**Context:** `tls` (upstream)

```kdl
tls {
    client-cert "/etc/sentinel/client.crt"
    client-key "/etc/sentinel/client.key"
}
```

---

### `ca-cert`

Path to CA certificate for upstream verification.

**Context:** `tls` (upstream)

```kdl
tls {
    ca-cert "/etc/sentinel/ca.pem"
}
```

---

## HTTP Version Directives
<small class="source-ref">[`crates/config/src/upstreams.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/upstreams.rs)</small>

### `http-version`

Configures HTTP version settings for upstream connections.

**Context:** `upstream`

```kdl
http-version {
    min-version 1
    max-version 2
}
```

---

### `min-version`

Minimum HTTP version (1 or 2).

**Context:** `http-version`
**Default:** `1`

```kdl
http-version {
    min-version 2
}
```

---

### `max-version`

Maximum HTTP version.

**Context:** `http-version`
**Default:** `2`

```kdl
http-version {
    max-version 2
}
```

---

### `h2-ping-interval-secs`

HTTP/2 ping interval (0 to disable).

**Context:** `http-version`
**Default:** `0`

```kdl
http-version {
    h2-ping-interval-secs 30
}
```

---

### `max-h2-streams`

Maximum HTTP/2 streams per connection.

**Context:** `http-version`
**Default:** `100`

```kdl
http-version {
    max-h2-streams 200
}
```

---

## Agent Directives
<small class="source-ref">[`crates/config/src/agents.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/agents.rs)</small>

### `agent`

Defines an external processing agent.

**Context:** `agents`

```kdl
agents {
    agent "auth" {
        type "auth"
        timeout-ms 1000
        failure-mode "closed"
    }
}
```

---

### `type` (agent)

Agent type. Common: `"waf"`, `"auth"`, `"rate_limit"`, or custom string.

**Context:** `agent`
**Required**

```kdl
agent "auth" {
    type "auth"
}
```

---

### `timeout-ms`

Maximum time to wait for agent response.

**Context:** `agent`
**Default:** `1000`

```kdl
agent "auth" {
    timeout-ms 50
}
```

---

### `max-request-body-bytes`

Maximum request body to send to agent.

**Context:** `agent`

```kdl
agent "waf" {
    max-request-body-bytes 1048576
}
```

---

### `max-response-body-bytes`

Maximum response body to send to agent.

**Context:** `agent`

```kdl
agent "logger" {
    max-response-body-bytes 4096
}
```

---

### `request-body-mode`

How to handle request body. Options: `"buffer"`, `"stream"`, `"hybrid"`.

**Context:** `agent`
**Default:** `"buffer"`

```kdl
agent "waf" {
    request-body-mode "buffer"
}
```

---

### `response-body-mode`

How to handle response body. Options: `"buffer"`, `"stream"`, `"hybrid"`.

**Context:** `agent`
**Default:** `"buffer"`

```kdl
agent "logger" {
    response-body-mode "stream"
}
```

---

### `chunk-timeout-ms`

Timeout per body chunk when streaming.

**Context:** `agent`
**Default:** `5000`

```kdl
agent "waf" {
    chunk-timeout-ms 2000
}
```

---

### `max-concurrent-calls`

Maximum concurrent calls to agent.

**Context:** `agent`
**Default:** `100`

```kdl
agent "auth" {
    max-concurrent-calls 200
}
```

---

### `transport`

Communication mechanism for agent connections.

**Context:** `agent`

```kdl
agent "auth" {
    transport {
        type "unix_socket"
        path "/var/run/auth.sock"
    }
}
```

---

### `events`

Request lifecycle events the agent receives.

**Context:** `agent`

Available: `"request_headers"`, `"request_body"`, `"response_headers"`, `"response_body"`, `"log"`, `"websocket_frame"`

```kdl
agent "logger" {
    events "request_headers" "response_headers"
}
```

---

### `config`

Agent-specific configuration passed as JSON.

**Context:** `agent`

```kdl
agent "custom" {
    config {
        custom-field "value"
    }
}
```

---

## Transport Directives
<small class="source-ref">[`crates/config/src/agents.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/agents.rs)</small>

### `type` (transport)

Transport type. Options: `"unix_socket"`, `"grpc"`, `"http"`.

**Context:** `transport`
**Required**

```kdl
transport {
    type "unix_socket"
    path "/var/run/agent.sock"
}
```

---

### `path`

Unix socket path.

**Context:** `transport` (unix_socket)

```kdl
transport {
    type "unix_socket"
    path "/var/run/auth.sock"
}
```

---

### `url`

HTTP endpoint URL.

**Context:** `transport` (http)

```kdl
transport {
    type "http"
    url "http://127.0.0.1:8888"
}
```

---

## Filter Directives
<small class="source-ref">[`crates/config/src/filters.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/filters.rs)</small>

### `filter`

Defines a reusable filter.

**Context:** `filters`

```kdl
filters {
    filter "rate-limit" {
        type "rate-limit"
        max-rps 100
    }
}
```

---

### `type` (filter)

Filter type. Options: `"rate-limit"`, `"headers"`, `"compress"`, `"cors"`, `"timeout"`, `"log"`, `"geo"`, `"agent"`.

**Context:** `filter`
**Required**

```kdl
filter "cors" {
    type "cors"
}
```

---

### `max-rps`

Maximum requests per second (rate-limit filter).

**Context:** `filter` (rate-limit)

```kdl
filter "rate-limit" {
    type "rate-limit"
    max-rps 100
    burst 200
}
```

---

### `on-limit`

Action when rate limit exceeded. Options: `"reject"`, `"delay"`, `"log-only"`.

**Context:** `filter` (rate-limit)
**Default:** `"reject"`

```kdl
filter "rate-limit" {
    type "rate-limit"
    on-limit "delay"
    max-delay-ms 5000
}
```

---

### `status-code`

HTTP status code for rate limit rejection.

**Context:** `filter` (rate-limit)
**Default:** `429`

```kdl
filter "rate-limit" {
    type "rate-limit"
    status-code 503
}
```

---

### `backend`

Rate limit storage backend. Options: `"local"`, `"redis"`, `"memcached"`.

**Context:** `filter` (rate-limit)
**Default:** `"local"`

```kdl
filter "rate-limit" {
    type "rate-limit"
    backend {
        type "redis"
        url "redis://127.0.0.1:6379"
    }
}
```

---

### `phase`

When filter runs. Options: `"request"`, `"response"`, `"both"`.

**Context:** `filter` (headers)

```kdl
filter "headers" {
    type "headers"
    phase "response"
}
```

---

### `algorithms`

Compression algorithms. Options: `"gzip"`, `"br"`, `"deflate"`, `"zstd"`.

**Context:** `filter` (compress)

```kdl
filter "compress" {
    type "compress"
    algorithms "gzip" "br"
}
```

---

### `min-size`

Minimum size for compression.

**Context:** `filter` (compress)
**Default:** `1024`

```kdl
filter "compress" {
    type "compress"
    min-size 512
}
```

---

### `content-types`

Content types to compress.

**Context:** `filter` (compress)

```kdl
filter "compress" {
    type "compress"
    content-types "text/html" "application/json"
}
```

---

### `level`

Compression level (1-9).

**Context:** `filter` (compress)
**Default:** `6`

```kdl
filter "compress" {
    type "compress"
    level 9
}
```

---

### `allowed-origins`

CORS allowed origins.

**Context:** `filter` (cors)

```kdl
filter "cors" {
    type "cors"
    allowed-origins "*"
}
```

---

### `allowed-methods`

CORS allowed methods.

**Context:** `filter` (cors)

```kdl
filter "cors" {
    type "cors"
    allowed-methods "GET" "POST" "PUT"
}
```

---

### `allowed-headers`

CORS allowed headers.

**Context:** `filter` (cors)

```kdl
filter "cors" {
    type "cors"
    allowed-headers "Content-Type" "Authorization"
}
```

---

### `allow-credentials`

CORS allow credentials.

**Context:** `filter` (cors)
**Default:** `#false`

```kdl
filter "cors" {
    type "cors"
    allow-credentials #true
}
```

---

### `max-age-secs`

CORS preflight cache duration.

**Context:** `filter` (cors)
**Default:** `86400`

```kdl
filter "cors" {
    type "cors"
    max-age-secs 3600
}
```

---

### `database-path`

GeoIP database path.

**Context:** `filter` (geo)

```kdl
filter "geo" {
    type "geo"
    database-path "/etc/sentinel/GeoLite2-Country.mmdb"
}
```

---

### `database-type`

GeoIP database type. Options: `"maxmind"`, `"ip2location"`.

**Context:** `filter` (geo)
**Default:** `"maxmind"`

```kdl
filter "geo" {
    type "geo"
    database-type "maxmind"
}
```

---

### `action`

Geo filter action. Options: `"block"`, `"allow"`, `"log-only"`.

**Context:** `filter` (geo)

```kdl
filter "geo" {
    type "geo"
    action "block"
    countries "RU" "CN"
}
```

---

### `countries`

Country codes for geo filter (ISO 3166-1 alpha-2).

**Context:** `filter` (geo)

```kdl
filter "geo" {
    type "geo"
    countries "US" "CA" "GB"
}
```

---

## WAF Directives
<small class="source-ref">[`crates/config/src/waf.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/waf.rs)</small>

### `engine`

WAF engine. Options: `"modsecurity"`, `"coraza"`, or custom.

**Context:** `waf`
**Required**

```kdl
waf {
    engine "coraza"
}
```

---

### `mode`

WAF mode. Options: `"off"`, `"detection"`, `"prevention"`.

**Context:** `waf`
**Default:** `"prevention"`

```kdl
waf {
    mode "detection"
}
```

---

### `audit-log`

Enable WAF audit logging.

**Context:** `waf`
**Default:** `#true`

```kdl
waf {
    audit-log #true
}
```

---

### `ruleset`

WAF ruleset configuration.

**Context:** `waf`

```kdl
waf {
    ruleset {
        crs-version "3.3.4"
        paranoia-level 1
        anomaly-threshold 5
    }
}
```

---

### `crs-version`

OWASP Core Rule Set version.

**Context:** `ruleset`

```kdl
ruleset {
    crs-version "3.3.4"
}
```

---

### `paranoia-level`

CRS paranoia level (1-4).

**Context:** `ruleset`
**Default:** `1`

```kdl
ruleset {
    paranoia-level 2
}
```

---

### `anomaly-threshold`

Anomaly score threshold for blocking.

**Context:** `ruleset`
**Default:** `5`

```kdl
ruleset {
    anomaly-threshold 10
}
```

---

### `exclusions`

WAF rule exclusions.

**Context:** `waf`

```kdl
waf {
    exclusions {
        exclusion {
            rule-ids "920350" "920420"
            scope "global"
        }
    }
}
```

---

### `body-inspection`

WAF body inspection policy.

**Context:** `waf`

```kdl
waf {
    body-inspection {
        inspect-request-body #true
        inspect-response-body #false
        max-inspection-bytes 1048576
    }
}
```

---

## Limits Directives
<small class="source-ref">[`crates/common/src/limits.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/common/src/limits.rs)</small>

### `max-header-size-bytes`

Maximum size per header.

**Context:** `limits`
**Default:** `8192`

```kdl
limits {
    max-header-size-bytes 16384
}
```

---

### `max-header-count`

Maximum number of headers.

**Context:** `limits`
**Default:** `100`

```kdl
limits {
    max-header-count 200
}
```

---

### `max-body-size-bytes`

Maximum request body size.

**Context:** `limits`
**Default:** `1048576`

```kdl
limits {
    max-body-size-bytes 10485760
}
```

---

### `max-connections-per-client`

Maximum connections from single client.

**Context:** `limits`
**Default:** `100`

```kdl
limits {
    max-connections-per-client 50
}
```

---

### `max-connections-per-route`

Maximum connections per route.

**Context:** `limits`
**Default:** `1000`

```kdl
limits {
    max-connections-per-route 500
}
```

---

### `max-total-connections`

Global maximum connections.

**Context:** `limits`
**Default:** `10000`

```kdl
limits {
    max-total-connections 50000
}
```

---

### `max-in-flight-requests`

Maximum in-flight requests globally.

**Context:** `limits`
**Default:** `10000`

```kdl
limits {
    max-in-flight-requests 20000
}
```

---

### `max-queued-requests`

Queue length before rejection.

**Context:** `limits`
**Default:** `1000`

```kdl
limits {
    max-queued-requests 5000
}
```

---

## Observability Directives
<small class="source-ref">[`crates/config/src/observability.rs`](https://github.com/raskell-io/sentinel/blob/main/crates/config/src/observability.rs)</small>

### `metrics`

Prometheus metrics configuration.

**Context:** `observability`

```kdl
observability {
    metrics {
        enabled #true
        address "0.0.0.0:9090"
        path "/metrics"
    }
}
```

---

### `high-cardinality`

Enable high-cardinality metrics labels.

**Context:** `metrics`
**Default:** `#false`

```kdl
metrics {
    high-cardinality #true
}
```

---

### `logging`

Logging configuration.

**Context:** `observability`

```kdl
observability {
    logging {
        level "info"
        format "json"
    }
}
```

---

### `format`

Log format. Options: `"json"`, `"pretty"`.

**Context:** `logging`
**Default:** `"json"`

```kdl
logging {
    format "pretty"
}
```

---

### `timestamps`

Include timestamps in logs.

**Context:** `logging`
**Default:** `#true`

```kdl
logging {
    timestamps #true
}
```

---

### `file`

Log output file path.

**Context:** `logging`

```kdl
logging {
    file "/var/log/sentinel/app.log"
}
```

---

### `access-log`

Access log configuration.

**Context:** `logging`

```kdl
logging {
    access-log {
        enabled #true
        file "/var/log/sentinel/access.log"
        format "json"
    }
}
```

---

### `error-log`

Error log configuration.

**Context:** `logging`

```kdl
logging {
    error-log {
        enabled #true
        file "/var/log/sentinel/error.log"
        level "warn"
    }
}
```

---

### `audit-log`

Audit log configuration.

**Context:** `logging`

```kdl
logging {
    audit-log {
        enabled #true
        file "/var/log/sentinel/audit.log"
        log-blocked #true
    }
}
```

---

### `tracing`

Distributed tracing configuration.

**Context:** `observability`

```kdl
observability {
    tracing {
        backend "otlp" {
            endpoint "http://localhost:4317"
        }
        sampling-rate 0.01
        service-name "sentinel"
    }
}
```

---

### `sampling-rate`

Tracing sampling rate (0.0 to 1.0).

**Context:** `tracing`
**Default:** `0.01`

```kdl
tracing {
    sampling-rate 0.1
}
```

---

### `service-name`

Service name for tracing spans.

**Context:** `tracing`
**Default:** `"sentinel"`

```kdl
tracing {
    service-name "api-gateway"
}
```

---

## See Also

- [Configuration Schema](@/reference/config-schema.md) — Full configuration examples
- [CLI Reference](@/reference/cli.md) — Command-line options
- [Environment Variables](@/reference/env-vars.md) — Environment configuration
