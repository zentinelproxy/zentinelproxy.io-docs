+++
title = "Routes"
weight = 4
updated = 2026-10-20
+++

The `routes` block defines how incoming requests are matched and forwarded to upstreams or handlers. Routes are evaluated by priority, with higher priority routes checked first.

## Basic Configuration

```kdl
routes {
    route "api" {
        priority 100
        matches {
            path-prefix "/api/"
        }
        upstream "backend"
    }

    route "static" {
        priority 50
        matches {
            path-prefix "/static/"
        }
        service-type "static"
        static-files {
            root "/var/www/static"
        }
    }
}
```

## Route Options

### Priority

```kdl
route "api" {
    priority 100
    matches { path-prefix "/api/" }
    upstream "backend"
}
```

Higher priority routes are evaluated first. When multiple routes could match, the highest priority wins.

| Priority | Typical Use |
|----------|-------------|
| 1000+ | Health checks, admin endpoints |
| 100-999 | API routes |
| 50-99 | Static files |
| 1-49 | Catch-all routes |

### Match Conditions

Routes support multiple match conditions. All conditions within a route must match (AND logic).

Every `matches` example below goes inside a `route` block.

#### Path Matching

```fragment,kdl
matches {
    // Exact path match
    path "/api/v1/users"

    // Prefix match
    path-prefix "/api/"

    // Regex match
    path-regex "^/api/v[0-9]+/.*$"
}
```

| Match Type | Example | Matches |
|------------|---------|---------|
| `path` | `/users` | `/users` only |
| `path-prefix` | `/api/` | `/api/`, `/api/users`, `/api/v1/data` |
| `path-regex` | `^/user/[0-9]+$` | `/user/123`, `/user/456` |

#### Host Matching

```fragment,kdl
matches {
    host "api.example.com"
}
```

Match by the `Host` header. Useful for virtual hosting.

#### Method Matching

```fragment,kdl
matches {
    method "GET"
}
```

Match an HTTP method. From 26.10_5 `method` takes one or more values and
matches any of them: `method "GET" "POST"` matches `GET` and `POST`. Write them
on one line; two `method` lines are two conditions that must both match, so
nothing matches them. Before 26.10_5 only the first value was read
(`method "GET" "POST"` matched `GET` only); on those releases use one route per
method.

#### Header Matching

```fragment,kdl
matches {
    // Match if header exists
    header "X-Api-Key"

    // Match header with specific value
    header "X-Api-Version" "2"
}
```

#### Query Parameter Matching

```fragment,kdl
matches {
    // Match if parameter exists
    query-param "debug"

    // Match parameter with value
    query-param "format" "json"
}
```

### Service Types

```kdl
route "api" {
    matches { path-prefix "/" }
    upstream "backend"
    service-type "web"  // Default
}
```

| Type | Description |
|------|-------------|
| `web` | Standard HTTP proxy (default) |
| `api` | API service with request schema validation (`api-schema`) |
| `static` | Static file serving |
| `builtin` | Built-in handlers |
| `inference` | LLM inference routing |

> **How the type is decided.** It is implied by the route's blocks:
> `static-files` makes it `static`, a recognised `builtin-handler` makes it
> `builtin`, `api-schema` makes it `api`, `inference` makes it `inference`, and
> anything else is `web`. An explicit `service-type` is applied where the
> blocks allow it (`api` needs no block). A value that is not a type, or that
> the blocks contradict, keeps the implied type and is reported by
> `zentinel lint` as being ignored. Before 26.10_4, `service-type` was accepted
> but never read.

#### Static File Serving

```kdl
route "assets" {
    matches {
        path-prefix "/static/"
    }
    service-type "static"
    static-files {
        root "/var/www/static"
        index "index.html"
        directory-listing #false
        cache-control "public, max-age=86400"
        compress #true
        fallback "index.html"  // For SPAs
    }
}
```

| Option | Default | Description |
|--------|---------|-------------|
| `root` | Required | Root directory for files |
| `index` | `index.html` | Default index file |
| `directory-listing` | `false` | Enable directory browsing |
| `cache-control` | `public, max-age=3600` | Cache-Control header |
| `compress` | `true` | Enable gzip/brotli compression |
| `fallback` | None | Fallback file for 404s (SPA routing) |

#### Built-in Handlers

```kdl
route "health" {
    priority 1000
    matches {
        path "/health"
    }
    service-type "builtin"
    builtin-handler "health"
}
```

| Handler | Path | Description |
|---------|------|-------------|
| `health` | `/health` | Health check (200 OK) |
| `status` | `/status` | JSON status with version/uptime |
| `metrics` | `/metrics` | Prometheus metrics |
| `not-found` | Any | 404 handler |
| `config` | `/admin/config` | Configuration dump (admin) |
| `upstreams` | `/admin/upstreams` | Upstream health status (admin) |

#### API Schema Validation

