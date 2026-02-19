+++
title = "Load Balancer"
weight = 3
updated = 2026-02-19
+++

A load balancer configuration distributing traffic across multiple backend servers with health checks, session affinity, and weighted routing.

## Use Case

- Distribute traffic across multiple backend instances
- Handle backend failures gracefully
- Support blue-green and canary deployments
- Sticky sessions for stateful applications

## Architecture

```
                         ┌─────────────────┐
                         │    Zentinel     │
                         │  Load Balancer  │
                         └────────┬────────┘
                                  │
        ┌────────────┬────────────┼────────────┬────────────┐
        │            │            │            │            │
        ▼            ▼            ▼            ▼            ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
   │ App 1   │ │ App 2   │ │ App 3   │ │ App 4   │ │ App 5   │
   │ :3000   │ │ :3001   │ │ :3002   │ │ :3003   │ │ :3004   │
   └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
```

## Configuration

Create `zentinel.kdl`:

```kdl
// Load Balancer Configuration
// Distributes traffic across multiple backends

system {
    worker-threads 0
    graceful-shutdown-timeout-secs 60
}

listeners {
    listener "http" {
        address "0.0.0.0:8080"
        protocol "http"
    }
    listener "https" {
        address "0.0.0.0:8443"
        protocol "https"
        tls {
            cert-file "/etc/zentinel/certs/lb.crt"
            key-file "/etc/zentinel/certs/lb.key"
        }
    }
}

routes {
    // Health check endpoint
    route "health" {
        priority 1000
        matches {
            path "/health"
        }
        service-type "builtin"
        builtin-handler "health"
    }

    // Upstream health status (admin)
    route "upstream-status" {
        priority 999
        matches {
            path "/admin/upstreams"
            header name="X-Admin-Key" value="${ADMIN_KEY}"
        }
        service-type "builtin"
        builtin-handler "upstreams"
    }

    // Main application - round robin
    route "app" {
        matches {
            path-prefix "/"
        }
        upstream "app-cluster"
        circuit-breaker {
            failure-threshold 5
            success-threshold 2
            timeout-seconds 30
        }
        retry-policy {
            max-attempts 3
            retryable-status-codes 502 503 504
        }
    }
}

upstreams {
    upstream "app-cluster" {
        target "10.0.1.10:3000" weight=100
        target "10.0.1.11:3000" weight=100
        target "10.0.1.12:3000" weight=100
        target "10.0.1.13:3000" weight=100
        target "10.0.1.14:3000" weight=100
        load-balancing "round-robin"
        health-check {
            type "http" {
                path "/health"
                expected-status 200
            }
            interval-secs 5
            timeout-secs 3
            unhealthy-threshold 3
            healthy-threshold 2
        }
        connection-pool {
            max-idle-connections 100
            idle-timeout-secs 60
        }
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
}
```

## Load Balancing Algorithms

### Round Robin (Default)

```kdl
upstreams {
    upstream "app" {
        load-balancing "round-robin"
    }
}
```

Distributes requests evenly across all healthy backends.

### Weighted Round Robin

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

upstreams {
    upstream "app" {
        target "10.0.1.10:3000" weight=100
        target "10.0.1.11:3000" weight=50
        target "10.0.1.12:3000" weight=50
        load-balancing "weighted-round-robin"
    }
}

routes {
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
    }
}

