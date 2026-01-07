+++
title = "First Route"
weight = 3
+++

Routes are the core of Sentinel's traffic management. They match incoming requests and direct them to the appropriate backend.

## Anatomy of a Route

A route consists of three main parts:

1. **Matches** - Conditions that determine when the route applies
2. **Upstream** - Where to send matching requests
3. **Policies** - How to handle the request (timeouts, headers, etc.)

```kdl
route "my-route" {
    priority "normal"           // Route priority

    matches {                   // When to match
        path-prefix "/api/"
    }

    upstream "backend"          // Where to send

    policies {                  // How to handle
        timeout-secs 30
    }
}
```

## Creating Your First Route

Let's create a simple API route that:
- Matches requests to `/api/v1/*`
- Forwards to a backend server
- Sets appropriate timeouts

```kdl
routes {
    route "api-v1" {
        matches {
            path-prefix "/api/v1/"
            method "GET" "POST" "PUT" "DELETE"
        }
        upstream "api-backend"
        service-type "api"
        policies {
            timeout-secs 30
        }
    }
}

upstreams {
    upstream "api-backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
}
```

## Match Conditions

Routes support multiple match conditions. All conditions must match for the route to apply.

### Path Matching

```kdl
matches {
    // Prefix match - matches /api/, /api/users, /api/v1/items
    path-prefix "/api/"

    // Exact match - only matches /health exactly
    path "/health"

    // Regex match - matches /v1/, /v2/, /v99/
    path-regex "^/v[0-9]+/"
}
```

### Host Matching

Route based on the `Host` header:

```kdl
matches {
    host "api.example.com"
    path-prefix "/"
}
```

### Method Matching

Restrict to specific HTTP methods:

```kdl
matches {
    path-prefix "/api/"
    method "GET" "POST"     // Only GET and POST requests
}
```

### Header Matching

Match on request headers:

```kdl
matches {
    path-prefix "/api/"
    header "Authorization"              // Header must exist
    header "Content-Type" "application/json"  // Header with value
}
```

### Query Parameter Matching

Match on query parameters:

```kdl
matches {
    path-prefix "/search"
    query-param "q"                     // Parameter must exist
    query-param "format" "json"         // Parameter with value
}
```

## Route Priority

When multiple routes could match, priority determines which one wins:

```kdl
routes {
    // High priority - checked first
    route "api-health" {
        priority "high"
        matches {
            path "/api/health"
        }
        service-type "builtin"
    }

    // Normal priority (default)
    route "api" {
        priority "normal"
        matches {
            path-prefix "/api/"
        }
        upstream "api-backend"
    }

    // Low priority - catch-all
    route "default" {
        priority "low"
        matches {
            path-prefix "/"
        }
        upstream "web-backend"
    }
}
```

Priority levels: `high` > `normal` > `low`

## Service Types

Different service types optimize behavior for specific use cases:

### API Service

For REST APIs - returns JSON errors:

```kdl
route "api" {
    matches { path-prefix "/api/" }
    upstream "api-backend"
    service-type "api"
}
```

Error responses are JSON:
```json
{"error": "Not Found", "status": 404, "request_id": "abc123"}
```

### Web Service

For traditional web applications - returns HTML errors:

```kdl
route "web" {
    matches { path-prefix "/" }
    upstream "web-backend"
    service-type "web"
}
```

### Static Files

Serve files directly without a backend:

```kdl
route "static" {
    matches { path-prefix "/static/" }
    service-type "static"
    static-files {
        root "/var/www/static"
        index "index.html"
        compress #true
    }
}
```

### Built-in Handlers

For health checks and metrics:

```kdl
route "health" {
    matches { path "/health" }
    service-type "builtin"
}

route "metrics" {
    matches { path "/metrics" }
    service-type "builtin"
}
```

## Route Policies

Policies control request handling behavior:

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
    route "api" {
        matches { path-prefix "/api/" }
        upstream "api-backend"

        policies {
            timeout-secs 30
            max-body-size "10MB"
            failure-mode "closed"

            request-headers {
                set {
                    "X-Forwarded-Proto" "https"
                }
                remove "X-Internal-Header"
            }

            response-headers {
                set {
                    "X-Content-Type-Options" "nosniff"
                    "X-Frame-Options" "DENY"
                }
            }
        }
    }

    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
    }
}
```

## Complete Example

Here's a full example with multiple routes:

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
    // Health check endpoint
    route "health" {
        priority "high"
        matches { path "/health" }
        service-type "builtin"
    }

    // API routes
    route "api-v1" {
        priority "normal"
        matches {
            path-prefix "/api/v1/"
            method "GET" "POST" "PUT" "DELETE"
        }
        upstream "api-backend"
        service-type "api"
        policies {
            timeout-secs 30
            max-body-size "5MB"
        }
    }

    // Static assets
    route "assets" {
        priority "normal"
        matches {
            path-prefix "/assets/"
        }
        service-type "static"
        static-files {
            root "/var/www/assets"
            compress #true
        }
    }

    // Catch-all for web app
    route "web" {
        priority "low"
        matches {
            path-prefix "/"
        }
        upstream "web-backend"
        service-type "web"
    }
}

upstreams {
    upstream "api-backend" {
        targets {
            target { address "127.0.0.1:3000" }
        }
        health-check {
            type "http" { path "/health" }
            interval-secs 10
        }
    }

    upstream "web-backend" {
        targets {
            target { address "127.0.0.1:3001" }
        }
    }
}
```

## Testing Routes

Validate your configuration before deploying:

```bash
sentinel -c sentinel.kdl --test
```

Test specific routes with curl:

```bash
# Test API route
curl -v http://localhost:8080/api/v1/users

# Test with specific headers
curl -H "Authorization: Bearer token" http://localhost:8080/api/v1/protected

# Test POST request
curl -X POST -d '{"name":"test"}' -H "Content-Type: application/json" \
  http://localhost:8080/api/v1/users
```

## Next Steps

- [Basic Configuration](../basic-configuration/) - Full configuration reference
- [Route Matching](/concepts/route-matching/) - Advanced matching patterns
- [Load Balancing](/concepts/routing/) - Multiple upstream targets
- [Filters](/features/filters/) - Request/response processing