The `api` service type supports JSON Schema validation for requests and responses. This enables contract validation at the proxy layer using OpenAPI/Swagger specifications or inline JSON schemas.

##### OpenAPI/Swagger File Reference

Reference an OpenAPI 3.0 or Swagger 2.0 specification (YAML or JSON):

```kdl
route "api-v1" {
    matches {
        path-prefix "/api/v1"
    }
    upstream "api-backend"
    service-type "api"
    api-schema {
        schema-file "/etc/zentinel/schemas/api-v1-openapi.yaml"
        validate-requests #true
        validate-responses #false
        strict-mode #false
    }
}
```

The schema file is loaded at startup and used to validate requests against the paths, methods, and schemas defined in the OpenAPI specification.

##### Inline OpenAPI/Swagger Specification

Embed an OpenAPI specification directly in the configuration as a string:

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

routes {
    route "api-v1" {
        matches {
            path-prefix "/api/v1"
        }
        upstream "api-backend"
    }

    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
    }
}

upstreams {
    upstream "api-backend" {
        target "127.0.0.1:3001"
    }
    upstream "backend" {
        target "127.0.0.1:3000"
    }
}

```

**Important**: The `schema-file` and `schema-content` options are **mutually exclusive**. Use one or the other, not both.

Inline specs are useful for:
- Small APIs that don't warrant a separate file
- Testing and prototyping
- Self-contained configuration that includes all dependencies

For large or shared schemas, prefer `schema-file` to keep configuration maintainable.

##### Inline JSON Schema

Define JSON schemas directly in the configuration using KDL syntax:

```kdl
route "user-registration" {
    matches {
        path "/api/register"
    }
    upstream "api-backend"
    service-type "api"
    api-schema {
        validate-requests #true
        request-schema {
            type "object"
            properties {
                email {
                    type "string"
                    format "email"
                    description "User email address"
                }
                password {
                    type "string"
                    minLength 8
                    maxLength 128
                    description "Password (min 8 characters)"
                }
                username {
                    type "string"
                    minLength 3
                    maxLength 32
                    pattern "^[a-zA-Z0-9_-]+$"
                }
                age {
                    type "integer"
                    minimum 13
                    maximum 120
                }
                terms_accepted {
                    type "boolean"
                }
            }
            required "email" "password" "username" "terms_accepted"
        }
    }
}
```

The inline schema is converted to JSON Schema and compiled at startup. It follows the JSON Schema specification and supports all standard JSON Schema keywords.

##### Request and Response Validation

Configure separate validation for requests and responses:

```kdl
route "user-profile" {
    matches {
        path-prefix "/api/profile"
    }
    upstream "api-backend"
    service-type "api"
    api-schema {
        validate-requests #true
        validate-responses #true  // Enable response validation
        strict-mode #true          // Reject additional properties

        // Schema for profile updates
        request-schema {
            type "object"
            properties {
                display_name {
                    type "string"
                    minLength 1
                    maxLength 100
                }
                bio {
                    type "string"
                    maxLength 500
                }
                avatar_url {
                    type "string"
                    format "uri"
                }
            }
            minProperties 1  // At least one field required
        }

        // Schema for profile responses
        response-schema {
            type "object"
            properties {
                id {
                    type "string"
                    format "uuid"
                }
                email {
                    type "string"
                    format "email"
                }
                username { type "string" }
                display_name { type "string" }
                bio { type "string" }
                avatar_url {
                    type "string"
                    format "uri"
                }
                created_at {
                    type "string"
                    format "date-time"
                }
                updated_at {
                    type "string"
                    format "date-time"
                }
            }
            required "id" "email" "username" "created_at"
        }
    }
}
```

##### Complex Nested Schemas

Support for complex object hierarchies and arrays:

```kdl
route "create-order" {
    matches {
        path "/api/orders"
        method "POST"
    }
    upstream "api-backend"
    service-type "api"
    api-schema {
        validate-requests #true
        strict-mode #true
        request-schema {
            type "object"
            properties {
                customer {
                    type "object"
                    properties {
                        name {
                            type "string"
                            minLength 1
                        }
                        email {
                            type "string"
                            format "email"
                        }
                        phone {
                            type "string"
                            pattern "^\\+?[1-9]\\d{1,14}$"
                        }
                    }
                    required "name" "email"
                }
                items {
                    type "array"
                    minItems 1
                    items {
                        type "object"
                        properties {
                            product_id { type "string" }
                            quantity {
                                type "integer"
                                minimum 1
                            }
                            price {
                                type "number"
                                minimum 0
                            }
                        }
                        required "product_id" "quantity" "price"
                    }
                }
                shipping_address {
                    type "object"
                    properties {
                        street { type "string" }
                        city { type "string" }
                        state {
                            type "string"
                            minLength 2
                            maxLength 2
                        }
                        zip {
                            type "string"
                            pattern "^\\d{5}(-\\d{4})?$"
                        }
                        country {
                            type "string"
                            enum "US" "CA" "MX"
                        }
                    }
                    required "street" "city" "state" "zip" "country"
                }
            }
            required "customer" "items" "shipping_address"
        }
    }
}
```

##### Validation Options

| Option | Default | Description |
|--------|---------|-------------|
| `schema-file` | None | Path to OpenAPI/Swagger spec file (YAML or JSON) |
| `request-schema` | None | Inline JSON Schema for request validation |
| `response-schema` | None | Inline JSON Schema for response validation |
| `validate-requests` | `true` | Enable request body validation |
| `validate-responses` | `false` | Enable response body validation |
| `strict-mode` | `false` | Reject additional properties not in schema |

##### Validation Error Responses

When request validation fails, Zentinel answers `400 Bad Request` with
`Content-Type: application/json; charset=utf-8` and an `x-request-id` header.
This is the body 26.10_3 returns for a POST of `{"x":1}` to a route whose schema
requires `email` and `name`:

```json
{
  "status": 400,
  "title": "Bad Request",
  "message": "Request validation failed",
  "request_id": "VBr4jwTp1GS",
  "timestamp": 1792393653,
  "details": {
    "validation_error": "{\"error\":\"Validation failed\",\"status\":400,\"validation_errors\":[{\"field\":\"$\",\"message\":\"\\\"email\\\" is a required property\",\"value\":{\"x\":1}},{\"field\":\"$\",\"message\":\"\\\"name\\\" is a required property\",\"value\":{\"x\":1}}],\"request_id\":\"VBr4jwTp1GS\"}"
  }
}
```

The list of validation errors is inside `details.validation_error` as a JSON
**string**, not as an object: parse it a second time to read the individual
errors. Only `POST`, `PUT` and `PATCH` bodies are validated.

> **A schema that does not compile disables validation for the route.** The
> proxy logs `Failed to initialize schema validator for route <id>` at startup
> and forwards every request unchecked. One known cause: `required` with a
> single name (`required "email"`) is converted to a string instead of a list,
> and the schema is rejected with `"email" is not of type "array"`. Check the
> startup log for that line after changing a schema.

##### JSON Schema Support

Zentinel supports JSON Schema Draft 7 with the following features:

- **Types**: `string`, `number`, `integer`, `boolean`, `array`, `object`, `null`
- **String validation**: `minLength`, `maxLength`, `pattern`, `format` (email, uri, uuid, date-time, etc.)
- **Numeric validation**: `minimum`, `maximum`, `multipleOf`
- **Array validation**: `minItems`, `maxItems`, `uniqueItems`, `items`
- **Object validation**: `properties`, `required`, `minProperties`, `maxProperties`, `additionalProperties`
- **Logical operators**: `allOf`, `anyOf`, `oneOf`, `not`
- **References**: `$ref` (for OpenAPI specs)

##### OpenAPI Integration

When using `schema-file`, Zentinel:

1. Loads the OpenAPI/Swagger specification at startup
2. Extracts schemas for each path and HTTP method
3. Validates incoming requests against the operation's `requestBody` schema
4. Validates responses against the operation's `responses` schema (if enabled)
5. Matches requests to operations by path and method

The schema file is monitored for changes and automatically reloaded (if hot-reload is enabled).

##### Performance Considerations

- Schemas are compiled once at startup for maximum performance
- Request validation adds minimal latency (typically <1ms)
- Request validation reads the whole request body before forwarding it; bodies
  up to the route's effective `max-body-size` are validated and then forwarded,
  and larger ones get `413`. Before 26.10_5 a body over 64 KiB could not be
  forwarded after validation: 26.10_4 answered `413`, earlier releases let the
  upstream time out
- Response validation requires buffering the full response body
- Use `validate-responses` only in development/testing environments
- For high-throughput APIs, consider validating only critical endpoints

##### Best Practices

1. **Use OpenAPI specs** for complex APIs with multiple endpoints
2. **Enable strict-mode** to catch unexpected fields early
3. **Validate requests in production**, responses in development
4. **Keep schemas focused** - validate only what's necessary
5. **Use meaningful descriptions** for better error messages
6. **Test validation** with invalid payloads before deploying
7. **Version your schemas** alongside your API versions

##### Example: Complete API Route

```kdl
route "user-api" {
    priority 200
    matches {
        path-prefix "/api/v2/users"
    }
    upstream "user-service"
    service-type "api"

    // Schema validation
    api-schema {
        schema-file "/etc/zentinel/schemas/user-api-v2.yaml"
        validate-requests #true
        validate-responses #false
        strict-mode #true
    }

    // Authentication and rate limiting
    filters "jwt-auth" "rate-limit"

    // Custom error pages (see Error Pages below)
    error-pages {
        pages {
            "503" {
                format "json"
                message "The user service is unavailable, retry shortly"
                headers {
                    Retry-After "30"
                }
            }
        }
    }

    // Performance tuning
    policies {
        timeout-secs 30
        max-body-size "10MB"
    }

    // Resilience
    retry-policy {
        max-attempts 3
    }
}
```

### Upstream Reference

```kdl
route "api" {
    matches { path-prefix "/api/" }
    upstream "backend"
}
```

Reference an upstream defined in the `upstreams` block. Required for `web` and `api` service types.

> **Note:** If the referenced upstream connects to an HTTPS backend, make sure it has a `tls` block configured. See [Upstream TLS](/configuration/upstreams/#upstream-tls).

### Filters and Agents

```kdl
route "api" {
    matches {
        path-prefix "/api/"
    }
    upstream "backend"
    filters "auth" "rate-limit" "cors"
}
```

Apply filters in order. Filters are defined in the top-level `filters` block.

Enable WAF shorthand:

```kdl
route "api" {
    matches { path-prefix "/api/" }
    upstream "backend"
    waf-enabled #true
}
```

## Route Policies

### Header Modifications

```kdl
route "api" {
    matches { path-prefix "/api/" }
    upstream "backend"
    policies {
        request-headers {
            // Set or replace header
            set {
                "X-Forwarded-Proto" "https"
            }
            // Add header (preserves existing)
            add {
                "X-Custom-Header" "value"
            }
            // Remove headers
            remove "X-Internal-Header" "X-Debug"
        }
        response-headers {
            set {
                "X-Content-Type-Options" "nosniff"
                "X-Frame-Options" "DENY"
            }
            remove "Server" "X-Powered-By"
        }
    }
}
```

### Timeout Override

```kdl
route "upload" {
    matches {
        path-prefix "/upload/"
    }
    upstream "backend"
    policies {
        timeout-secs 300  // 5 minutes for uploads
    }
}
```

### Body Size Limit

```kdl
route "upload" {
    matches { path-prefix "/upload/" }
    upstream "backend"
    policies {
        max-body-size "100MB"
    }
}
```

Supports units: `B`, `KB`, `MB`, `GB`

### Failure Mode

```kdl
route "api" {
    matches { path-prefix "/api/" }
    upstream "backend"
    policies {
        failure-mode "closed"  // Block on failure (default)
    }
}

