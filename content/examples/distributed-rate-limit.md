+++
title = "Distributed Rate Limiting"
weight = 15
+++

Configure distributed rate limiting across multiple Sentinel instances using Redis or Memcached backends. This example shows how to implement consistent rate limiting in multi-instance deployments.

## Use Case

- Rate limit across multiple Sentinel instances
- Per-client, per-API-key, or per-organization limits
- Tiered rate limits for different user types
- Graceful degradation with delay instead of reject
- Fallback to local rate limiting when backend unavailable

## Architecture

```
                    ┌─────────────────┐
                    │    Clients      │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
    ┌─────────┐        ┌─────────┐        ┌─────────┐
    │Sentinel │        │Sentinel │        │Sentinel │
    │  :8080  │        │  :8080  │        │  :8080  │
    └────┬────┘        └────┬────┘        └────┬────┘
         │                  │                  │
         └──────────────────┼──────────────────┘
                            │
                    ┌───────▼───────┐
                    │ Redis Cluster │
                    │   (counters)  │
                    └───────────────┘
```

## Configuration

Create `sentinel.kdl`:

```kdl
// Distributed Rate Limiting Configuration
// Multi-instance rate limiting with Redis backend

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
        target "10.0.1.12:8080" weight=1

        load-balancing "round-robin"

        health-check {
            type "http" {
                path "/health"
                expected-status 200
            }
            interval-secs 10
        }
    }

    upstream "premium-backend" {
        target "10.0.2.10:8080" weight=1
        target "10.0.2.11:8080" weight=1

        load-balancing "least-connections"
    }
}

// =============================================================================
// Filter definitions with different rate limit backends
// =============================================================================
filters {
    // Redis-backed distributed rate limiting
    filter "redis-rate-limit" {
        type "rate-limit"

        max-rps 100
        burst 200
        key "client-ip"
        on-limit "reject"

        // Redis backend for distributed counting
        backend "redis"
        redis-url "redis://redis-cluster.internal:6379"
        redis-prefix "sentinel:ratelimit:"
        redis-pool-size 10
        redis-timeout-ms 50
        redis-fallback-local #true  // Fall back to local if Redis unavailable
    }

    // Redis rate limit with API key as key
    filter "redis-api-rate-limit" {
        type "rate-limit"

        max-rps 1000
        burst 2000
        key "header:X-API-Key"
        on-limit "reject"

        backend "redis"
        redis-url "redis://redis-cluster.internal:6379"
        redis-prefix "sentinel:api-ratelimit:"
        redis-pool-size 20
        redis-timeout-ms 100
        redis-fallback-local #true
    }

    // Redis rate limit with delay action (graceful degradation)
    filter "redis-rate-delay" {
        type "rate-limit"

        max-rps 50
        burst 100
        key "client-ip"
        on-limit "delay"  // Delay instead of reject
        max-delay-ms 5000  // Max 5 second delay

        backend "redis"
        redis-url "redis://redis-cluster.internal:6379"
        redis-prefix "sentinel:delay-ratelimit:"
        redis-pool-size 10
        redis-timeout-ms 50
        redis-fallback-local #true
    }

    // Tiered rate limits
    filter "free-tier-limit" {
        type "rate-limit"
        max-rps 10
        burst 20
        key "header:X-User-Id"
        on-limit "reject"
        backend "redis"
        redis-url "redis://redis-cluster.internal:6379"
        redis-prefix "sentinel:free:"
        redis-fallback-local #true
    }

    filter "premium-tier-limit" {
        type "rate-limit"
        max-rps 1000
        burst 2000
        key "header:X-User-Id"
        on-limit "reject"
        backend "redis"
        redis-url "redis://redis-cluster.internal:6379"
        redis-prefix "sentinel:premium:"
        redis-fallback-local #true
    }

    // Local rate limiting (single instance only)
    filter "local-rate-limit" {
        type "rate-limit"
        max-rps 1000
        burst 2000
        key "client-ip"
        on-limit "reject"
        backend "local"
    }
}

routes {
    // Public API with Redis rate limiting
    route "public-api" {
        priority "normal"

        matches {
            path-prefix "/api/public"
        }

        upstream "api-backend"
        filters "redis-rate-limit"

        policies {
            timeout-secs 30
            failure-mode "open"
        }
    }

    // Authenticated API with API key rate limiting
    route "authenticated-api" {
        priority "high"

        matches {
            path-prefix "/api/v1"
            header "X-API-Key"
        }

        upstream "api-backend"
        filters "redis-api-rate-limit"

        policies {
            timeout-secs 30
            failure-mode "closed"
        }
    }

    // Tiered API access
    route "free-tier-api" {
        priority "normal"

        matches {
            path-prefix "/api"
            header "X-User-Tier" "free"
        }

        upstream "api-backend"
        filters "free-tier-limit"

        policies {
            timeout-secs 30
        }
    }

    route "premium-tier-api" {
        priority "high"

        matches {
            path-prefix "/api"
            header "X-User-Tier" "premium"
        }

        upstream "premium-backend"
        filters "premium-tier-limit"

        policies {
            timeout-secs 60
        }
    }

    // Rate limit with delay (graceful degradation)
    route "graceful-api" {
        priority "normal"

        matches {
            path-prefix "/api/graceful"
        }

        upstream "api-backend"
        filters "redis-rate-delay"

        policies {
            timeout-secs 35  // Account for potential delay
        }
    }

    // Layered rate limits (multiple filters)
    route "layered-rate-limit" {
        priority "high"

        matches {
            path-prefix "/api/protected"
        }

        upstream "api-backend"
        // Apply both per-IP and per-API-key limits
        filters "redis-rate-limit" "redis-api-rate-limit"

        policies {
            timeout-secs 30
            failure-mode "closed"
        }
    }

    // Health check (no rate limiting)
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
        // Rate limit metrics:
        // - sentinel_rate_limit_requests_total
        // - sentinel_rate_limit_limited_total
        // - sentinel_rate_limit_backend_latency_seconds
        // - sentinel_rate_limit_fallback_total
    }

    logging {
        level "info"
        format "json"

        access-log {
            enabled #true
            file "/var/log/sentinel/access.log"
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

### 1. Deploy Redis

```bash
# Using Docker
docker run -d --name redis \
  -p 6379:6379 \
  redis:7-alpine

