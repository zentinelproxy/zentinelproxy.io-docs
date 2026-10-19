+++
title = "Directive Index"
weight = 1
description = "Complete reference for all Zentinel configuration directives"
updated = 2026-10-19
+++

Complete reference for all Zentinel configuration directives, verified against the source code. Each entry includes syntax, context, default values, and usage examples.

---

## Root-Level Blocks
<small class="docs-ref">[File Format](/configuration/file-format/)</small>
<small class="source-ref">[`crates/config/src/lib.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/lib.rs)</small>

### `schema-version`

Configuration schema version for compatibility checking. Zentinel validates that the config matches the expected schema version.

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
    graceful-shutdown-timeout-secs 30
    auto-reload #true
}
```

---

### `listeners`

Top-level block containing all listener definitions. At least one listener is required for Zentinel to accept traffic.

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
        target "10.0.1.1:8080"
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
        unix-socket "/var/run/auth.sock"
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

{% callout(type="warning", title="Not wired into the runtime") %}
As of 26.10_3 the top-level `waf` block is parsed but the WAF engine is not
connected to the proxy: configuration validation **rejects** any `mode` other
than `"off"` (`crates/config/src/validation.rs`), so the examples in this
section and under [WAF Directives](#waf-directives) do not load as written.
Inspect traffic with a WAF agent attached to routes through
[filters](#filter) instead.
{% end %}

```fragment,kdl
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
    max-body-size 10485760    // bytes
    max-header-size 8192      // bytes
    max-header-count 100
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
    max-size 104857600  // bytes
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

### `namespace`

Top-level block for namespace-based configuration isolation. Each namespace is
its own top-level `namespace "<id>"` node; there is no `namespaces` wrapper.

**Context:** root

```kdl
namespace "api" {
    routes { }
    upstreams { }
}
```

---

## System Directives
<small class="docs-ref">[Server](/configuration/server/)</small>
<small class="source-ref">[`crates/config/src/server.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/server.rs)</small>

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

Accepted but **not applied**: Zentinel does not limit client connections. From
26.10_5, `zentinel test` and `zentinel lint` report it as not applied.

**Context:** `system`

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

When enabled, Zentinel forks to the background after startup, like the
`-d` / `--daemon` flag. Read from the configuration from 26.10_5; before, only
the flag worked.

**Context:** `system`
**Default:** `#false`

```kdl
system {
    daemon #true
    pid-file "/var/run/zentinel.pid"
}
```

---

### `pid-file`

Path to write the process ID file for process management.

**Context:** `system`

```kdl
system {
    pid-file "/var/run/zentinel.pid"
}
```

---

### `user`

Unix user to switch to after binding privileged ports.

**Context:** `system`

```kdl
system {
    user "zentinel"
    group "zentinel"
}
```

---

### `group`

Unix group to switch to after binding privileged ports.

**Context:** `system`

```kdl
system {
    user "zentinel"
    group "zentinel"
}
```

---

### `working-directory`

Directory to change to after startup.

**Context:** `system`

```kdl
system {
    working-directory "/var/lib/zentinel"
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

When enabled, Zentinel watches the configuration file for changes and automatically reloads.

**Context:** `system`
**Default:** `#false`

```kdl
system {
    auto-reload #true
}
```

---

## Listener Directives
<small class="docs-ref">[Listeners](/configuration/listeners/)</small>
<small class="source-ref">[`crates/config/src/server.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/server.rs)</small>

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
    address "0.0.0.0:8080"
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
    address "0.0.0.0:8080"
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
    address "0.0.0.0:8443"
    protocol "h2"
    max-concurrent-streams 250
}
```

---

### `default-route`

Fallback route ID when no other routes match the request.

**Context:** `listener`

```fragment,kdl
listener "http" {
    address "0.0.0.0:8080"
    default-route "not-found"  // id of a route defined under routes
}
```

---

## Listener TLS Directives
<small class="docs-ref">[Listeners](/configuration/listeners/)</small>
<small class="source-ref">[`crates/config/src/server.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/server.rs)</small>

### `tls`

Configures TLS settings for secure connections.

**Context:** `listener`, `upstream`

```kdl
listener "https" {
    address "0.0.0.0:8443"
    protocol "https"
    tls {
        cert-file "/etc/zentinel/server.crt"
        key-file "/etc/zentinel/server.key"
    }
}
```

---

### `cert-file`

Path to the TLS certificate file in PEM format.

**Context:** `tls` (listener)
**Required for HTTPS**

```fragment,kdl
tls {
    cert-file "/etc/zentinel/server.crt"
    key-file "/etc/zentinel/server.key"
}
```

---

### `key-file`

Path to the TLS private key file in PEM format.

**Context:** `tls` (listener)
**Required for HTTPS**

```fragment,kdl
tls {
    cert-file "/etc/zentinel/server.crt"
    key-file "/etc/zentinel/server.key"
}
```

---

### `ca-file`

Path to CA certificate file for verifying client certificates (mTLS).

**Context:** `tls` (listener)

```fragment,kdl
tls {
    ca-file "/etc/zentinel/client-ca.pem"
    client-auth #true
}
```

---

### `min-version`

Minimum TLS version to accept. Options: `"TLS1.2"`, `"TLS1.3"`.

**Context:** `tls` (listener)
**Default:** `"TLS1.2"`

```fragment,kdl
tls {
    min-version "TLS1.2"
}
```

---

### `max-version`

Maximum TLS version to accept.

**Context:** `tls` (listener)

```fragment,kdl
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

```fragment,kdl
tls {
    ca-file "/etc/zentinel/client-ca.pem"
    client-auth #true
}
```

---

### `ocsp-stapling`

Enables OCSP stapling for certificate validation.

**Context:** `tls` (listener)
**Default:** `#true`

```fragment,kdl
tls {
    ocsp-stapling #true
}
```

---

### `session-resumption`

Enables TLS session tickets for faster subsequent connections.

**Context:** `tls` (listener)
**Default:** `#true`

```fragment,kdl
tls {
    session-resumption #true
}
```

---

### `cipher-suite`

Restricts allowed TLS cipher suites. Empty uses secure defaults.

**Context:** `tls` (listener)

```fragment,kdl
tls {
    cipher-suite "TLS_AES_256_GCM_SHA384"
    cipher-suite "TLS_CHACHA20_POLY1305_SHA256"
}
```

---

### `sni`

SNI-based certificate selection block within TLS configuration.

**Context:** `tls` (listener)

```fragment,kdl
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
<small class="docs-ref">[Routes](/configuration/routes/)</small>
<small class="source-ref">[`crates/config/src/routes.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/routes.rs)</small>

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

Categorizes the route for specialized handling. Options: `"web"`, `"api"`, `"static"`, `"builtin"`, `"inference"`.

**Context:** `route`
**Default:** `"web"`

```fragment,kdl
route "files" {
    service-type "static"
    static-files { root "/var/www" }
}

route "llm-api" {
    service-type "inference"
    inference { provider "openai" }
}
```

---

### `upstream`

Target upstream pool ID for proxied requests.

**Context:** `route`

```fragment,kdl
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

```fragment,kdl
route "api" {
    waf-enabled #true
}
```

---

### `websocket`

Enables WebSocket upgrade support.

**Context:** `route`
**Default:** `#false`

```fragment,kdl
route "ws" {
    websocket #true
}
```

---

### `websocket-inspection`

Enables WebSocket frame inspection.

**Context:** `route`
**Default:** `#false`

```fragment,kdl
route "ws" {
    websocket #true
    websocket-inspection #true
}
```

---

### `filters`

List of filter IDs to apply to the route in order.

**Context:** `route`

```fragment,kdl
route "api" {
    filters "rate-limit" "cors" "logging"
}
```

---

## Route Matching Directives
<small class="docs-ref">[Routes](/configuration/routes/)</small>
<small class="source-ref">[`crates/config/src/routes.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/routes.rs)</small>

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

```fragment,kdl
matches {
    path-prefix "/api/v1/"
}
```

---

### `path`

Matches requests with an exact path.

**Context:** `matches`

```fragment,kdl
matches {
    path "/api/v1/status"
}
```

---

### `host`

Matches requests with a specific Host header. Supports wildcards.

**Context:** `matches`

```fragment,kdl
matches {
    host "api.example.com"
}

matches {
    host "*.example.com"
}
```

---

### `method`

Matches requests using an HTTP method.

**Context:** `matches`

```fragment,kdl
matches {
    method "GET"
}
```

From 26.10_5, `method "GET" "POST"` matches either method. Before 26.10_5 only
the first argument was read (`GET` only); use one route per method there.

---

### `header`

Matches requests containing a specific header with optional value.

**Context:** `matches`

```fragment,kdl
matches {
    header "X-API-Version" "v2"
    header "Authorization"
}
```

---

### `query-param`

Matches requests containing a specific query parameter with optional value.

**Context:** `matches`

```fragment,kdl
matches {
    query-param "format" "json"
    query-param "debug"
}
```

---

## Route Policies Directives
<small class="docs-ref">[Routes](/configuration/routes/)</small>
<small class="source-ref">[`crates/config/src/routes.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/routes.rs)</small>

### `policies`

Container for route-level policies including timeouts, headers, and rate limiting.

**Context:** `route`

```fragment,kdl
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

```fragment,kdl
policies {
    timeout-secs 30
}
```

---

### `max-body-size`

Maximum allowed request body size for this route.

**Context:** `policies`

```fragment,kdl
policies {
    max-body-size "10MB"
}
```

---

### `failure-mode`

Behavior when agent/upstream fails. Options: `"open"` (allow), `"closed"` (reject).

**Context:** `policies`, `agent`
**Default:** `"closed"`

```fragment,kdl
policies {
    failure-mode "open"
}
```

---

### `request-headers`

Container for request header manipulation rules.

**Context:** `policies`

```fragment,kdl
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

```fragment,kdl
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

```fragment,kdl
request-headers {
    set { "Host" "backend.internal" }
}
```

---

### `add`

Adds a header value without removing existing values.

**Context:** `request-headers`, `response-headers`

```fragment,kdl
response-headers {
    add { "X-Served-By" "zentinel" }
}
```

---

### `remove`

Removes a header.

**Context:** `request-headers`, `response-headers`

```fragment,kdl
request-headers {
    remove "X-Internal-Token"
}
```

---

### `rate-limit`

Configures rate limiting for the route.

**Context:** `policies`

```fragment,kdl
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

```fragment,kdl
rate-limit {
    requests-per-second 100
}
```

---

### `burst`

Maximum requests allowed to exceed the rate limit temporarily.

**Context:** `rate-limit`
**Default:** equal to `requests-per-second`

```fragment,kdl
rate-limit {
    requests-per-second 100
    burst 500
}
```

---

### `key`

Determines how rate limits are applied. Options: `"client-ip"` (or `"client_ip"`), `"path"`, `"route"`, `"client-ip-and-path"`, `"header:<name>"`.

**Context:** `rate-limit`
**Default:** `"client-ip"`

```fragment,kdl
rate-limit {
    key "header:X-API-Key"
}
```

---

## Route Cache Directives
<small class="docs-ref">[Cache](/configuration/cache/)</small>
<small class="source-ref">[`crates/config/src/routes.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/routes.rs)</small>

### `cache`

Configures response caching for the route. It is a direct child of the
route, not of `policies`; the storage backend is the separate top-level
[`cache`](#cache) block. The other entries in this section go inside the
route's `cache` block.

**Context:** `route`

```kdl
route "api" {
    matches { path-prefix "/api/" }
    upstream "backend"
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

```fragment,kdl
cache {
    default-ttl-secs 7200
}
```

---

### `max-size-bytes`

Maximum size of a cached response.

**Context:** `cache`

```fragment,kdl
cache {
    max-size-bytes 10485760
}
```

---

### `cache-private`

Whether to cache responses with Cache-Control: private.

**Context:** `cache`
**Default:** `#false`

```fragment,kdl
cache {
    cache-private #true
}
```

---

### `stale-while-revalidate-secs`

Serve stale content while revalidating in background.

**Context:** `cache`

```fragment,kdl
cache {
    stale-while-revalidate-secs 60
}
```

---

### `stale-if-error-secs`

Serve stale content if upstream returns error.

**Context:** `cache`

```fragment,kdl
cache {
    stale-if-error-secs 300
}
```

---

### `cacheable-methods`

HTTP methods eligible for caching.

**Context:** `cache`

```fragment,kdl
cache {
    cacheable-methods "GET" "HEAD"
}
```

---

### `cacheable-status-codes`

HTTP status codes eligible for caching.

**Context:** `cache`

```fragment,kdl
cache {
    cacheable-status-codes 200 203 204 206 300 301 308 404 410
}
```

---

### `vary-headers`

Headers to include in cache key.

**Context:** `cache`

```fragment,kdl
cache {
    vary-headers "Accept" "Accept-Encoding"
}
```

---

### `ignore-query-params`

Query parameters to exclude from cache key.

**Context:** `cache`

```fragment,kdl
cache {
    ignore-query-params "utm_source" "utm_medium"
}
```

---

## Static Files Directives
<small class="docs-ref">[Routes](/configuration/routes/)</small>
<small class="source-ref">[`crates/config/src/routes.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/routes.rs)</small>

### `static-files`

Configures static file serving for the route. A static route has no
`upstream`.

**Context:** `route`

```kdl
route "assets" {
    matches { path-prefix "/assets/" }
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

```fragment,kdl
static-files {
    root "/var/www/public"
}
```

---

### `index`

Filename to serve for directory requests.

**Context:** `static-files`
**Default:** `"index.html"`

```fragment,kdl
static-files {
    index "index.html"
}
```

---

### `directory-listing`

Enable HTML directory listing.

**Context:** `static-files`
**Default:** `#false`

```fragment,kdl
static-files {
    directory-listing #true
}
```

---

### `cache-control`

Cache-Control header for static responses.

**Context:** `static-files`

```fragment,kdl
static-files {
    cache-control "public, max-age=86400"
}
```

---

### `compress`

Enable automatic compression (gzip, brotli).

**Context:** `static-files`
**Default:** `#true`

```fragment,kdl
static-files {
    compress #true
}
```

---

### `fallback`

File to serve when requested file doesn't exist (SPA support).

**Context:** `static-files`

```fragment,kdl
static-files {
    root "/var/www/app"
    fallback "index.html"
}
```

---

### `mime-types`

Not configurable: no KDL parser reads `mime-types` as of 26.10_3 (the static
files parser always uses the built-in MIME table).

---

## Circuit Breaker Directives
<small class="docs-ref">[Upstreams](/configuration/upstreams/)</small>
<small class="source-ref">[`crates/config/src/kdl/circuitbreaker_helper.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/kdl/circuitbreaker_helper.rs)</small>

### `circuit-breaker`

Configures circuit breaker to prevent cascading failures. Valid inside an
`upstream` or an `agent`; a route has no `circuit-breaker`.

**Context:** `upstream`, `agent`

```kdl
upstream "backend" {
    target "127.0.0.1:3000"
    circuit-breaker {
        failure-threshold 5
        success-threshold 2
        timeout-seconds 30
    }
}
```

---

### `failure-threshold`

Consecutive failures before circuit opens.

**Context:** `circuit-breaker`
**Default:** `5`

```fragment,kdl
circuit-breaker {
    failure-threshold 10
}
```

---

### `success-threshold`

Consecutive successes to close circuit.

**Context:** `circuit-breaker`
**Default:** `2`

```fragment,kdl
circuit-breaker {
    success-threshold 3
}
```

---

### `timeout-seconds`

Time circuit remains open before half-open test.

**Context:** `circuit-breaker`
**Default:** `30`

```fragment,kdl
circuit-breaker {
    timeout-seconds 60
}
```

---

### `half-open-max-requests`

Requests allowed in half-open state.

**Context:** `circuit-breaker`
**Default:** `3`

```fragment,kdl
circuit-breaker {
    half-open-max-requests 5
}
```

---

## Retry Policy Directives
<small class="docs-ref">[Routes](/configuration/routes/)</small>
<small class="source-ref">[`crates/config/src/routes.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/routes.rs)</small>

### `retry-policy`

Configures automatic retry behavior for failed requests.

`max-attempts` is the only supported key; it bounds upstream peer-selection
attempts. Per-attempt timeouts, backoff tuning and status-code retries are not
implemented, and any other key is rejected at parse time. Tracked in
[zentinel#279](https://github.com/zentinelproxy/zentinel/issues/279).

**Context:** `route`

```fragment,kdl
retry-policy {
    max-attempts 3
}
```

---

### `max-attempts`

Maximum retry attempts including initial try.

**Context:** `retry-policy`
**Default:** `3`

```fragment,kdl
retry-policy {
    max-attempts 5
}
```

---

## Shadow/Traffic Mirroring Directives
<small class="docs-ref">[Routes](/configuration/routes/)</small>
<small class="source-ref">[`crates/config/src/routes.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/routes.rs)</small>

### `shadow`

Configures traffic mirroring to a shadow upstream.

**Context:** `route`

```kdl
route "api" {
    matches { path-prefix "/api/" }
    upstream "backend"
    shadow {
        upstream "shadow-backend"
        percentage 10.0
    }
}
```

---

### `percentage`

Percentage of traffic to mirror (0.0 to 100.0).

**Context:** `shadow`
**Default:** `100.0`

```fragment,kdl
shadow {
    percentage 50.0
}
```

---

### `sample-header`

Only mirror requests with this header/value.

**Context:** `shadow`

```fragment,kdl
shadow {
    sample-header "X-Canary" "true"
}
```

---

### `buffer-body`

Buffer request body for mirroring, up to `max-body-bytes` (default `1048576`).

**Context:** `shadow`
**Default:** `#false`

```fragment,kdl
shadow {
    buffer-body #true
    max-body-bytes 1048576
}
```

---

## Error Pages Directives
<small class="docs-ref">[Routes](/configuration/routes/)</small>
<small class="source-ref">[`crates/config/src/kdl/routes.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/kdl/routes.rs)</small>

### `error-pages`

**Not configurable.** No KDL parser reads `error-pages` as of 26.10_3: both the
single-file and the multi-file parser set a route's error pages to none, and
the loader reports the block as an unrecognised route directive. Error
responses use the default format for the route's `service-type` (JSON for
`api`, `builtin` and `inference` routes, HTML for `web` and `static`). The `default-format`,
`include-stack-trace`, `template-dir` and `pages` settings that earlier
versions of this page listed have no effect.

---

## Upstream Directives
<small class="docs-ref">[Upstreams](/configuration/upstreams/)</small>
<small class="source-ref">[`crates/config/src/upstreams.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/upstreams.rs)</small>

### `upstream`

Defines a group of backend servers.

**Context:** `upstreams`

```kdl
upstreams {
    upstream "backend" {
        target "127.0.0.1:8080"
        load-balancing "round_robin"
    }
}
```

---

### `load-balancing`

Algorithm for distributing requests across upstream targets.

**Context:** `upstream`
**Default:** `"round_robin"`

**Options:**

| Algorithm | Description |
|-----------|-------------|
| `round_robin` | Sequential rotation (default) |
| `least_connections` | Fewest active connections |
| `weighted_least_conn` | Connection/weight ratio |
| `random` | Random selection |
| `ip_hash` | Client IP based routing |
| `weighted` | Weight-proportional selection |
| `consistent_hash` | Ring-based consistent hashing |
| `maglev` | Google's Maglev consistent hashing |
| `power_of_two_choices` | Best of two random targets |
| `adaptive` | Response time based |
| `peak_ewma` | EWMA latency tracking |
| `locality_aware` | Zone-aware with fallback |
| `deterministic_subset` | Subset per proxy (large clusters) |
| `least_tokens_queued` | LLM/inference workloads |

```kdl
upstream "backend" {
    target "10.0.1.1:8080"
    target "10.0.1.2:8080"
    load-balancing "least_connections"
}
```

See [Upstreams - Load Balancing](/configuration/upstreams/#load-balancing) for detailed algorithm documentation.

---

### `targets`

Optional container for upstream target definitions; `target` nodes may also be
written directly in the `upstream` block, as below.

**Context:** `upstream`

```kdl
upstream "backend" {
    target "10.0.1.1:8080"
    target "10.0.1.2:8080"
}
```

---

### `target`

Defines an individual backend server. The address is the first argument (or
an `address` property/child); `weight` is the only other setting.

**Context:** `upstream`, `targets`

```fragment,kdl
target "10.0.1.1:8080" weight=1
```

---

### `weight`

Relative weight for load balancing.

**Context:** `target`
**Default:** `1`

```fragment,kdl
target "10.0.1.1:8080" weight=3
```

---

### `max-requests`, `metadata`

Not configurable from KDL: the target parser reads only the address and
`weight` (`RECOGNIZED_TARGET_KEYS` in `crates/config/src/kdl/upstreams.rs`), so
`max-requests` and `metadata` on a target are ignored.

---

## Health Check Directives
<small class="docs-ref">[Upstreams](/configuration/upstreams/)</small>
<small class="source-ref">[`crates/config/src/upstreams.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/upstreams.rs)</small>

### `health-check`

Configures active health checking for upstream targets. Check-specific
settings (`path`, `expected-status`, `host`) go in a block on the `type` node.

**Context:** `upstream`

```kdl
upstream "backend" {
    target "10.0.1.1:8080"
    health-check {
        type "http" {
            path "/health"
        }
        interval-secs 10
    }
}
```

---

### `type`

Health check protocol. Options: `"http"`, `"tcp"`, `"grpc"`, `"inference"`, `"mcp"`.

**Context:** `health-check`
**Default:** `"tcp"` (when no `type` is given)

```fragment,kdl
health-check {
    type "tcp"
}
```

---

### `interval-secs`

Time between health check probes.

**Context:** `health-check`
**Default:** `10`

```fragment,kdl
health-check {
    interval-secs 5
}
```

---

### `healthy-threshold`

Successful checks to mark target healthy.

**Context:** `health-check`
**Default:** `2`

```fragment,kdl
health-check {
    healthy-threshold 3
}
```

---

### `unhealthy-threshold`

Failed checks to mark target unhealthy.

**Context:** `health-check`
**Default:** `3`

```fragment,kdl
health-check {
    unhealthy-threshold 2
}
```

---

### `expected-status`

HTTP status indicating healthy (for HTTP checks).

**Context:** `type "http"` (inside `health-check`)
**Default:** `200`

```fragment,kdl
health-check {
    type "http" {
        path "/health"
        expected-status 200
    }
}
```

---

## Connection Pool Directives
<small class="docs-ref">[Upstreams](/configuration/upstreams/)</small>
<small class="source-ref">[`crates/config/src/upstreams.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/upstreams.rs)</small>

### `connection-pool`

Configures connection pooling to upstream targets.

**Context:** `upstream`

```fragment,kdl
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

```fragment,kdl
connection-pool {
    max-idle 30
}
```

---

### `idle-timeout-secs`

Time before idle connection is closed.

**Context:** `connection-pool`
**Default:** `60`

```fragment,kdl
connection-pool {
    idle-timeout-secs 120
}
```

---

### `max-lifetime-secs`

Maximum connection lifetime.

**Context:** `connection-pool`
**Default:** `300`

```fragment,kdl
connection-pool {
    max-lifetime-secs 3600
}
```

---

## Upstream Timeouts Directives
<small class="docs-ref">[Upstreams](/configuration/upstreams/)</small>
<small class="source-ref">[`crates/config/src/upstreams.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/upstreams.rs)</small>

### `timeouts`

Container for upstream timeout configuration.

**Context:** `upstream`

```fragment,kdl
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

```fragment,kdl
timeouts {
    connect-secs 5
}
```

---

### `request-secs`

Maximum time for complete request-response cycle.

**Context:** `timeouts`
**Default:** `60`

```fragment,kdl
timeouts {
    request-secs 120
}
```

---

### `read-secs`

Maximum time waiting for response data.

**Context:** `timeouts`
**Default:** `30`

```fragment,kdl
timeouts {
    read-secs 60
}
```

---

### `write-secs`

Maximum time writing request data.

**Context:** `timeouts`
**Default:** `30`

```fragment,kdl
timeouts {
    write-secs 60
}
```

---

## Upstream TLS Directives
<small class="docs-ref">[Upstreams](/configuration/upstreams/)</small>
<small class="source-ref">[`crates/config/src/upstreams.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/upstreams.rs)</small>

### `sni`

SNI hostname for upstream TLS connections.

**Context:** `tls` (upstream)

```kdl
upstream "backend" {
    target "10.0.1.1:443"
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

```fragment,kdl
tls {
    insecure-skip-verify #true
}
```

---

### `client-cert`

Path to client certificate for mTLS to upstream.

**Context:** `tls` (upstream)

```fragment,kdl
tls {
    client-cert "/etc/zentinel/client.crt"
    client-key "/etc/zentinel/client.key"
}
```

---

### `client-key`

Path to client private key for mTLS.

**Context:** `tls` (upstream)

```fragment,kdl
tls {
    client-cert "/etc/zentinel/client.crt"
    client-key "/etc/zentinel/client.key"
}
```

---

### `ca-cert`

Path to CA certificate for upstream verification.

**Context:** `tls` (upstream)

```fragment,kdl
tls {
    ca-cert "/etc/zentinel/ca.pem"
}
```

---

## HTTP Version Directives
<small class="docs-ref">[Upstreams](/configuration/upstreams/)</small>
<small class="source-ref">[`crates/config/src/upstreams.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/upstreams.rs)</small>

### `http-version`

Configures HTTP version settings for upstream connections.

**Context:** `upstream`

```fragment,kdl
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

```fragment,kdl
http-version {
    min-version 2
}
```

---

### `max-version`

Maximum HTTP version.

**Context:** `http-version`
**Default:** `2`

```fragment,kdl
http-version {
    max-version 2
}
```

---

### `h2-ping-interval`

HTTP/2 ping interval in seconds (0 to disable). The key has no `-secs` suffix.

**Context:** `http-version`
**Default:** `0`

```fragment,kdl
http-version {
    h2-ping-interval 30
}
```

---

### `max-h2-streams`

Maximum HTTP/2 streams per connection.

**Context:** `http-version`
**Default:** `100`

```fragment,kdl
http-version {
    max-h2-streams 200
}
```

---

## Agent Directives
<small class="docs-ref">[Agents](/configuration/agents/)</small>
<small class="source-ref">[`crates/config/src/agents.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/agents.rs)</small>

### `agent`

Defines an external processing agent.

**Context:** `agents`

```kdl
agents {
    agent "auth" {
        type "auth"
        unix-socket "/var/run/zentinel/auth.sock"
        timeout-ms 1000
        failure-mode "closed"
    }
}
```

Every agent needs exactly one transport: `unix-socket`, `grpc` or `http` (see
[Transport Directives](#transport-directives)). The single-setting examples
below omit it.

---

### `type` (agent)

Agent type. Common: `"waf"`, `"auth"`, `"rate_limit"`, or custom string.

**Context:** `agent`
**Required**

```fragment,kdl
agent "auth" {
    type "auth"
}
```

---

### `timeout-ms`

Maximum time to wait for agent response.

**Context:** `agent`
**Default:** `1000`

```fragment,kdl
agent "auth" {
    timeout-ms 50
}
```

---

### `max-request-body-bytes`

Maximum request body to send to agent.

**Context:** `agent`

```fragment,kdl
agent "waf" {
    max-request-body-bytes 1048576
}
```

---

### `max-response-body-bytes`

Maximum response body to send to agent.

**Context:** `agent`

```fragment,kdl
agent "logger" {
    max-response-body-bytes 4096
}
```

---

### `request-body-mode`

How to handle request body. Options: `"buffer"`, `"stream"`, `"hybrid"`.

**Context:** `agent`
**Default:** `"buffer"`

```fragment,kdl
agent "waf" {
    request-body-mode "buffer"
}
```

---

### `response-body-mode`

How to handle response body. Options: `"buffer"`, `"stream"`, `"hybrid"`.

**Context:** `agent`
**Default:** `"buffer"`

```fragment,kdl
agent "logger" {
    response-body-mode "stream"
}
```

---

### `chunk-timeout-ms`

Timeout per body chunk when streaming.

**Context:** `agent`
**Default:** `5000`

```fragment,kdl
agent "waf" {
    chunk-timeout-ms 2000
}
```

---

### `max-concurrent-calls`

Maximum concurrent calls to agent.

**Context:** `agent`
**Default:** `100`

```fragment,kdl
agent "auth" {
    max-concurrent-calls 200
}
```

---

### `events`

Request lifecycle events the agent receives.

**Context:** `agent`

Available: `"request_headers"`, `"request_body"`, `"response_headers"`, `"response_body"`, `"log"`, `"websocket_frame"`

```fragment,kdl
agent "logger" {
    events "request_headers" "response_headers"
}
```

---

### `config`

Agent-specific configuration passed as JSON.

**Context:** `agent`

```fragment,kdl
agent "custom" {
    config {
        custom-field "value"
    }
}
```

---

## Transport Directives
<small class="docs-ref">[Agents](/configuration/agents/)</small>
<small class="source-ref">[`crates/config/src/kdl/mod.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/kdl/mod.rs)</small>

An agent's transport is one of three child nodes. Each takes its address as
the first argument or as a property. There is no `transport` block.

### `unix-socket`

Unix domain socket path (argument or `path=`).

**Context:** `agent`

```kdl
agent "auth" {
    unix-socket "/var/run/zentinel/auth.sock"
}
```

---

### `grpc`

gRPC endpoint (argument or `address=`). May contain a `tls` block.

**Context:** `agent`

```kdl
agent "waf" {
    grpc "http://127.0.0.1:50051"
}
```

---

### `http`

HTTP endpoint (argument or `url=`). May contain a `tls` block.

**Context:** `agent`

```kdl
agent "policy" {
    http "http://127.0.0.1:8888"
}
```

---

## Filter Directives
<small class="docs-ref">[Filters](/configuration/filters/)</small>
<small class="source-ref">[`crates/config/src/filters.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/filters.rs)</small>

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

Filter type. Options: `"rate-limit"`, `"agent"`, `"headers"`, `"compress"`, `"cors"`, `"timeout"`, `"log"`, `"geo"`, `"redirect"`, `"url-rewrite"`.

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
Backend settings are flat keys on the filter (`redis-url`, `redis-prefix`,
`redis-pool-size`, `redis-timeout-ms`, `redis-fallback-local`, and the
`memcached-*` equivalents), not a nested block.

**Context:** `filter` (rate-limit)
**Default:** `"local"`

```kdl
filter "rate-limit" {
    type "rate-limit"
    max-rps 100
    backend "redis"
    redis-url "redis://127.0.0.1:6379"
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

Compression algorithms, as one comma-separated string. Options: `gzip`, `br`
(or `brotli`), `deflate`, `zstd`.

**Context:** `filter` (compress)
**Default:** `"gzip,br"`

```kdl
filter "compress" {
    type "compress"
    algorithms "gzip,br"
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

Not configurable from KDL as of 26.10_3: the compress filter always uses
`text/html`, `text/css`, `application/json` and `application/javascript`.

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

### CORS settings (`allowed-origins`, `allowed-methods`, `allowed-headers`, `allow-credentials`, `max-age-secs`)

Not configurable from KDL as of 26.10_3: a `type "cors"` filter is built with
default settings and the parser reads none of these keys
(`crates/config/src/kdl/filters.rs`). Set CORS headers with a `headers`
filter or the route's `policies { response-headers { ... } }` instead.

---

### `database-path`

GeoIP database path.

**Context:** `filter` (geo)

```kdl
filter "geo" {
    type "geo"
    database-path "/etc/zentinel/GeoLite2-Country.mmdb"
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
    database-path "/etc/zentinel/GeoLite2-Country.mmdb"
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
    database-path "/etc/zentinel/GeoLite2-Country.mmdb"
    action "block"
    countries "RU,CN"
}
```

---

### `countries`

Country codes for geo filter (ISO 3166-1 alpha-2), as one comma-separated
string.

**Context:** `filter` (geo)

```kdl
filter "geo" {
    type "geo"
    database-path "/etc/zentinel/GeoLite2-Country.mmdb"
    action "allow"
    countries "US,CA,GB"
}
```

---

## WAF Directives
<small class="source-ref">[`crates/config/src/waf.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/waf.rs)</small>

{% callout(type="warning", title="Not wired into the runtime") %}
The top-level `waf` block is parsed but not connected to the proxy as of
26.10_3. Validation rejects every `mode` except `"off"`, and the mode defaults
to `"prevention"`, so a `waf` block without `mode "off"` stops the
configuration from loading. The settings below are listed for reference only;
the examples are fragments. Use a WAF agent attached to routes through
[filters](#filter) to inspect traffic.
{% end %}

### `engine`

WAF engine. Options: `"modsecurity"`, `"coraza"`, or custom.

**Context:** `waf`
**Required**

```fragment,kdl
waf {
    engine "coraza"
}
```

---

### `mode`

WAF mode. Options: `"off"`, `"detection"`, `"prevention"`.

**Context:** `waf`
**Default:** `"prevention"` — which validation rejects (see below)

```fragment,kdl
waf {
    mode "detection"
}
```

---

### `audit-log`

Enable WAF audit logging.

**Context:** `waf`
**Default:** `#true`

```fragment,kdl
waf {
    audit-log #true
}
```

---

### `ruleset`

WAF ruleset configuration.

**Context:** `waf`

```fragment,kdl
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

```fragment,kdl
ruleset {
    crs-version "3.3.4"
}
```

---

### `paranoia-level`

CRS paranoia level (1-4).

**Context:** `ruleset`
**Default:** `1`

```fragment,kdl
ruleset {
    paranoia-level 2
}
```

---

### `anomaly-threshold`

Anomaly score threshold for blocking.

**Context:** `ruleset`
**Default:** `5`

```fragment,kdl
ruleset {
    anomaly-threshold 10
}
```

---

### `exclusions`

WAF rule exclusions. They belong to the `ruleset` block (an `exclusions`
wrapper or `exclusion` nodes listed directly).

**Context:** `ruleset`

```fragment,kdl
waf {
    ruleset {
        exclusions {
            exclusion {
                rule-ids "920350" "920420"
                scope "global"
            }
        }
    }
}
```

---

### `body-inspection`

WAF body inspection policy.

**Context:** `waf`

```fragment,kdl
waf {
    body-inspection {
        inspect-request-body #true
        inspect-response-body #false
        max-inspection-bytes 1048576
    }
}
```

---

## Inference Directives
<small class="docs-ref">[Inference](/examples/inference-routing/)</small>
<small class="source-ref">[`crates/config/src/routes.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/routes.rs)</small>

### `inference`

Configures inference/LLM-specific settings for a route, including token-based rate limiting, budget tracking, cost attribution, model routing, and semantic guardrails.

**Context:** `route`

```kdl
route "openai-proxy" {
    matches { path-prefix "/v1/" }
    upstream "openai"
    inference {
        provider "openai"
        rate-limit {
            tokens-per-minute 100000
        }
    }
}
```

---

### `provider`

LLM provider type for token counting and API parsing. Options: `"openai"`, `"anthropic"`, `"generic"`.

**Context:** `inference`
**Default:** `"generic"`

```fragment,kdl
inference {
    provider "openai"
}
```

---

### `rate-limit` (inference)

Token-based rate limiting for inference routes. Settings: `tokens-per-minute`
(required), `requests-per-minute`, `burst-tokens` (default `10000`) and
`estimation-method` (`"chars"` (default), `"words"`, `"tiktoken"`). There is no
`key` setting here.

**Context:** `inference`

```fragment,kdl
inference {
    rate-limit {
        tokens-per-minute 100000
        requests-per-minute 1000
        burst-tokens 20000
    }
}
```

---

### `tokens-per-minute`

Maximum tokens per minute for inference rate limiting.

**Context:** `rate-limit` (inference)

```fragment,kdl
rate-limit {
    tokens-per-minute 50000
}
```

---

### `requests-per-minute`

Maximum requests per minute (in addition to token limits).

**Context:** `rate-limit` (inference)

```fragment,kdl
rate-limit {
    tokens-per-minute 50000
    requests-per-minute 500
}
```

---

### `budget`

Token budget tracking over one period, with alert thresholds. One `budget`
block per route sets one `limit` for one `period`.

**Context:** `inference`

```fragment,kdl
inference {
    provider "openai"
    budget {
        period "monthly"          // hourly, daily (default), monthly, or seconds
        limit 100000000           // tokens per period (required)
        alert-thresholds 0.8 0.9  // default 0.80 0.90 0.95
        enforce #true             // reject when exhausted (default #true)
        rollover #false
    }
}
```

The `hourly-limit`, `daily-limit`, `monthly-limit` and `alert-threshold` keys
listed here before are not read by any parser; use `period` plus `limit`, and
`alert-thresholds`.

---

### `period`

Budget period. Options: `"hourly"`, `"daily"`, `"monthly"`, or a number of seconds.

**Context:** `budget`
**Default:** `"daily"`

---

### `limit`

Tokens allowed per period.

**Context:** `budget`
**Required**

---

### `alert-thresholds`

Fractions of the budget (0.0–1.0) at which alerts are emitted.

**Context:** `budget`
**Default:** `0.80 0.90 0.95`

---

### `cost-attribution`

Per-model pricing for cost tracking and metrics. Prices are per **million**
tokens, in a `pricing` block.

**Context:** `inference`

```fragment,kdl
inference {
    provider "openai"
    cost-attribution {
        enabled #true
        currency "USD"
        default-input-cost 1.0     // per million tokens, for unmatched models
        default-output-cost 2.0
        pricing {
            model "gpt-4*" {
                input-cost-per-million 30.0
                output-cost-per-million 60.0
            }
            model "gpt-3.5*" {
                input-cost-per-million 1.5
                output-cost-per-million 2.0
            }
        }
    }
}
```

---

### `input-cost-per-million`, `output-cost-per-million`

Cost per million input/output tokens for a `model` pattern in
`cost-attribution { pricing { ... } }`. Both are required on each `model`
entry; an optional `currency` overrides the block's currency. (There is no
`input-cost-per-1k` / `output-cost-per-1k`.)

**Context:** `model` (`pricing`)

---

### `model-routing`

Route requests to different upstreams based on model name, with `model`
entries (glob pattern, `upstream=`, optional `provider=`).

**Context:** `inference`

```fragment,kdl
inference {
    provider "openai"
    model-routing {
        model "gpt-4*" upstream="openai-primary"
        model "claude*" upstream="anthropic" provider="anthropic"
        default-upstream "openai-fallback"
    }
}
```

---

### `default-upstream`

Fallback upstream when no model route matches.

**Context:** `model-routing`

```fragment,kdl
model-routing {
    default-upstream "generic-backend"
}
```

---

### `fallback`

Automatic failover to other upstreams. A route-level block (a direct child of
the route, not of `inference`).

**Context:** `route`

```fragment,kdl
fallback {
    max-attempts 2
    triggers {
        on-health-failure #true
        on-budget-exhausted #true
        on-error-codes 429 500 502 503 504
        on-connection-error #true
    }
    fallback-upstream "anthropic" {
        skip-if-unhealthy #true
        model-mapping {
            "gpt-4" "claude-3-opus-20240229"
            "gpt-3.5-turbo" "claude-3-haiku-20240307"
        }
    }
}
```

---

### `model-mapping`

Maps models between providers for cross-provider failover.

**Context:** `fallback-upstream`

```fragment,kdl
fallback-upstream "anthropic" {
    model-mapping {
        "gpt-4" "claude-3-opus-20240229"
    }
}
```

---

### `guardrails`

Semantic guardrails for prompt injection detection and PII scanning.

**Context:** `inference`

```fragment,kdl
inference {
    guardrails {
        prompt-injection {
            enabled #true
            agent "prompt-guard"
            action "block"
        }
        pii-detection {
            enabled #true
            agent "pii-scanner"
            categories "ssn" "credit-card" "email"
        }
    }
}
```

---

### `prompt-injection`

Prompt injection detection configuration for request-phase inspection.

**Context:** `guardrails`

```fragment,kdl
prompt-injection {
    enabled #true
    agent "prompt-guard"
    action "block"
    block-status 400
    block-message "Request blocked: potential prompt injection"
    timeout-ms 500
    failure-mode "open"
}
```

---

### `action` (prompt-injection)

Action when prompt injection is detected. Options: `"block"`, `"log"`, `"warn"`.

**Context:** `prompt-injection`
**Default:** `"log"`

```fragment,kdl
prompt-injection {
    action "warn"
}
```

---

### `block-status`

HTTP status code returned when blocking.

**Context:** `prompt-injection`
**Default:** `400`

```fragment,kdl
prompt-injection {
    action "block"
    block-status 403
}
```

---

### `block-message`

Message returned in response body when blocking.

**Context:** `prompt-injection`

```fragment,kdl
prompt-injection {
    block-message "Your request was blocked for security reasons"
}
```

---

### `pii-detection`

PII detection configuration for response-phase inspection.

**Context:** `guardrails`

```fragment,kdl
pii-detection {
    enabled #true
    agent "pii-scanner"
    action "log"
    categories "ssn" "credit-card" "email" "phone"
    timeout-ms 1000
    failure-mode "open"
}
```

---

### `action` (pii-detection)

Action when PII is detected. Options: `"log"`, `"redact"`, `"block"`.

**Context:** `pii-detection`
**Default:** `"log"`

```fragment,kdl
pii-detection {
    action "redact"
}
```

---

### `categories`

PII categories to detect. Options: `"ssn"`, `"credit-card"`, `"email"`, `"phone"`, `"address"`, `"name"`, `"dob"`, `"passport"`, `"driver-license"`, `"bank-account"`, `"ip-address"`, `"medical-record"`.

**Context:** `pii-detection`

```fragment,kdl
pii-detection {
    categories "ssn" "credit-card" "email"
}
```

---

## Limits Directives
<small class="docs-ref">[Limits](/configuration/limits/)</small>
<small class="source-ref">[`crates/common/src/limits.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/common/src/limits.rs)</small>

A configuration file's `limits` block reads exactly the six keys below. The
`-bytes` spellings (`max-header-size-bytes`, `max-body-size-bytes`) and the
other keys earlier versions of this index listed (`max-connections-per-route`,
`max-queued-requests`, `max-requests-per-second-*`, `max-memory-bytes`, ...)
belong to the directory-configuration loader, which the `zentinel` command
cannot load ([#541](https://github.com/zentinelproxy/zentinel/issues/541)).
From 26.10_5, `zentinel test` and `zentinel lint` report them as ignored.

### `max-header-size`

Maximum total size of the request headers (names and values), in bytes. `1048576` or more disables the check.

**Context:** `limits`
**Default:** `8192`

```kdl
limits {
    max-header-size 16384
}
```

---

### `max-header-count`

Maximum number of request headers. `1048576` or more disables the check.

**Context:** `limits`
**Default:** `100`

```kdl
limits {
    max-header-count 200
}
```

---

### `max-body-size`

Maximum request body size, in bytes. A route's `policies { max-body-size }` can lower it for that route; the smaller of the two applies. A body over it gets `413` (from 26.10_5; `500` before).

**Context:** `limits`
**Default:** `10485760`

```kdl
limits {
    max-body-size 10485760
}
```

---

### `max-connections-per-client`

Parsed but **not applied**: Zentinel does not limit client connections ([#542](https://github.com/zentinelproxy/zentinel/issues/542)).

**Context:** `limits`
**Default:** `100`

```kdl
limits {
    max-connections-per-client 50
}
```

---

### `max-total-connections`

Parsed but **not applied** ([#542](https://github.com/zentinelproxy/zentinel/issues/542)).

**Context:** `limits`
**Default:** `10000`

```kdl
limits {
    max-total-connections 10000
}
```

---

### `max-in-flight-requests`

Parsed but **not applied** ([#542](https://github.com/zentinelproxy/zentinel/issues/542)).

**Context:** `limits`
**Default:** `10000`

```kdl
limits {
    max-in-flight-requests 10000
}
```

---

## Observability Directives
<small class="docs-ref">[Observability](/configuration/observability/)</small>
<small class="source-ref">[`crates/config/src/observability.rs`](https://github.com/zentinelproxy/zentinel/blob/main/crates/config/src/observability.rs)</small>

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

```fragment,kdl
metrics {
    high-cardinality #true
}
```

---

### `logging`

Logging configuration. As of 26.10_3 `level` and `format` are parsed, but the
log subscriber takes its level from `RUST_LOG` / `--verbose`; validation warns
when they are set to anything but `info` / `json`.

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

```fragment,kdl
logging {
    format "pretty"
}
```

---

### `timestamps`

Include timestamps in logs.

**Context:** `logging`
**Default:** `#true`

```fragment,kdl
logging {
    timestamps #true
}
```

---

### `file`

Not a `logging` setting: application logs always go to stdout/stderr (redirect
them with the service manager). `file` is a setting of `access-log`,
`error-log` and `audit-log`, below.

---

### `access-log`

Access log configuration.

**Context:** `logging`

```fragment,kdl
logging {
    access-log {
        enabled #true
        file "/var/log/zentinel/access.log"
        format "json"
    }
}
```

---

### `error-log`

Error log configuration. **Enabled by default** — writes to `/var/log/zentinel/error.log` at `warn` level without explicit configuration.

**Context:** `logging`

```fragment,kdl
logging {
    error-log {
        enabled #true
        file "/var/log/zentinel/error.log"
        level "warn"
    }
}
```

---

### `audit-log`

Audit log configuration.

**Context:** `logging`

```fragment,kdl
logging {
    audit-log {
        enabled #true
        file "/var/log/zentinel/audit.log"
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
        service-name "zentinel"
    }
}
```

---

### `sampling-rate`

Tracing sampling rate (0.0 to 1.0).

**Context:** `tracing`
**Default:** `0.01`

```fragment,kdl
tracing {
    sampling-rate 0.1
}
```

---

### `service-name`

Service name for tracing spans.

**Context:** `tracing`
**Default:** `"zentinel"`

```fragment,kdl
tracing {
    service-name "api-gateway"
}
```

---

## See Also

- [Configuration Schema](@/reference/config-schema.md) — Full configuration examples
- [CLI Reference](@/reference/cli.md) — Command-line options
- [Environment Variables](@/reference/env-vars.md) — Environment configuration
