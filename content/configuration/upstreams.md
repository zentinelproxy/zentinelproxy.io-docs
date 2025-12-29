+++
title = "Upstreams"
weight = 5
+++

The `upstreams` block defines backend server pools. Each upstream contains one or more targets with load balancing, health checks, and connection pooling.

## Basic Configuration

```kdl
upstreams {
    upstream "backend" {
        targets {
            target { address "10.0.1.1:8080" }
            target { address "10.0.1.2:8080" }
            target { address "10.0.1.3:8080" }
        }
        load-balancing "round_robin"
    }
}
```

## Targets

### Target Definition

```kdl
targets {
    target {
        address "10.0.1.1:8080"
        weight 3
        max-requests 1000
    }
    target {
        address "10.0.1.2:8080"
        weight 2
    }
    target {
        address "10.0.1.3:8080"
        weight 1
    }
}
```

| Option | Default | Description |
|--------|---------|-------------|
| `address` | Required | Target address (`host:port`) |
| `weight` | `1` | Weight for weighted load balancing |
| `max-requests` | None | Maximum concurrent requests to this target |

### Target Metadata

```kdl
target {
    address "10.0.1.1:8080"
    metadata {
        "zone" "us-east-1a"
        "version" "v2.1.0"
    }
}
```

Metadata is available for custom load balancing decisions and observability.

## Load Balancing

```kdl
upstream "backend" {
    load-balancing "round_robin"
}
```

### Algorithms

| Algorithm | Description |
|-----------|-------------|
| `round_robin` | Sequential rotation through targets (default) |
| `least_connections` | Route to target with fewest active connections |
| `random` | Random target selection |
| `ip_hash` | Consistent routing based on client IP |
| `weighted` | Weighted random selection |
| `consistent_hash` | Consistent hashing for cache-friendly routing |
| `power_of_two_choices` | Pick best of two random targets |
| `adaptive` | Dynamic selection based on response times |

### Round Robin

```kdl
upstream "backend" {
    load-balancing "round_robin"
}
```

Simple sequential rotation. Good for homogeneous backends.

### Weighted

```kdl
upstream "backend" {
    targets {
        target { address "10.0.1.1:8080" weight=3 }  // 50% traffic
        target { address "10.0.1.2:8080" weight=2 }  // 33% traffic
        target { address "10.0.1.3:8080" weight=1 }  // 17% traffic
    }
    load-balancing "weighted"
}
```

Traffic distributed proportionally to weights. Use for:
- Different server capacities
- Gradual rollouts
- A/B testing

### Least Connections

```kdl
upstream "backend" {
    load-balancing "least_connections"
}
```

Routes to the target with the fewest active connections. Best for:
- Varying request durations
- Long-running connections
- Heterogeneous workloads

### IP Hash

```kdl
upstream "backend" {
    load-balancing "ip_hash"
}
```

Consistent routing based on client IP. Provides session affinity without cookies.

**Note:** Clients behind shared NAT will route to the same target.

### Consistent Hash

```kdl
upstream "backend" {
    load-balancing "consistent_hash"
}
```

Consistent hashing minimizes redistribution when targets are added/removed. Ideal for:
- Caching layers
- Stateful backends
- Maintaining locality

### Power of Two Choices

```kdl
upstream "backend" {
    load-balancing "power_of_two_choices"
}
```

Randomly selects two targets, routes to the one with fewer connections. Provides:
- Near-optimal load distribution
- O(1) selection time
- Better than pure random

### Adaptive

```kdl
upstream "backend" {
    load-balancing "adaptive"
}
```

Dynamically adjusts routing based on observed response times and error rates.

## Health Checks

### HTTP Health Check

```kdl
upstream "backend" {
    health-check {
        type "http" {
            path "/health"
            expected-status 200
            host "backend.internal"  // Optional Host header
        }
        interval-secs 10
        timeout-secs 5
        healthy-threshold 2
        unhealthy-threshold 3
    }
}
```