route "metrics" {
    matches { path-prefix "/telemetry/" }
    upstream "backend"
    policies {
        failure-mode "open"    // Allow through on failure
    }
}
```

| Mode | Behavior | Use Case |
|------|----------|----------|
| `closed` | Block traffic on agent/upstream failure | Security-sensitive routes |
| `open` | Allow traffic through on failure | Non-critical observability |

### Request/Response Buffering


> **`buffer-requests` and `buffer-responses` were removed in 26.08_5**
> ([zentinelproxy/zentinel#366](https://github.com/zentinelproxy/zentinel/issues/366)).
> They never had a KDL parser and were read by nothing in the proxy; writing
> them in `policies` has no effect and `zentinel lint` reports them as ignored
> keys. Delete them from existing configurations.
>
> Body inspection by agents does not depend on these settings and works without
> them.

## MCP and A2A

Routes carrying Model Context Protocol or Agent2Agent traffic can declare which
methods and tools are permitted, enforced by reading the JSON-RPC envelope. See
[Agentic Protocols](../agentic/).

## Retry Policy

Re-sends a request when the upstream fails to answer usefully.

```kdl
route "api" {
    matches { path-prefix "/api/" }
    upstream "backend"
    retry-policy {
        max-attempts 3
        retryable-status-codes 502 503 504
        backoff "100ms"
        max-backoff "2s"
        per-attempt-timeout "1s"
    }
}
```

| Option | Default | Description |
|--------|---------|-------------|
| `max-attempts` | `3` | Total attempts including the first, so `3` means one try and two retries |
| `retryable-status-codes` | *(none)* | Upstream statuses that discard the response and retry |
| `backoff` | `100ms` | Delay before the first retry; doubles each attempt |
| `max-backoff` | `2s` | Ceiling for the doubling backoff |
| `per-attempt-timeout` | *(inherits)* | Connection timeout applied to each attempt |
| `retry-non-idempotent` | `false` | Allow replaying `POST` and other non-idempotent methods |

### Nothing is retried unless you ask

`retryable-status-codes` is empty by default, so a bare `retry-policy` block retries only connection failures. Retrying a status code replays the request, and which codes are safe to replay depends on the application: a `503` from a load shedder is worth another try; a `500` from a handler that already charged a card is not.

### `POST` is not replayed by default

Idempotent methods — `GET`, `HEAD`, `PUT`, `DELETE`, `OPTIONS`, `TRACE` — are safe to replay by definition. Anything else is not retried unless you set `retry-non-idempotent`, because replaying it can duplicate a side effect the origin already performed and the proxy cannot tell whether it did.

```fragment,kdl
retry-policy {
    max-attempts 3
    retryable-status-codes 503
    retry-non-idempotent #true   // only if your endpoints are safe to replay
}
```

### The last response is the one your client sees

When the retry budget runs out, the client receives the upstream's own response — three failed tries against a struggling backend end with its `503`, not a generic gateway error. Retries are only visible in the logs and in the extra latency.

### Set `per-attempt-timeout` if you set `max-attempts`

Without it, each attempt waits the full connection timeout. Three attempts against a black-holed upstream take three times as long as one, so a policy meant to improve availability makes the worst case worse. `per-attempt-timeout` bounds each try.

### Large request bodies are not retried

Retrying a request means re-sending its body, which requires having buffered it. A body too large to buffer cannot be replayed, so the response is forwarded as-is and Zentinel logs:

```
WARN Not retrying: request body exceeded the retry buffer and cannot be replayed
```

If retries matter for an endpoint that takes large uploads, that is the message to look for.

### Backoff must fit under its ceiling

A `backoff` larger than `max-backoff` is rejected at load, because the delay would never grow and the ceiling would silently become the only value:

```
retry-policy backoff (10s) is greater than max-backoff (1s); the backoff would never grow
```

### What `max-attempts` used to mean

Before this was implemented, `max-attempts` bounded upstream *peer-selection* attempts — retrying the choice of backend from the pool, not the request. Peer selection only fails when no member of the pool is healthy, so the setting rarely did anything, and never what its name suggested. It now governs request retries. Peer selection has its own small fixed retry count and is not configurable.

## Circuit Breaker

> **Not supported at route scope.** The route-level `circuit-breaker` block is dropped by the KDL parser (the proxy logs `Unrecognized directive in route block (will be ignored)` for it). Configure circuit breaking at the **upstream** level instead — the `circuit-breaker` block inside `upstream { ... }` is parsed and configurable as of [zentinelproxy/zentinel#267](https://github.com/zentinelproxy/zentinel/pull/267). The block below shows the parsed keys inside an upstream. (Note: recovery from the open state has a known bug — see [zentinelproxy/zentinel#261](https://github.com/zentinelproxy/zentinel/issues/261).)

```kdl
upstream "backend" {
    target "10.0.1.1:8080"
    circuit-breaker {
        failure-threshold 5
        success-threshold 2
        timeout-seconds 30
        half-open-max-requests 1
    }
}
```

| Option | Default | Description |
|--------|---------|-------------|
| `failure-threshold` | `5` | Failures before opening circuit |
| `success-threshold` | `2` | Successes to close circuit |
| `timeout-seconds` | `30` | Time before trying half-open |
| `half-open-max-requests` | `1` | Requests allowed in half-open |

Circuit breaker states:
- **Closed**: Normal operation, requests flow through
- **Open**: Requests fail immediately (circuit tripped)
- **Half-Open**: Limited requests to test recovery

## Traffic Mirroring / Shadow Traffic

Traffic mirroring (also called shadow traffic or dark traffic) duplicates live requests to a secondary upstream for testing purposes, while the client receives the response from the primary upstream. This enables safe canary deployments, performance testing, and debug workflows.

```kdl
route "api" {
    matches { path-prefix "/api/" }
    upstream "production"

    shadow {
        upstream "canary"
        percentage 100.0
        timeout-ms 5000
        buffer-body #false
        max-body-bytes 1048576
    }
}
```

### Key Characteristics

- **Fire-and-forget**: Shadow requests are sent asynchronously and non-blocking
- **No client impact**: Shadow failures don't affect the primary response
- **Zero latency**: Shadow execution happens in a separate tokio task
- **Sampling control**: Percentage-based and header-based filtering
- **Independent failure domain**: Separate connection pools for shadow upstreams

### Shadow Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `upstream` | string | *required* | Shadow target upstream ID (must exist in upstreams block) |
| `percentage` | float | `100.0` | Percentage of requests to mirror (0.0-100.0) |
| `sample-header` | tuple | none | Only mirror if request header matches `(name, value)` |
| `timeout-ms` | int | `5000` | Shadow request timeout in milliseconds |
| `buffer-body` | bool | `false` | Whether to buffer request bodies for POST/PUT/PATCH |
| `max-body-bytes` | int | `1048576` | Maximum body size to shadow (1MB default) |

### Example: Full Shadow (100% Mirrored)

Mirror all traffic to a canary deployment for comprehensive testing:

```kdl
route "api-full-shadow" {
    matches {
        path-prefix "/api/v1"
    }
    upstream "production"

    shadow {
        upstream "canary"
        percentage 100.0
        timeout-ms 5000
    }
}
```

**Use case**: Initial canary deployment - validate stability with all traffic.

### Example: Partial Shadow (10% Sampling)

Mirror a percentage of requests to reduce shadow load:

```kdl
route "api-partial-shadow" {
    matches {
        path-prefix "/api/v2"
    }
    upstream "production"

    shadow {
        upstream "canary"
        percentage 10.0  // Mirror 10% of requests
        timeout-ms 5000
    }
}
```

**Use case**: Gradual rollout - representative traffic sampling with lower overhead.

### Example: Header-Based Shadow

Mirror only requests with specific headers for targeted testing:

```kdl
route "api-debug-shadow" {
    matches {
        path-prefix "/api/v3"
    }
    upstream "production"

    shadow {
        upstream "canary"
        percentage 100.0
        sample-header "X-Debug-Shadow" "true"  // Only if header present
        timeout-ms 5000
    }
}
```

**Use case**: Developer testing - mirror only debug-flagged requests.

### Body Buffering

By default, shadow requests **do not** include request bodies to avoid buffering overhead. For POST/PUT/PATCH requests that need body inspection in the shadow:

```fragment,kdl
shadow {
    upstream "canary"
    buffer-body #true        // Enable body buffering
    max-body-bytes 1048576   // Limit to 1MB
}
```

⚠️ **Important**: Buffering request bodies has memory and latency implications. Use `max-body-bytes` to enforce strict limits.

**When to buffer bodies:**
- ✅ Small payloads (<1MB), testing form submissions, API validation
- ❌ Large uploads, streaming data, file uploads, high-throughput APIs

### Metrics

Zentinel exposes Prometheus metrics for shadow traffic monitoring:

```prometheus
# Total shadow requests sent (labels: route, upstream, result)
shadow_requests_total{route="api-full-shadow",upstream="canary",result="success"} 1234

