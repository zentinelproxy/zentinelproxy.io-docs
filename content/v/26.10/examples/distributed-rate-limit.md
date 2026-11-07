+++
title = "Distributed Rate Limiting"
weight = 15
updated = 2026-10-20
+++

Configure distributed rate limiting across multiple Zentinel instances using Redis or Memcached backends. This example shows how to implement consistent rate limiting in multi-instance deployments.

{% callout(type="warning", title="Build with the distributed feature") %}
The Redis and memcached backends are used from 26.10_6, and only in a binary
built with the `distributed-rate-limit` feature. The official release binaries
and images are built without it: they enforce these filters **per instance**
and log a warning that the feature is missing. Build from source:

```bash
cargo build --release -p zentinel-proxy --features distributed-rate-limit
```

Before 26.10_6 the backends were not used in any build, so every limit on this
page was enforced per instance. See
[Filters: Distributed Rate Limiting](/configuration/filters/#distributed-rate-limiting).
{% end %}

## Use Case

- Rate limit across multiple Zentinel instances
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
    │Zentinel │        │Zentinel │        │Zentinel │
    │  :8080  │        │  :8080  │        │  :8080  │
    └────┬────┘        └────┬────┘        └────┬────┘
         │                  │                  │
         └──────────────────┼──────────────────┘
                            │
                    ┌───────▼───────┐
                    │     Redis     │
                    │   (buckets)   │
                    └───────────────┘
```

## Configuration

Create `zentinel.kdl`:

```kdl
// Distributed Rate Limiting Configuration
// Multi-instance rate limiting with Redis backend

system {
    worker-threads 4
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

        load-balancing "round_robin"

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

        load-balancing "least_connections"
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
        redis-prefix "zentinel:ratelimit:"
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
        redis-prefix "zentinel:api-ratelimit:"
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
        redis-prefix "zentinel:delay-ratelimit:"
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
        redis-prefix "zentinel:free:"
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
        redis-prefix "zentinel:premium:"
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
        // Refused requests: zentinel_rate_limited_total{route=...}
        // and zentinel_blocked_requests_total{reason="rate_limited"}
    }

    logging {
        level "info"
        format "json"

        access-log {
            enabled #true
            file "/var/log/zentinel/access.log"
        }
    }
}

limits {
    max-header-size 8192
    max-header-count 100
    max-body-size 10485760
}
```

## Setup

### 1. Deploy Redis

```bash
# Using Docker
docker run -d --name redis \
  -p 6379:6379 \
  redis:7-alpine
```

Every instance points `redis-url` at the same server.

### 2. Start Zentinel

Use a binary built with `--features distributed-rate-limit` (see above):

```bash
zentinel -c zentinel.kdl
```

A release binary starts too, but logs `Rate limit backend "redis" needs the
distributed-rate-limit-redis feature, which this build lacks; limiting locally
(per instance) instead` and limits each instance separately.

### 3. Start Backend Services

```bash
# Start API backends
node api/server.js --port 8080 &
```

## Testing

### Basic Rate Limiting

```bash
# Send 300 requests rapidly
for i in {1..300}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    http://localhost:8080/api/public/test
done | sort | uniq -c
```

`redis-rate-limit` is a token bucket of `burst 200` refilled at `max-rps 100`.
The first 200 requests empty the bucket, and after that about 100 a second are
admitted, so a burst of 300 sent faster than a second gets roughly:
```
~220 200
 ~80 429
```

Run the same loop against two instances at once: with the Redis backend they
share one bucket per client, so the total admitted stays the same. On a binary
without the feature each instance admits its own 200.

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

memcached 1.6 or later is needed (the meta protocol). From 26.10_6 a URL with
an IP address (`memcache://10.0.0.5:11211`) connects; before, only a host name
did.

```kdl
filter "memcached-rate-limit" {
    type "rate-limit"
    max-rps 100
    burst 200
    key "client-ip"
    on-limit "reject"

    backend "memcached"
    memcached-url "memcache://memcached.internal:11211"
    memcached-prefix "zentinel:ratelimit:"
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
    redis-prefix "zentinel:enterprise:"
    redis-fallback-local #true
}
```

## Next Steps

- [HTTP Caching](../http-caching/) - Add response caching
- [API Gateway](../api-gateway/) - Complete API management
- [Load Balancer](../load-balancer/) - Advanced load balancing
