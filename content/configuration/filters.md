+++
title = "Filters"
weight = 6
+++

Filters provide a flexible pipeline for request and response processing. They can be built-in (rate-limit, headers, CORS, compression) or external agents. Filters are defined centrally in the `filters` block with unique IDs, then referenced by name in route configurations.

## Basic Configuration

```kdl
filters {
    filter "api-rate-limit" {
        type "rate-limit"
        max-rps 100
        burst 20
        key "client-ip"
    }

    filter "add-security-headers" {
        type "headers"
        phase "response"
        set {
            "X-Content-Type-Options" "nosniff"
            "X-Frame-Options" "DENY"
        }
    }
}

routes {
    route "api" {
        matches {
            path-prefix "/api/"
        }
        upstream "backend"
        filters "api-rate-limit" "add-security-headers"
    }
}
```

## Filter Types

### Rate Limiting

Rate limiting using a token bucket algorithm. Supports local (single-instance) or distributed (Redis) backends.

```kdl
filter "rate-limiter" {
    type "rate-limit"
    max-rps 100              // Maximum requests per second
    burst 20                 // Token bucket size
    key "client-ip"          // Rate limit key
    on-limit "reject"        // Action when exceeded
    status-code 429          // Response status
    limit-message "Too many requests"
}
```

#### Rate Limit Keys

| Key | Description |
|-----|-------------|
| `client-ip` | Rate limit per client IP address (default) |
| `path` | Rate limit per request path |
| `route` | Global rate limit for the route |
| `client-ip-and-path` | Combined client IP and path |
| `header:X-API-Key` | Rate limit by specific header value |

#### Rate Limit Actions

| Action | Description |
|--------|-------------|
| `reject` | Reject with 429 status (default) |
| `delay` | Queue request until tokens available (up to max-delay-ms) |
| `log-only` | Log but allow request through |

#### Distributed Rate Limiting with Redis

```kdl
filter "distributed-limiter" {
    type "rate-limit"
    max-rps 1000
    burst 100
    backend "redis" {
        url "redis://127.0.0.1:6379"
        key-prefix "sentinel:ratelimit:"
        pool-size 10
        timeout-ms 50
        fallback-local #true
    }
}
```

### Global Rate Limits

Apply rate limits at the server level before route-specific limits:

```kdl
rate-limits {
    default-rps 100        // Default for routes without explicit limits
    default-burst 20
    key "client-ip"

    global {
        max-rps 10000      // Server-wide limit
        burst 1000
        key "client-ip"
    }
}
```

### Headers Filter

Manipulate request or response headers:

```kdl
filter "security-headers" {
    type "headers"
    phase "response"       // "request", "response", or "both"

    // Set headers (overwrites existing)
    set {
        "X-Content-Type-Options" "nosniff"
        "X-Frame-Options" "DENY"
        "X-XSS-Protection" "1; mode=block"
        "Strict-Transport-Security" "max-age=31536000; includeSubDomains"
    }

    // Add headers (preserves existing)
    add {
        "X-Request-ID" "${trace_id}"
    }

    // Remove headers
    remove "Server" "X-Powered-By"
}
```

### CORS Filter

Handle Cross-Origin Resource Sharing:

```kdl
filter "cors" {
    type "cors"
    allowed-origins "https://example.com" "https://app.example.com"
    allowed-methods "GET" "POST" "PUT" "DELETE" "OPTIONS"
    allowed-headers "Content-Type" "Authorization" "X-Request-ID"
    exposed-headers "X-Request-ID" "X-RateLimit-Remaining"
    allow-credentials #true
    max-age-secs 86400    // Preflight cache duration
}
```

| Option | Default | Description |
|--------|---------|-------------|
| `allowed-origins` | `*` | Origins allowed to access (use `*` for any) |
| `allowed-methods` | Common methods | HTTP methods allowed |
| `allowed-headers` | None | Request headers client can send |
| `exposed-headers` | None | Response headers client can read |
| `allow-credentials` | `false` | Allow cookies/auth headers |
| `max-age-secs` | `86400` | Preflight cache duration |

### Compression Filter

Compress response bodies:

```kdl
filter "compress" {
    type "compress"
    algorithms "brotli" "gzip" "zstd"
    min-size 1024          // Minimum size to compress (bytes)
    level 6                // Compression level (1-9)
    content-types "text/html" "text/css" "application/json" "application/javascript"
}
```

| Algorithm | Description |
|-----------|-------------|
| `gzip` | Widely supported, good compression |
| `brotli` | Better compression, modern browsers |
| `deflate` | Legacy, wide support |
| `zstd` | Fast compression/decompression |

### GeoIP Filter

Filter requests based on geographic location:

```kdl
// Block mode - block specific countries
filter "block-countries" {
    type "geo"
    database-path "/etc/sentinel/GeoLite2-Country.mmdb"
    action "block"
    countries "RU" "CN" "KP" "IR"
    on-failure "closed"    // Block if lookup fails
    status-code 403
    block-message "Access denied from your region"
}

// Allow mode - allow only specific countries
filter "us-only" {
    type "geo"
    database-path "/etc/sentinel/GeoLite2-Country.mmdb"
    action "allow"
    countries "US" "CA"
    status-code 451        // Unavailable for legal reasons
}

// Log-only mode - tag requests with country
filter "geo-tagging" {
    type "geo"
    database-path "/etc/sentinel/GeoLite2-Country.mmdb"
    action "log-only"
    add-country-header #true
}
```

