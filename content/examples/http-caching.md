+++
title = "HTTP Caching"
weight = 16
+++

Configure HTTP response caching with different storage backends and per-route cache policies. This example demonstrates memory caching, stale-while-revalidate, and cache control handling.

## Use Case

- Cache API responses to reduce backend load
- Long-lived caching for static assets
- Short-lived caching for dynamic content
- Stale-while-revalidate for improved availability
- Per-route cache configuration
- Cache bypass for authenticated requests

## Architecture

```
                    ┌─────────────────┐
                    │    Clients      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    Sentinel     │
                    │   ┌─────────┐   │
                    │   │  Cache  │   │
                    │   │ (memory)│   │
                    │   └─────────┘   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
         ┌─────────┐   ┌─────────┐   ┌─────────┐
         │   API   │   │ Static  │   │  Slow   │
         │ Backend │   │ Backend │   │ Backend │
         └─────────┘   └─────────┘   └─────────┘
```

## Configuration

Create `sentinel.kdl`:

```kdl
// HTTP Caching Configuration
// Response caching with memory backend

system {
    worker-threads 4
    max-connections 10000
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
        request-timeout-secs 60
    }
}

upstreams {
    upstream "api-backend" {
        target "10.0.1.10:8080" weight=1
        target "10.0.1.11:8080" weight=1

        load-balancing "round-robin"

        health-check {
            type "http" {
                path "/health"
                expected-status 200
            }
            interval-secs 10
        }
    }

    upstream "static-backend" {
        target "10.0.2.10:8080" weight=1

        load-balancing "round-robin"
    }

    upstream "slow-backend" {
        target "10.0.3.10:8080" weight=1

        load-balancing "round-robin"

        timeouts {
            request-secs 120
        }
    }
}

// =============================================================================
// Global cache storage configuration
// =============================================================================
cache {
    enabled #true

    // Storage backend: "memory", "disk", or "hybrid"
    backend "memory" {
        max-size-mb 512
    }

    // Lock timeout to prevent thundering herd
    lock-timeout 10
}

routes {
    // API with caching enabled
    route "api-cached" {
        priority "high"

        matches {
            path-prefix "/api/v1"
            method "GET"
        }

        upstream "api-backend"

        policies {
            timeout-secs 30

            cache {
                enabled #true

                // Cache TTL
                ttl-secs 300  // 5 minutes

                // Vary cache by these headers
                vary-headers "Accept" "Accept-Encoding" "Accept-Language"

                // Respect Cache-Control headers from upstream
                respect-cache-control #true

                // Stale-while-revalidate: serve stale while refreshing
                stale-while-revalidate-secs 60

                // Stale-if-error: serve stale on upstream error
                stale-if-error-secs 300
            }
        }
    }

    // Static assets with aggressive caching
    route "static-assets" {
        priority "normal"

        matches {
            path-prefix "/static"
            method "GET"
        }

        upstream "static-backend"

        policies {
            timeout-secs 10

            cache {
                enabled #true

                // Long TTL for static assets
                ttl-secs 86400  // 24 hours

                // Only vary by Accept-Encoding
                vary-headers "Accept-Encoding"

                // Ignore Cache-Control from origin
                respect-cache-control #false

                // Long stale times for availability
                stale-while-revalidate-secs 3600
                stale-if-error-secs 86400
            }

            response-headers {
                set {
                    "Cache-Control" "public, max-age=86400, immutable"
                }
            }
        }
    }

    // Short-lived cache for dynamic content
    route "dynamic-cached" {
        priority "normal"

        matches {
            path-prefix "/api/feed"
            method "GET"
        }

        upstream "api-backend"

        policies {
            timeout-secs 30

            cache {
                enabled #true
                ttl-secs 30  // Short TTL
                vary-headers "Accept" "Authorization"
                respect-cache-control #true
            }
        }
    }

    // API key-based cache variation
    route "api-key-cached" {
        priority "high"

        matches {
            path-prefix "/api/user"
            method "GET"
            header "X-API-Key"
        }

        upstream "api-backend"

        policies {
            timeout-secs 30

            cache {
                enabled #true
                ttl-secs 60
                // Cache varies by API key (per-user cache)
                vary-headers "X-API-Key" "Accept"
                respect-cache-control #true
            }
        }
    }

    // Slow endpoint with long cache
    route "slow-endpoint" {
        priority "normal"

        matches {
            path-prefix "/api/reports"
            method "GET"
        }

        upstream "slow-backend"

        policies {
            timeout-secs 120

            cache {
                enabled #true
                // Long cache for expensive computations
                ttl-secs 3600  // 1 hour
                vary-headers "Accept"
                stale-while-revalidate-secs 600
                stale-if-error-secs 3600
            }
        }
    }

    // Cache bypass for authenticated requests
    route "no-cache-auth" {
        priority "high"

        matches {
            path-prefix "/api/private"
            method "GET"
            header "Authorization"
        }

        upstream "api-backend"

        policies {
            timeout-secs 30

            // Disable caching for authenticated requests
            cache {
                enabled #false
            }
        }
    }

    // POST requests are not cached
    route "api-write" {
        priority "high"

        matches {
            path-prefix "/api"
            method "POST" "PUT" "DELETE" "PATCH"
        }

        upstream "api-backend"

        policies {
            timeout-secs 30
            // No cache block - mutations are not cached
        }
    }

    // Cache purge endpoint
    route "cache-purge" {
        priority "critical"

        matches {
            path-prefix "/_cache/purge"
            method "POST" "DELETE"
        }

        builtin-handler "cache-purge"

        policies {
            failure-mode "closed"
        }
    }

    // Cache stats endpoint
    route "cache-stats" {
        priority "critical"

        matches {
            path "/_cache/stats"
            method "GET"
        }

        builtin-handler "cache-stats"
    }

    // Health check
    route "health" {
        priority "critical"

        matches {
            path "/health"
        }

        builtin-handler "health"
    }
}

observability {
    metrics {
        enabled #true
        address "0.0.0.0:9090"
        path "/metrics"
        // Cache metrics:
        // - sentinel_cache_hits_total
        // - sentinel_cache_misses_total
        // - sentinel_cache_stale_hits_total
        // - sentinel_cache_size_bytes
        // - sentinel_cache_entries_count
        // - sentinel_cache_evictions_total
    }

    logging {
        level "info"
        format "json"

        access-log {
            enabled #true
            file "/var/log/sentinel/access.log"
            // Cache status in logs: HIT, MISS, STALE, BYPASS
        }
    }
}

limits {
    max-header-size-bytes 8192
    max-header-count 100
    max-body-size-bytes 10485760
}
```