```

### Least Connections

```kdl
upstreams {
    upstream "app" {
        load-balancing "least-connections"
    }
}
```

Routes to the backend with fewest active connections.

### IP Hash (Sticky Sessions)

```kdl
upstreams {
    upstream "app" {
        load-balancing "ip-hash"
    }
}
```

Same client IP always routes to the same backend (when available).

### Random

```kdl
upstreams {
    upstream "app" {
        load-balancing "random"
    }
}
```

### Maglev (Consistent Hashing)

```kdl
upstreams {
    upstream "cache-cluster" {
        target "cache-1:6379"
        target "cache-2:6379"
        target "cache-3:6379"
        load-balancing "maglev"
    }
}
```

Google's Maglev algorithm provides O(1) lookup with minimal key redistribution when backends change. Ideal for cache clusters.

### Peak EWMA (Latency-Aware)

```kdl
upstreams {
    upstream "api" {
        target "api-1:8080"
        target "api-2:8080"
        target "api-3:8080"
        load-balancing "peak_ewma"
    }
}
```

Tracks latency using exponential moving average. Automatically routes away from slow backends.

### Locality-Aware (Multi-Region)

```kdl
upstreams {
    upstream "global-api" {
        target "10.0.1.1:8080" {
            metadata { "zone" "us-east-1a" }
        }
        target "10.0.1.2:8080" {
            metadata { "zone" "us-east-1b" }
        }
        target "10.0.2.1:8080" {
            metadata { "zone" "eu-west-1a" }
        }
        load-balancing "locality_aware"
    }
}
```

Prefers backends in the same zone as the proxy, reducing cross-region latency.

### Weighted Least Connections

```kdl
upstreams {
    upstream "mixed-capacity" {
        target "large-server:8080" weight=200
        target "medium-server:8080" weight=100
        target "small-server:8080" weight=50
        load-balancing "weighted_least_conn"
    }
}
```

Selects backends with the lowest connections-to-weight ratio. Use when backends have different capacities.

### Deterministic Subsetting (Large Clusters)

```kdl
upstreams {
    upstream "mega-cluster" {
        // 1000+ targets
        target "backend-001:8080"
        target "backend-002:8080"
        // ... many more ...
        target "backend-999:8080"
        load-balancing "deterministic_subset"
    }
}
```

Each proxy instance connects to a subset of backends. Reduces connection overhead for very large clusters.

### Adaptive (Self-Tuning)

```kdl
upstreams {
    upstream "api" {
        target "api-1:8080" weight=100
        target "api-2:8080" weight=100
        target "api-3:8080" weight=100
        load-balancing "adaptive"
        health-check {
            type "http" {
                path "/health"
                expected-status 200
            }
            interval-secs 5
        }
    }
}
```

Dynamically adjusts weights based on response times and error rates.

### LLM Inference (Token-Based)

```kdl
upstreams {
    upstream "llm-cluster" {
        target "gpu-node-1:8080"
        target "gpu-node-2:8080"
        target "gpu-node-3:8080"
        load-balancing "least_tokens_queued"
    }
}
```

Specialized for LLM workloads. Routes to the backend with fewest tokens queued.

## Deployment Patterns

### Blue-Green Deployment

```kdl
upstreams {
    // Blue (current production)
    upstream "app-blue" {
        target "10.0.1.10:3000"
        target "10.0.1.11:3000"
    }

    // Green (new version)
    upstream "app-green" {
        target "10.0.2.10:3000"
        target "10.0.2.11:3000"
    }
}

routes {
    route "app" {
        matches {
            path-prefix "/"
        }
        // Switch between blue and green by changing this
        upstream "app-blue"
    }
}
```

Switch traffic by updating `upstream "app-blue"` to `upstream "app-green"` and reloading:

```bash
kill -HUP $(pgrep zentinel)
```

### Canary Deployment

```kdl
upstreams {
    upstream "app-canary" {
        // Stable (90% traffic)
        target "10.0.1.10:3000" weight=90
        target "10.0.1.11:3000" weight=90
        // Canary (10% traffic)
        target "10.0.2.10:3000" weight=10
        load-balancing "weighted-round-robin"
    }
}
```

### Header-Based Routing (A/B Testing)

```kdl
routes {
    // Beta users route to new version
    route "app-beta" {
        priority 100
        matches {
            path-prefix "/"
            header name="X-Beta-User" value="true"
        }
        upstream "app-v2"
    }

    // Everyone else gets stable version
    route "app-stable" {
        priority 50
        matches {
            path-prefix "/"
        }
        upstream "app-v1"
    }
}
```

## Testing

### Check Upstream Health

```bash
curl -H "X-Admin-Key: $ADMIN_KEY" http://localhost:8080/admin/upstreams
```

Response:

```json
{
  "upstreams": {
    "app-cluster": {
      "healthy": 5,
      "unhealthy": 0,
      "targets": [
        {"address": "10.0.1.10:3000", "healthy": true, "active_connections": 12},
        {"address": "10.0.1.11:3000", "healthy": true, "active_connections": 8}
      ]
    }
  }
}
```

### Verify Load Distribution

```bash
# Send 100 requests and check distribution
for i in {1..100}; do
  curl -s http://localhost:8080/whoami
done | sort | uniq -c
```

### Simulate Backend Failure

```bash
# Stop one backend
docker stop app-3

# Verify traffic continues
curl http://localhost:8080/

# Check health status
curl -H "X-Admin-Key: $ADMIN_KEY" http://localhost:8080/admin/upstreams
```

## Metrics

Key load balancer metrics:

```bash
curl http://localhost:9090/metrics | grep -E "zentinel_(upstream|connections)"
```

| Metric | Description |
|--------|-------------|
| `zentinel_upstream_health` | Health status per target (1=healthy, 0=unhealthy) |
| `zentinel_upstream_connections_active` | Active connections per target |
| `zentinel_upstream_requests_total` | Requests per target |
| `zentinel_upstream_latency_seconds` | Latency per target |

## Customizations

### Connection Draining

```kdl
upstreams {
    upstream "app" {
        connection-draining {
            enabled #true
            timeout-secs 30
        }
    }
}
```

Allows in-flight requests to complete before removing unhealthy targets.

### Slow Start

```kdl
upstreams {
    upstream "app" {
        slow-start {
            enabled #true
            duration-secs 60
        }
    }
}
```

Gradually increases traffic to newly healthy targets.

## Next Steps

- [Observability](../observability/) - Monitor load distribution
- [API Gateway](../api-gateway/) - Add authentication layer
- [Security](../security/) - Protect against attacks