#### Geo Filter Options

| Option | Default | Description |
|--------|---------|-------------|
| `database-path` | Required | Path to GeoIP database (.mmdb or .bin) |
| `database-type` | Auto-detect | `maxmind` or `ip2location` |
| `action` | `block` | `block`, `allow`, or `log-only` |
| `countries` | Empty | ISO 3166-1 alpha-2 codes (e.g., `US`, `CN`) |
| `on-failure` | `open` | `open` (allow) or `closed` (block) on lookup failure |
| `status-code` | `403` | HTTP status for blocked requests |
| `block-message` | None | Custom message for blocked requests |
| `add-country-header` | `true` | Add `X-Country-Code` header |
| `cache-ttl-secs` | `3600` | Cache TTL for lookups |

### Timeout Filter

Override timeouts for specific routes:

```kdl
filter "long-timeout" {
    type "timeout"
    request-timeout-secs 300       // Total request timeout
    upstream-timeout-secs 120      // Backend timeout
    connect-timeout-secs 30        // Connection timeout
}
```

### Log Filter

Add detailed logging for specific routes:

```kdl
filter "debug-logging" {
    type "log"
    log-request #true
    log-response #true
    log-body #true
    max-body-log-size 4096
    level "debug"
    fields "user-agent" "content-type" "x-request-id"
}
```

### Agent Filter

Delegate processing to an external agent:

```kdl
filter "waf" {
    type "agent"
    agent "waf-agent"      // Reference to agent defined in agents block
    phase "request"        // "request", "response", or "both"
    timeout-ms 200
    failure-mode "open"    // "open" or "closed"
}
```

## Filter Phases

Filters execute at different phases of the request lifecycle:

| Phase | Description |
|-------|-------------|
| `request` | Before forwarding to upstream |
| `response` | After receiving from upstream |
| `both` | Both request and response phases |

Filter phase mapping:

| Filter Type | Default Phase |
|-------------|---------------|
| `rate-limit` | Request |
| `headers` | Configurable |
| `cors` | Both |
| `compress` | Response |
| `geo` | Request |
| `timeout` | Request |
| `log` | Configurable |
| `agent` | Configurable |

## Filter Ordering

Filters execute in the order specified in the route:

```kdl
route "api" {
    filters "rate-limit" "auth" "cors" "logging"
    //       ^^^^^^^^^    ^^^^   ^^^^   ^^^^^^^
    //       1st          2nd    3rd    4th
}
```

For request phase:
1. Rate limit check
2. Auth validation
3. CORS headers (preflight)
4. Logging

For response phase (reverse order of declaration):
1. Logging
2. CORS headers
3. (Auth typically doesn't run on response)
4. (Rate limit doesn't run on response)

## Complete Example

```kdl
filters {
    // Rate limiting with Redis backend
    filter "api-limiter" {
        type "rate-limit"
        max-rps 100
        burst 20
        key "header:X-API-Key"
        on-limit "reject"
        backend "redis" {
            url "redis://redis:6379"
            fallback-local #true
        }
    }

    // Geo-blocking
    filter "geo-block" {
        type "geo"
        database-path "/etc/sentinel/GeoLite2-Country.mmdb"
        action "block"
        countries "RU" "CN"
        on-failure "open"
    }

    // CORS for API
    filter "api-cors" {
        type "cors"
        allowed-origins "https://app.example.com"
        allowed-methods "GET" "POST" "PUT" "DELETE"
        allowed-headers "Content-Type" "Authorization"
        allow-credentials #true
    }

    // Security headers
    filter "security" {
        type "headers"
        phase "response"
        set {
            "X-Content-Type-Options" "nosniff"
            "X-Frame-Options" "DENY"
        }
        remove "Server"
    }

    // Response compression
    filter "compress" {
        type "compress"
        algorithms "brotli" "gzip"
        min-size 1024
    }

    // WAF agent
    filter "waf" {
        type "agent"
        agent "waf-agent"
        timeout-ms 100
        failure-mode "closed"
    }
}

routes {
    route "public-api" {
        matches {
            path-prefix "/api/v1/"
        }
        upstream "api-backend"
        filters "geo-block" "api-limiter" "api-cors" "security" "compress"
    }

    route "secure-api" {
        matches {
            path-prefix "/api/admin/"
        }
        upstream "admin-backend"
        filters "geo-block" "waf" "api-limiter" "security"
    }
}
```

## Default Values

| Filter | Setting | Default |
|--------|---------|---------|
| Rate Limit | `burst` | `10` |
| Rate Limit | `key` | `client-ip` |
| Rate Limit | `on-limit` | `reject` |
| Rate Limit | `status-code` | `429` |
| Rate Limit | `max-delay-ms` | `5000` |
| Headers | `phase` | `request` |
| Compress | `algorithms` | `gzip`, `brotli` |
| Compress | `min-size` | `1024` |
| Compress | `level` | `6` |
| CORS | `allowed-origins` | `*` |
| CORS | `max-age-secs` | `86400` |
| Geo | `action` | `block` |
| Geo | `on-failure` | `open` |
| Geo | `status-code` | `403` |
| Log | `level` | `info` |
| Log | `max-body-log-size` | `4096` |

## Next Steps

- [Agents](../../agents/) - External processing agents
- [Routes](../routes/) - Applying filters to routes
- [Observability](../observability/) - Logging and metrics