## Setup

### 1. Start Sentinel

```bash
sentinel -c sentinel.kdl
```

### 2. Start Backend Services

```bash
# Start API backend
node api/server.js --port 8080 &

# Start static file server
python -m http.server 8080 --directory /var/www/static &
```

## Testing

### Cache Hit/Miss

```bash
# First request - MISS
curl -I http://localhost:8080/api/v1/users
# X-Cache-Status: MISS

# Second request - HIT
curl -I http://localhost:8080/api/v1/users
# X-Cache-Status: HIT
```

### Stale-While-Revalidate

```bash
# Request after TTL but within stale window
curl -I http://localhost:8080/api/v1/users
# X-Cache-Status: STALE
# Response served immediately while background refresh happens
```

### Cache Stats

```bash
curl http://localhost:8080/_cache/stats
```

Response:
```json
{
  "entries": 156,
  "size_bytes": 2345678,
  "hits": 12345,
  "misses": 1234,
  "stale_hits": 56,
  "evictions": 23
}
```

### Cache Purge

```bash
# Purge specific path
curl -X POST "http://localhost:8080/_cache/purge?path=/api/v1/users"

# Purge by prefix
curl -X POST "http://localhost:8080/_cache/purge?prefix=/api/v1/"

# Purge all
curl -X DELETE "http://localhost:8080/_cache/purge"
```

### Monitor Cache Metrics

```bash
curl http://localhost:9090/metrics | grep cache
```

## Customizations

### Disk-Based Cache

```kdl
cache {
    enabled #true

    backend "disk" {
        path "/var/cache/sentinel"
        max-size-mb 10240  // 10GB
        shards 16
    }
}
```

### Hybrid Cache (Memory + Disk)

```kdl
cache {
    enabled #true

    backend "hybrid" {
        memory-max-size-mb 512
        disk-path "/var/cache/sentinel"
        disk-max-size-mb 10240
    }
}
```

### Cache Key Customization

```kdl
route "custom-cache-key" {
    policies {
        cache {
            enabled #true
            ttl-secs 300
            // Include specific query params in cache key
            vary-query-params "page" "limit" "sort"
            // Ignore certain query params
            ignore-query-params "timestamp" "nonce"
        }
    }
}
```

### Conditional Caching

```kdl
route "conditional-cache" {
    policies {
        cache {
            enabled #true
            ttl-secs 300
            // Only cache successful responses
            cacheable-status-codes 200 301 302
            // Don't cache responses larger than 10MB
            max-cacheable-size-bytes 10485760
        }
    }
}
```

## Next Steps

- [Distributed Rate Limiting](../distributed-rate-limit/) - Add rate limiting
- [Static Site](../static-site/) - Serve static files
- [API Gateway](../api-gateway/) - Complete API management
