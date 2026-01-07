+++
title = "Microservices"
weight = 5
+++

Route traffic to multiple backend services based on path, headers, and other criteria. This example demonstrates a microservices architecture with Sentinel as the API gateway.

## Use Case

- Route to different backend services by path
- Service-specific timeouts and retry policies
- Circuit breakers for fault isolation
- Centralized authentication and rate limiting

## Architecture

```
                              ┌─────────────────┐
                              │    Sentinel     │
                              │   API Gateway   │
                              └────────┬────────┘
                                       │
       ┌───────────────┬───────────────┼───────────────┬───────────────┐
       │               │               │               │               │
       ▼               ▼               ▼               ▼               ▼
  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
  │  Users  │    │ Orders  │    │Products │    │ Search  │    │  Auth   │
  │ :3001   │    │ :3002   │    │ :3003   │    │ :3004   │    │ :3005   │
  └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
```

## Configuration

Create `sentinel.kdl`:

```kdl
// Microservices Gateway Configuration
// Routes to multiple backend services

system {
    worker-threads 0
    graceful-shutdown-timeout-secs 60
}

listeners {
    listener "https" {
        address "0.0.0.0:8443"
        protocol "https"
        tls {
            cert-file "/etc/sentinel/certs/api.crt"
            key-file "/etc/sentinel/certs/api.key"
        }
    }
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
}

routes {
    // Health check
    route "health" {
        priority 1000
        matches { path "/health" }
        service-type "builtin"
        builtin-handler "health"
    }

    // Authentication service - no auth required (handles login)
    route "auth" {
        priority 500
        matches {
            path-prefix "/api/auth/"
        }
        upstream "auth-service"
        service-type "api"
        policies {
            timeout-secs 10
        }
    }

    // User service
    route "users" {
        priority 200
        matches {
            path-prefix "/api/users/"
        }
        upstream "user-service"
        agents ["auth" "ratelimit"]
        service-type "api"
        circuit-breaker {
            failure-threshold 5
            timeout-seconds 30
        }
        retry-policy {
            max-attempts 2
            retryable-status-codes 502 503 504
        }
        policies {
            timeout-secs 30
            request-headers {
                set { "X-Service" "users" }
            }
        }
    }

    // Order service - higher timeout for complex operations
    route "orders" {
        priority 200
        matches {
            path-prefix "/api/orders/"
        }
        upstream "order-service"
        agents ["auth" "ratelimit"]
        service-type "api"
        circuit-breaker {
            failure-threshold 3
            timeout-seconds 60
        }
        retry-policy {
            max-attempts 3
            retryable-status-codes 502 503 504
        }
        policies {
            timeout-secs 60
            max-body-size "10MB"
            request-headers {
                set { "X-Service" "orders" }
            }
        }
    }

    // Product catalog - read-heavy, cacheable
    route "products" {
        priority 200
        matches {
            path-prefix "/api/products/"
            method "GET"
        }
        upstream "product-service"
        agents ["ratelimit"]  // No auth for public product listing
        service-type "api"
        retry-policy {
            max-attempts 3
        }
        policies {
            timeout-secs 10
            response-headers {
                set { "Cache-Control" "public, max-age=60" }
            }
        }
    }

    // Product mutations - require auth
    route "products-write" {
        priority 250
        matches {
            path-prefix "/api/products/"
            method "POST" "PUT" "DELETE"
        }
        upstream "product-service"
        agents ["auth" "ratelimit"]
        service-type "api"
        policies {
            timeout-secs 30
        }
    }

    // Search service - separate infrastructure
    route "search" {
        priority 200
        matches {
            path-prefix "/api/search/"
        }
        upstream "search-service"
        service-type "api"
        circuit-breaker {
            failure-threshold 10
            timeout-seconds 15
        }
        policies {
            timeout-secs 5  // Fast timeout, search should be quick
            failure-mode "open"  // Degrade gracefully if search is down
        }
    }

    // Webhooks - external callbacks
    route "webhooks" {
        priority 200
        matches {
            path-prefix "/webhooks/"
        }
        upstream "webhook-service"
        policies {
            timeout-secs 30
            max-body-size "1MB"
        }
    }

    // Fallback 404
    route "not-found" {
        priority 1
        matches {
            path-prefix "/"
        }
        service-type "builtin"
        builtin-handler "not-found"
    }
}

upstreams {
    upstream "auth-service" {
        targets {
            target { address "auth.internal:3005" }
        }
        health-check {
            type "http" { path "/health" }
            interval-secs 5
        }
    }

    upstream "user-service" {
        targets {
            target { address "users-1.internal:3001" }
            target { address "users-2.internal:3001" }
        }
        load-balancing "least-connections"
        health-check {
            type "http" { path "/health" }
            interval-secs 5
        }
    }

    upstream "order-service" {
        targets {
            target { address "orders-1.internal:3002" }
            target { address "orders-2.internal:3002" }
            target { address "orders-3.internal:3002" }
        }
        load-balancing "round-robin"
        health-check {
            type "http" { path "/health" }
            interval-secs 5
        }
    }

    upstream "product-service" {
        targets {
            target { address "products-1.internal:3003" }
            target { address "products-2.internal:3003" }
        }
        load-balancing "round-robin"
        health-check {
            type "http" { path "/health" }
            interval-secs 10
        }
    }

    upstream "search-service" {
        targets {
            target { address "search.internal:3004" }
        }
        health-check {
            type "http" { path "/health" }
            interval-secs 5
        }
    }

    upstream "webhook-service" {
        targets {
            target { address "webhooks.internal:3006" }
        }
    }
}

agents {
    agent "auth" {
        transport "unix_socket" {
            path "/var/run/sentinel/auth.sock"
        }
        events ["request_headers"]
        timeout-ms 50
        failure-mode "closed"
    }

    agent "ratelimit" {
        transport "unix_socket" {
            path "/var/run/sentinel/ratelimit.sock"
        }
        events ["request_headers"]
        timeout-ms 20
        failure-mode "open"
    }
}

observability {
    metrics {
        enabled #true
        address "0.0.0.0:9090"
    }
    logging {
        level "info"
        format "json"
    }
    tracing {
        enabled #true
        service-name "api-gateway"
        endpoint "http://jaeger.internal:4317"
        sample-rate 0.1  // Sample 10% of requests
    }
}
```

