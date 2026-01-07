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
| `inference` | LLM/AI inference with token rate limiting ([details](../inference/)) |

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