# Shadow request errors (labels: route, upstream, error_type)
shadow_errors_total{route="api-full-shadow",upstream="canary",error_type="timeout"} 5

# Shadow request latency histogram (labels: route, upstream)
shadow_latency_seconds_bucket{route="api-full-shadow",upstream="canary",le="0.1"} 980
```

**Key metrics to monitor:**
- `shadow_requests_total{result="success"}` - Successful shadow requests
- `shadow_requests_total{result="error"}` - Failed shadow requests
- `shadow_errors_total{error_type="timeout"}` - Shadow timeouts
- `shadow_latency_seconds` - Shadow request latency distribution

### Security Considerations

Shadow traffic contains **real user data**. Ensure shadow upstreams:

- Have equivalent security controls (TLS, auth, encryption)
- Comply with data residency and privacy requirements
- Use the same data handling policies as production
- Audit shadow traffic access appropriately

For regulated environments (PCI, HIPAA, GDPR):
- **Do not** mirror sensitive data to less-secure environments
- Use `sample-header` to exclude sensitive requests
- Consider data masking/scrubbing before shadowing
- Document shadow data flows in compliance audits

### Best Practices

1. **Start with low sampling**: Begin with 1-5% and gradually increase
2. **Use timeouts**: Configure shadow timeouts shorter than primary timeouts
3. **Monitor shadow health**: Set up alerts for shadow error rates
4. **Body buffering limits**: Enforce strict size limits when buffering
5. **Header-based targeting**: Use headers for targeted testing without impacting all traffic

### Complete Example

```kdl
routes {
    // Production route with canary shadow
    route "api-v2" {
        priority 200
        matches {
            path-prefix "/api/v2/"
        }
        upstream "production"

        // Mirror 10% of traffic to canary
        shadow {
            upstream "canary"
            percentage 10.0
            timeout-ms 3000
            buffer-body #false
        }

        // Additional configuration
        filters "auth" "rate-limit"
        retry-policy {
            max-attempts 3
        }
    }

    // Debug route with 100% shadow for beta users
    route "api-beta" {
        priority 250
        matches {
            path-prefix "/api/v2/"
            header "X-User-Tier" "beta"
        }
        upstream "production"

        shadow {
            upstream "canary"
            percentage 100.0
            sample-header "X-Enable-Shadow" "true"
            timeout-ms 5000
        }
    }
}
```

For a complete traffic mirroring example with Docker Compose and test scripts, see the [Traffic Mirroring Example](../../examples/traffic-mirroring/).

## Error Pages

From 26.10_6 a route can replace the response for chosen error statuses with
its own page, in an `error-pages` block:

```fragment,kdl
routes {
    route "shop" {
        matches {
            path-prefix "/"
        }
        upstream "web"
        service-type "web"

        error-pages {
            default-format "html"                // html, json, text or xml
            template-dir "/etc/zentinel/errors"  // base for relative templates
            pages {
                "404" {
                    message "We could not find that page."
                }
                "503" {
                    template "503.html"
                    message "We are back in a minute."
                    headers {
                        Retry-After "30"
                    }
                }
            }
        }
    }
}
```

| Key | Where | Meaning |
|-----|-------|---------|
| `default-format` | `error-pages` | Format of pages that set no `format`, and of the errors the proxy generates on this route. Default: `json` on `api`, `builtin` and `inference` routes, `html` on `web` and `static` routes |
| `template-dir` | `error-pages` | Directory a relative `template` is resolved against. Without it, a relative path is relative to the proxy's working directory |
| `pages` | `error-pages` | One child per status, named by the status code in quotes (`"503" { }`), `400` to `599` |
| `format` | page | `html`, `json`, `text` (or `plain`) or `xml` |
| `message` | page | Text shown on the page, in place of the proxy's generic message |
| `template` | page | File used as the page body, in the page's format |
| `headers` | page | Extra response headers, one `Name "value"` per line |

Without a `template`, the page is generated in its format and carries the
status, the status's reason phrase, the `message` and the request ID. A
template is read when the configuration is loaded (and on reload), and these
placeholders are filled in:

| Placeholder | Value |
|-------------|-------|
| `{{status}}` | Status code, for example `503` |
| `{{title}}` | Reason phrase, for example `Service Unavailable` |
| `{{message}}` | The page's `message`, or the proxy's message for the error |
| `{{request_id}}` | The request's trace ID |
| `{{timestamp}}` | Unix time in seconds |

In `html` and `xml` pages the values are HTML-escaped, and in `json` pages
they are escaped as JSON string content, so a message that contains request
data (a static route's error names the requested path) cannot inject markup.
Every page response also has `Content-Type` for its format and `X-Request-Id`.

### Which errors a page replaces

A page for a status replaces, on its route:

- an **upstream** response with that status: status, headers and body are
  replaced by the page (the upstream's `Content-Type`, `Content-Length` and
  encoding headers go with them);
- an error the **proxy** raises itself with that status: upstream unreachable
  or timed out (`502`/`503`/`504`), every target failing its health check
  (`503`), a body over the limit (`413`), a header over the limit (`500`);
- from 26.10_7, a request the **proxy refuses** on the route: a rate limit
  (`429`, including the inference token limit and token budget), a request over
  `max-in-flight-requests` (`503`), a geo block, a prompt-injection block, a
  WebSocket upgrade on a route without `websocket #true` (`403`), a route
  without a usable upstream (`500`), and an agent block that carries no body of
  its own.