| Option | Default | Description |
|--------|---------|-------------|
| `type` | Required | Check type (`http`, `tcp`, `grpc`) |
| `interval-secs` | `10` | Time between checks |
| `timeout-secs` | `5` | Check timeout |
| `healthy-threshold` | `2` | Successes to mark healthy |
| `unhealthy-threshold` | `3` | Failures to mark unhealthy |

### TCP Health Check

```kdl
upstream "database" {
    health-check {
        type "tcp"
        interval-secs 5
        timeout-secs 2
    }
}
```

Simple TCP connection check. Use for non-HTTP services.

### gRPC Health Check

```kdl
upstream "grpc-service" {
    health-check {
        type "grpc" {
            service "grpc.health.v1.Health"
        }
        interval-secs 10
        timeout-secs 5
    }
}
```

Uses the gRPC Health Checking Protocol.

### Health Check Behavior

When a target fails health checks:

1. Target marked **unhealthy** after `unhealthy-threshold` failures
2. Traffic stops routing to unhealthy target
3. Health checks continue at `interval-secs`
4. Target marked **healthy** after `healthy-threshold` successes
5. Traffic resumes to recovered target

## Connection Pool

```kdl
upstream "backend" {
    connection-pool {
        max-connections 100
        max-idle 20
        idle-timeout-secs 60
        max-lifetime-secs 3600
    }
}
```

| Option | Default | Description |
|--------|---------|-------------|
| `max-connections` | `100` | Maximum connections per target |
| `max-idle` | `20` | Maximum idle connections to keep |
| `idle-timeout-secs` | `60` | Close idle connections after |
| `max-lifetime-secs` | None | Maximum connection lifetime |

### Connection Pool Sizing

| Scenario | max-connections | max-idle |
|----------|-----------------|----------|
| Low traffic | 20-50 | 5-10 |
| Medium traffic | 100 | 20 |
| High traffic | 500+ | 50+ |
| Long-lived connections | 50 | 10 |

**Guidelines:**
- `max-connections` = expected peak RPS × average request duration
- `max-idle` = 20-30% of `max-connections`
- Set `max-lifetime-secs` if backends have connection limits

## Timeouts

```kdl
upstream "backend" {
    timeouts {
        connect-secs 10
        request-secs 60
        read-secs 30
        write-secs 30
    }
}
```

| Timeout | Default | Description |
|---------|---------|-------------|
| `connect-secs` | `10` | TCP connection timeout |
| `request-secs` | `60` | Total request timeout |
| `read-secs` | `30` | Read timeout (response) |
| `write-secs` | `30` | Write timeout (request body) |

### Timeout Recommendations

| Service Type | connect | request | read | write |
|--------------|---------|---------|------|-------|
| Fast API | 5 | 30 | 15 | 15 |
| Standard API | 10 | 60 | 30 | 30 |
| Slow/batch | 10 | 300 | 120 | 60 |
| File upload | 10 | 600 | 30 | 300 |

## Upstream TLS

### Basic TLS to Upstream

```kdl
upstream "secure-backend" {
    targets {
        target { address "backend.internal:443" }
    }
    tls {
        sni "backend.internal"
    }
}
```

### mTLS to Upstream

```kdl
upstream "mtls-backend" {
    targets {
        target { address "secure.internal:443" }
    }
    tls {
        sni "secure.internal"
        client-cert "/etc/sentinel/certs/client.crt"
        client-key "/etc/sentinel/certs/client.key"
        ca-cert "/etc/sentinel/certs/backend-ca.crt"
    }
}
```

### TLS Options

| Option | Description |
|--------|-------------|
| `sni` | Server Name Indication hostname |
| `client-cert` | Client certificate for mTLS |
| `client-key` | Client private key for mTLS |
| `ca-cert` | CA certificate to verify upstream |
| `insecure-skip-verify` | Skip certificate verification (testing only) |

**Warning:** Never use `insecure-skip-verify` in production.

## Complete Examples

### Multi-tier Application