## Service Discovery

### Static Configuration

As shown above, manually configure upstream targets.

### DNS-Based Discovery

```kdl
upstreams {
    upstream "user-service" {
        discovery "dns" {
            hostname "users.service.internal"
            port 3001
            refresh-interval-secs 30
        }
        load-balancing "round-robin"
    }
}
```

### Kubernetes Service Discovery

```kdl
upstreams {
    upstream "user-service" {
        discovery "kubernetes" {
            namespace "production"
            service "user-service"
            port-name "http"
        }
    }
}
```

## Testing

### Route to User Service

```bash
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8080/api/users/123
```

### Route to Product Service (Public)

```bash
curl http://localhost:8080/api/products/
```

### Check Circuit Breaker Status

```bash
curl http://localhost:9090/metrics | grep circuit
```

### Trace a Request

```bash
curl -H "X-Request-Id: test-123" \
     -H "Authorization: Bearer $TOKEN" \
     http://localhost:8080/api/orders/
```

Check Jaeger UI for trace with ID `test-123`.

## Service Mesh Patterns

### Request Hedging

Send duplicate requests to reduce tail latency:

```kdl
route "search" {
    upstream "search-service"
    hedge {
        enabled #true
        delay-ms 50  // Hedge after 50ms
        max-requests 2
    }
}
```

### Traffic Mirroring

Mirror production traffic to staging:

```kdl
route "products" {
    upstream "product-service"
    mirror {
        upstream "product-service-staging"
        percentage 10  // Mirror 10% of traffic
    }
}
```

### Request Shadowing

```kdl
route "api" {
    upstream "api-v2"
    shadow {
        upstream "api-v3-canary"
        percentage 5
    }
}
```

## Customizations

### Per-Service Rate Limits

```bash
# User service: 100 req/min
sentinel-agent-ratelimit \
    --socket /var/run/sentinel/ratelimit-users.sock \
    --requests-per-minute 100 &

# Search service: 1000 req/min
sentinel-agent-ratelimit \
    --socket /var/run/sentinel/ratelimit-search.sock \
    --requests-per-minute 1000 &
```

### Service-Specific Error Pages

```kdl
route "api" {
    error-pages {
        default-format "json"
        pages {
            "503" {
                format "json"
                message "Service temporarily unavailable"
            }
        }
    }
}
```

## Next Steps

- [Observability](../observability/) - Distributed tracing setup
- [Security](../security/) - Add WAF protection
- [Load Balancer](../load-balancer/) - Advanced load balancing