The refusal's own headers are kept with the page: `Retry-After` and the
`X-RateLimit-*` headers are always sent, and they override a page header of the
same name. A page without a `message` shows the refusal's message (for example
`Rate limit exceeded` or `WebSocket not enabled for this route`).

An agent block that carries its own body is not replaced: the agent's body is
sent as `text/plain`, with the agent's status. This holds in the request-body
phase too; before 26.10_7 a body-phase block was answered with the proxy's
generic JSON body instead of the agent's.

Statuses without a page behave as described in the next section: upstream
errors pass through unchanged, and the proxy's own errors and refusals get
their default body. A request that matches no route has no route pages, so its
`404` is always the JSON body.

**Before 26.10_7** rate-limit, in-flight, geo, prompt-injection, WebSocket,
no-upstream and header-phase agent refusals were written directly and never
replaced by a page.

Invalid values do not stop the configuration from loading. A missing or
unreadable template, an unknown format, a page name that is not a status from
400 to 599, or a header with an invalid name or value is reported by
`zentinel test` and `zentinel lint` as "is being ignored" (and fails
`test --strict`); the page is then generated in its format, or the header is
left out. `include-stack-trace` is reported as ignored: the proxy produces no
stack traces.

**Before 26.10_6** no parser read `error-pages`: the whole block was reported
as ignored and every error used the default responses below. Generated HTML
error pages also inserted the message unescaped.