```kdl
upstreams {
    // Web tier
    upstream "web" {
        targets {
            target { address "web-1.internal:8080" weight=2 }
            target { address "web-2.internal:8080" weight=2 }
            target { address "web-3.internal:8080" weight=1 }
        }
        load-balancing "weighted"
        health-check {
            type "http" {
                path "/health"
                expected-status 200
            }
            interval-secs 10
            timeout-secs 5
        }
        connection-pool {
            max-connections 200
            max-idle 50
        }
    }

    // API tier
    upstream "api" {
        targets {
            target { address "api-1.internal:8080" }
            target { address "api-2.internal:8080" }
        }
        load-balancing "least_connections"
        health-check {
            type "http" {
                path "/api/health"
                expected-status 200
            }
            interval-secs 5
            unhealthy-threshold 2
        }
        timeouts {
            connect-secs 5
            request-secs 30
        }
    }

    // Cache tier
    upstream "cache" {
        targets {
            target { address "cache-1.internal:6379" }
            target { address "cache-2.internal:6379" }
            target { address "cache-3.internal:6379" }
        }
        load-balancing "consistent_hash"
        health-check {
            type "tcp"
            interval-secs 5
            timeout-secs 2
        }
    }
}
```

### Blue-Green Deployment

```kdl
upstreams {
    // Blue environment (current)
    upstream "api-blue" {
        targets {
            target { address "api-blue-1.internal:8080" }
            target { address "api-blue-2.internal:8080" }
        }
    }

    // Green environment (new version)
    upstream "api-green" {
        targets {
            target { address "api-green-1.internal:8080" }
            target { address "api-green-2.internal:8080" }
        }
    }

    // Canary routing (90% blue, 10% green)
    upstream "api-canary" {
        targets {
            target { address "api-blue-1.internal:8080" weight=45 }
            target { address "api-blue-2.internal:8080" weight=45 }
            target { address "api-green-1.internal:8080" weight=5 }
            target { address "api-green-2.internal:8080" weight=5 }
        }
        load-balancing "weighted"
    }
}
```

### Secure Internal Service

```kdl
upstreams {
    upstream "payment-service" {
        targets {
            target { address "payment.internal:443" }
        }
        tls {
            sni "payment.internal"
            client-cert "/etc/sentinel/certs/sentinel-client.crt"
            client-key "/etc/sentinel/certs/sentinel-client.key"
            ca-cert "/etc/sentinel/certs/internal-ca.crt"
        }
        health-check {
            type "http" {
                path "/health"
                expected-status 200
                host "payment.internal"
            }
            interval-secs 10
        }
        timeouts {
            connect-secs 5
            request-secs 30
        }
        connection-pool {
            max-connections 50
            max-idle 10
            max-lifetime-secs 300
        }
    }
}
```

## Default Values

| Setting | Default |
|---------|---------|
| `load-balancing` | `round_robin` |
| `target.weight` | `1` |
| `health-check.interval-secs` | `10` |
| `health-check.timeout-secs` | `5` |
| `health-check.healthy-threshold` | `2` |
| `health-check.unhealthy-threshold` | `3` |
| `connection-pool.max-connections` | `100` |
| `connection-pool.max-idle` | `20` |
| `connection-pool.idle-timeout-secs` | `60` |
| `timeouts.connect-secs` | `10` |
| `timeouts.request-secs` | `60` |
| `timeouts.read-secs` | `30` |
| `timeouts.write-secs` | `30` |

## Monitoring Upstream Health

Check upstream status via the admin endpoint:

```bash
curl http://localhost:9090/admin/upstreams
```

Response:

```json
{
  "upstreams": {
    "backend": {
      "targets": [
        {"address": "10.0.1.1:8080", "healthy": true, "connections": 45},
        {"address": "10.0.1.2:8080", "healthy": true, "connections": 42},
        {"address": "10.0.1.3:8080", "healthy": false, "connections": 0}
      ]
    }
  }
}
```

## Next Steps

- [Limits](../limits/) - Request limits and performance tuning
- [Routes](../routes/) - Routing to upstreams