# Or using Redis Cluster for HA
docker-compose up -d redis-cluster
```

### 2. Start Sentinel

```bash
sentinel -c sentinel.kdl
```

### 3. Start Backend Services

```bash
# Start API backends
node api/server.js --port 8080 &
```

## Testing

### Basic Rate Limiting

```bash
# Send 150 requests rapidly
for i in {1..150}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    http://localhost:8080/api/public/test
done | sort | uniq -c
```

Expected output shows 429 responses after limit exceeded:
```
100 200
 50 429
```

### API Key Rate Limiting

```bash
# Test with API key
for i in {1..50}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -H "X-API-Key: test-key-123" \
    http://localhost:8080/api/v1/users
done | sort | uniq -c
```

### Tiered Rate Limits

```bash
# Free tier (10 RPS limit)
curl -H "X-User-Tier: free" -H "X-User-Id: user1" \
  http://localhost:8080/api/data

# Premium tier (1000 RPS limit)
curl -H "X-User-Tier: premium" -H "X-User-Id: user2" \
  http://localhost:8080/api/data
```

### Check Rate Limit Headers

```bash
curl -I http://localhost:8080/api/public/test
```

Response headers include:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1234567890
```

### Monitor Metrics

```bash
curl http://localhost:9090/metrics | grep rate_limit
```

## Customizations

### Memcached Backend

```kdl
filter "memcached-rate-limit" {
    type "rate-limit"
    max-rps 100
    burst 200
    key "client-ip"
    on-limit "reject"

    backend "memcached"
    memcached-url "memcache://memcached.internal:11211"
    memcached-prefix "sentinel:ratelimit:"
    memcached-pool-size 10
    memcached-timeout-ms 50
    memcached-fallback-local #true
}
```

### Custom Rate Limit Keys

```kdl
// By header value
filter "by-header" {
    type "rate-limit"
    key "header:X-Tenant-Id"
}

// By client IP (default)
filter "by-ip" {
    type "rate-limit"
    key "client-ip"
}

// By JWT claim (requires auth agent)
filter "by-user" {
    type "rate-limit"
    key "header:X-User-Id"
}
```

### Enterprise Tier with Delay

```kdl
filter "enterprise-tier-limit" {
    type "rate-limit"
    max-rps 10000
    burst 20000
    key "header:X-Org-Id"
    on-limit "delay"  // Slow down instead of reject
    max-delay-ms 1000

    backend "redis"
    redis-url "redis://redis-cluster.internal:6379"
    redis-prefix "sentinel:enterprise:"
    redis-fallback-local #true
}
```

## Next Steps

- [HTTP Caching](../http-caching/) - Add response caching
- [API Gateway](../api-gateway/) - Complete API management
- [Load Balancer](../load-balancer/) - Advanced load balancing