### Default error responses

What a client receives on an error when the route has no page for its status.
From 26.10_5:

| Situation | Status | Body | `Content-Type` |
|-----------|--------|------|----------------|
| Upstream unreachable (`503` for a refused connection) or timed out (`504`) | `502`/`503`/`504` | `{"error":"502 Bad Gateway","trace_id":"V9ZSZT2h6Ug"}` | `application/json` |
| Request over a header limit | `500` | `{"error":"500 Internal Server Error","trace_id":"..."}` | `application/json` |
| Every target failing its health check | `503` | `{"error":"503 Service Unavailable","trace_id":"..."}` | `application/json` |
| Request body over the effective `max-body-size` | `413` | `{"error":"413 Payload Too Large","trace_id":"..."}` | `application/json` |
| No route matches | `404` | `{"error":"404 Not Found","trace_id":"..."}` | `application/json` |
| Upstream answers with `4xx`/`5xx` | upstream's | upstream's, unchanged | upstream's, unchanged |
| Static file not found | `404` | `404 Not Found` | `text/plain` |
| Request over `max-in-flight-requests` | `503` | `{"error":"503 Service Unavailable","trace_id":"..."}`, with `Retry-After: 1` | `application/json` |
| Rate-limit filter | `429` | `Rate limit exceeded`, with `X-RateLimit-*` and `Retry-After` | `text/plain; charset=utf-8` |
| Inference token limit or token budget | `429` | `Token rate limit exceeded` or `Token budget exhausted` | `text/plain; charset=utf-8` |
| Geo block | the filter's status | the filter's block message, or `Access denied` | `text/plain` |
| Prompt-injection block | the guardrail's status | `{"error":"prompt_injection_blocked","message":"..."}` | `application/json` |
| WebSocket upgrade on a route without `websocket #true` | `403` | `WebSocket not enabled for this route` | `text/plain` |
| Route without a usable upstream | `500` | `Internal Server Error` | `text/plain` |
| Agent block with its own body (never replaced by a page) | agent's | agent's | `text/plain` |
| Agent block without a body, on request headers | agent's | `Blocked by agent` | `text/plain` |
| Agent block without a body, on the request body | agent's | `{"error":"403 Forbidden","trace_id":"..."}` (the agent's status) | `application/json` |
| Request schema validation | `400` | see [Validation Error Responses](#validation-error-responses) | `application/json; charset=utf-8` |

Errors the proxy generates itself have the same JSON shape on every route type:
`error` (status code and the status's standard reason phrase) and `trace_id`,
which is also sent as the `X-Correlation-Id` response header. There is no
`status` or `request_id` field. From 26.10_7 the refusals in the table carry
`X-Correlation-Id` too (all but an agent's own body sent on request headers),
and the proxy closes the connection after each of them.

When the **upstream** returns `4xx`/`5xx`, the response is passed through as
the upstream sent it: status, headers (including `Content-Type`) and body.

**Before 26.10_5:** an upstream error kept its body but had `Content-Type`
replaced (`text/html; charset=utf-8` on `web` and `static` routes,
`application/json` on `api`, `builtin` and `inference` routes); proxy errors
other than 400, 500, 502, 503 and 504 were labelled "Internal Server Error"
(for example `"404 Internal Server Error"`); the no-route 404 had an empty
`trace_id` and `X-Correlation-Id`; a body over the global limit got `500`; and
failing health checks did not take targets out of rotation, so requests still
went to them.

## Complete Examples

### API Gateway

```kdl
routes {
    // Health check (highest priority)
    route "health" {
        priority 1000
        matches {
            path "/health"
        }
        service-type "builtin"
        builtin-handler "health"
    }

    // Metrics endpoint (admin only)
    route "metrics" {
        priority 999
        matches {
            path "/metrics"
            header "X-Admin-Token"
        }
        service-type "builtin"
        builtin-handler "metrics"
    }

    // API v2 (current)
    route "api-v2" {
        priority 200
        matches {
            path-prefix "/api/v2/"
        }
        upstream "api-v2"
        filters "auth" "rate-limit"
        retry-policy {
            max-attempts 3
        }
        policies {
            timeout-secs 30
            failure-mode "closed"
            request-headers {
                set {
                    "X-Api-Version" "2"
                }
            }
        }
    }

    // API v1 (legacy)
    route "api-v1" {
        priority 100
        matches {
            path-prefix "/api/v1/"
        }
        upstream "api-v1"
        filters "auth"
        policies {
            timeout-secs 60
            response-headers {
                set {
                    "X-Deprecation-Notice" "API v1 is deprecated. Please migrate to v2."
                }
            }
        }
    }

    // Static assets
    route "static" {
        priority 50
        matches {
            path-prefix "/static/"
        }
        service-type "static"
        static-files {
            root "/var/www/static"
            cache-control "public, max-age=31536000, immutable"
            compress #true
        }
    }

    // SPA fallback
    route "spa" {
        priority 1
        matches {
            path-prefix "/"
            method "GET"
        }
        service-type "static"
        static-files {
            root "/var/www/app"
            fallback "index.html"
        }
    }
}
```

### Multi-tenant Routing

```kdl
routes {
    route "tenant-a" {
        priority 100
        matches {
            host "tenant-a.example.com"
            path-prefix "/api/"
        }
        upstream "tenant-a-backend"
        policies {
            request-headers {
                set {
                    "X-Tenant-Id" "tenant-a"
                }
            }
        }
    }

    route "tenant-b" {
        priority 100
        matches {
            host "tenant-b.example.com"
            path-prefix "/api/"
        }
        upstream "tenant-b-backend"
        policies {
            request-headers {
                set {
                    "X-Tenant-Id" "tenant-b"
                }
            }
        }
    }
}
```

## Default Values

| Setting | Default |
|---------|---------|
| `priority` | `0` |
| `service-type` | `web` |
| `policies.failure-mode` | `closed` |
| `policies.buffer-requests` | `false` |
| `policies.buffer-responses` | `false` |
| `static-files.index` | `index.html` |
| `static-files.directory-listing` | `false` |
| `static-files.compress` | `true` |
| `retry-policy.max-attempts` | `3` |
| `retry-policy.backoff` | `100ms` |
| `retry-policy.max-backoff` | `2s` |
| `retry-policy.retry-non-idempotent` | `false` |
| `circuit-breaker.failure-threshold` | `5` |

## Route Evaluation Order

1. Routes sorted by priority (descending)
2. First matching route wins
3. If no route matches and listener has `default-route`, use that
4. Otherwise, return 404

## Next Steps

- [Upstreams](../upstreams/) - Backend server configuration
- [Limits](../limits/) - Request limits and performance
