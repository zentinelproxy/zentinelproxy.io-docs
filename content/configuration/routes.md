+++
title = "Routes"
weight = 4
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

#### Path Matching

```kdl
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

```kdl
matches {
    host "api.example.com"
}
```

Match by the `Host` header. Useful for virtual hosting.

#### Method Matching

```kdl
matches {
    method "GET" "POST" "PUT" "DELETE"
}
```

Match specific HTTP methods. Multiple methods are OR'd together.

#### Header Matching

```kdl
matches {
    // Match if header exists
    header name="X-Api-Key"

    // Match header with specific value
    header name="X-Api-Version" value="2"
}
```

#### Query Parameter Matching

```kdl
matches {
    // Match if parameter exists
    query-param name="debug"

    // Match parameter with value
    query-param name="format" value="json"
}
```

### Service Types

```kdl
route "api" {
    service-type "web"  // Default
}
```

| Type | Description |
|------|-------------|
| `web` | Standard HTTP proxy (default) |
| `api` | API service with JSON error responses |
| `static` | Static file serving |
| `builtin` | Built-in handlers |

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
        directory-listing false
        cache-control "public, max-age=86400"
        compress true
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
        schema-file "/etc/sentinel/schemas/api-v1-openapi.yaml"
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
route "api-v1" {
    matches {
        path-prefix "/api/v1"
    }
    upstream "api-backend"
    service-type "api"
    api-schema {
        validate-requests #true
        schema-content r#"
openapi: 3.0.0
info:
  title: User API
  version: 1.0.0
paths:
  /api/v1/users:
    post:
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [email, password]
              properties:
                email:
                  type: string
                  format: email
                password:
                  type: string
                  minLength: 8
    get:
      responses:
        '200':
          description: List of users
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
                  properties:
                    id: { type: string, format: uuid }
                    email: { type: string, format: email }
                    username: { type: string }
        "#
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

When validation fails, Sentinel returns a structured JSON error response:

```json
{
  "error": "Validation failed",
  "status": 400,
  "request_id": "req-123",
  "validation_errors": [
    {
      "field": "$.email",
      "message": "'not-an-email' is not a valid email",
      "value": "not-an-email"
    },
    {
      "field": "$.password",
      "message": "String is too short (expected minimum 8 characters)",
      "value": "short"
    }
  ]
}
```

##### JSON Schema Support

Sentinel supports JSON Schema Draft 7 with the following features:

- **Types**: `string`, `number`, `integer`, `boolean`, `array`, `object`, `null`
- **String validation**: `minLength`, `maxLength`, `pattern`, `format` (email, uri, uuid, date-time, etc.)
- **Numeric validation**: `minimum`, `maximum`, `multipleOf`
- **Array validation**: `minItems`, `maxItems`, `uniqueItems`, `items`
- **Object validation**: `properties`, `required`, `minProperties`, `maxProperties`, `additionalProperties`
- **Logical operators**: `allOf`, `anyOf`, `oneOf`, `not`
- **References**: `$ref` (for OpenAPI specs)

##### OpenAPI Integration

When using `schema-file`, Sentinel:

1. Loads the OpenAPI/Swagger specification at startup
2. Extracts schemas for each path and HTTP method
3. Validates incoming requests against the operation's `requestBody` schema
4. Validates responses against the operation's `responses` schema (if enabled)
5. Matches requests to operations by path and method

The schema file is monitored for changes and automatically reloaded (if hot-reload is enabled).

##### Performance Considerations

- Schemas are compiled once at startup for maximum performance
- Request validation adds minimal latency (typically <1ms)
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
        method "GET" "POST" "PUT" "DELETE"
    }
    upstream "user-service"
    service-type "api"

    // Schema validation
    api-schema {
        schema-file "/etc/sentinel/schemas/user-api-v2.yaml"
        validate-requests #true
        validate-responses #false
        strict-mode #true
    }

    // Authentication and rate limiting
    filters "jwt-auth" "rate-limit"

    // Error handling
    error-pages {
        default-format "json"
        pages {
            "400" {
                format "json"
                message "Invalid request"
            }
            "401" {
                format "json"
                message "Authentication required"
            }
        }
    }

    // Performance tuning
    policies {
        timeout-secs 30
        max-body-size "10MB"
        buffer-requests #true  // Required for validation
    }

    // Resilience
    retry-policy {
        max-attempts 3
        retryable-status-codes 502 503 504
    }
}
```

### Upstream Reference

```kdl
route "api" {
    upstream "backend"
}
```

Reference an upstream defined in the `upstreams` block. Required for `web` and `api` service types.

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
    waf-enabled true
}
```

## Route Policies

### Header Modifications

```kdl
route "api" {
    upstream "backend"
    policies {
        request-headers {
            // Set or replace header
            set {
                "X-Forwarded-Proto" "https"
                "X-Request-Start" "${request_time}"
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
    policies {
        max-body-size "100MB"
    }
}
```

Supports units: `B`, `KB`, `MB`, `GB`

### Failure Mode

```kdl
route "api" {
    policies {
        failure-mode "closed"  // Block on failure (default)
    }
}

route "metrics" {
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

```kdl
route "api" {
    policies {
        buffer-requests true   // Buffer full request before forwarding
        buffer-responses true  // Buffer full response before sending
    }
}
```

Buffering is required for body inspection by agents. Be mindful of memory usage with large bodies.

## Retry Policy

```kdl
route "api" {
    upstream "backend"
    retry-policy {
        max-attempts 3
        timeout-ms 30000
        backoff-base-ms 100
        backoff-max-ms 10000
        retryable-status-codes 502 503 504
    }
}
```

| Option | Default | Description |
|--------|---------|-------------|
| `max-attempts` | `3` | Maximum retry attempts |
| `timeout-ms` | `30000` | Total timeout for all attempts |
| `backoff-base-ms` | `100` | Initial backoff delay |
| `backoff-max-ms` | `10000` | Maximum backoff delay |
| `retryable-status-codes` | `502, 503, 504` | Status codes to retry |

Backoff uses exponential delay: `min(base * 2^attempt, max)`

## Circuit Breaker

```kdl
route "api" {
    upstream "backend"
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

## Error Pages

```kdl
route "api" {
    error-pages {
        default-format "json"
        pages {
            "404" {
                format "json"
                message "Resource not found"
            }
            "500" {
                format "json"
                message "Internal server error"
            }
            "503" {
                format "html"
                template "/etc/sentinel/errors/503.html"
            }
        }
    }
}
```

| Format | Content-Type |
|--------|--------------|
| `json` | `application/json` |
| `html` | `text/html` |
| `text` | `text/plain` |
| `xml` | `application/xml` |

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
            header name="X-Admin-Token"
        }
        service-type "builtin"
        builtin-handler "metrics"
    }

    // API v2 (current)
    route "api-v2" {
        priority 200
        matches {
            path-prefix "/api/v2/"
            method "GET" "POST" "PUT" "DELETE" "PATCH"
        }
        upstream "api-v2"
        filters "auth" "rate-limit"
        retry-policy {
            max-attempts 3
            retryable-status-codes 502 503 504
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
            compress true
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
| `circuit-breaker.failure-threshold` | `5` |

## Route Evaluation Order

1. Routes sorted by priority (descending)
2. First matching route wins
3. If no route matches and listener has `default-route`, use that
4. Otherwise, return 404

## Next Steps

- [Upstreams](../upstreams/) - Backend server configuration
- [Limits](../limits/) - Request limits and performance
