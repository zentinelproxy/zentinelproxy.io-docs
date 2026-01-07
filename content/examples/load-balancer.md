+++
title = "Load Balancer"
weight = 3
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
                         │    Sentinel     │
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

Create `sentinel.kdl`:

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
            cert-file "/etc/sentinel/certs/lb.crt"
            key-file "/etc/sentinel/certs/lb.key"
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
        targets {
            target { address "10.0.1.10:3000" weight 100 }
            target { address "10.0.1.11:3000" weight 100 }
            target { address "10.0.1.12:3000" weight 100 }
            target { address "10.0.1.13:3000" weight 100 }
            target { address "10.0.1.14:3000" weight 100 }
        }
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
        targets {
            target { address "10.0.1.10:3000" weight 100 }  // 50% traffic
            target { address "10.0.1.11:3000" weight 50 }   // 25% traffic
            target { address "10.0.1.12:3000" weight 50 }   // 25% traffic
        }
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

## Deployment Patterns

### Blue-Green Deployment

```kdl
upstreams {
    // Blue (current production)
    upstream "app-blue" {
        targets {
            target { address "10.0.1.10:3000" }
            target { address "10.0.1.11:3000" }
        }
    }

    // Green (new version)
    upstream "app-green" {
        targets {
            target { address "10.0.2.10:3000" }
            target { address "10.0.2.11:3000" }
        }
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
kill -HUP $(pgrep sentinel)
```

### Canary Deployment

```kdl
upstreams {
    upstream "app-canary" {
        targets {
            // Stable (90% traffic)
            target { address "10.0.1.10:3000" weight 90 }
            target { address "10.0.1.11:3000" weight 90 }
            // Canary (10% traffic)
            target { address "10.0.2.10:3000" weight 10 }
        }
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
curl http://localhost:9090/metrics | grep -E "sentinel_(upstream|connections)"
```

| Metric | Description |
|--------|-------------|
| `sentinel_upstream_health` | Health status per target (1=healthy, 0=unhealthy) |
| `sentinel_upstream_connections_active` | Active connections per target |
| `sentinel_upstream_requests_total` | Requests per target |
| `sentinel_upstream_latency_seconds` | Latency per target |

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
