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
| `weighted_least_conn` | Weighted least connections (connection/weight ratio) |
| `random` | Random target selection |
| `ip_hash` | Consistent routing based on client IP |
| `weighted` | Weighted random selection |
| `consistent_hash` | Consistent hashing for cache-friendly routing |
| `maglev` | Google's Maglev consistent hashing (minimal disruption) |
| `power_of_two_choices` | Pick best of two random targets |
| `adaptive` | Dynamic selection based on response times |
| `peak_ewma` | Latency-based selection using exponential moving average |
| `locality_aware` | Zone-aware routing with fallback strategies |
| `deterministic_subset` | Subset of backends per proxy (large clusters) |
| `least_tokens_queued` | Token-based selection for LLM workloads |

### Round Robin

```kdl
upstream "backend" {
    load-balancing "round_robin"
}
```

Simple sequential rotation. Good for homogeneous backends.

### Weighted

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
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        targets {
            target { address "10.0.1.1:8080" weight=3 }
            target { address "10.0.1.2:8080" weight=2 }
            target { address "10.0.1.3:8080" weight=1 }
        }
        load-balancing "weighted"
    }
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

Dynamically adjusts routing based on observed response times and error rates. The adaptive balancer continuously learns from request outcomes and automatically routes traffic away from slow or failing backends.

#### How It Works

1. **Weight Adjustment**: Each target starts with its configured weight. The balancer adjusts effective weights based on performance:
   - Targets with high error rates have their weights reduced
   - Targets with high latency have their weights reduced
   - Healthy, fast targets recover their weights over time

2. **EWMA Smoothing**: Error rates and latencies use Exponentially Weighted Moving Averages to smooth out transient spikes and focus on sustained trends.

3. **Circuit Breaker Integration**: Targets with consecutive failures are temporarily removed from rotation, then gradually reintroduced.

4. **Latency Feedback**: Every request reports its latency back to the balancer, enabling real-time performance awareness.

#### Selection Algorithm

For each request, the adaptive balancer:
1. Calculates a score for each healthy target: `score = weight / (1 + connections + error_penalty + latency_penalty)`
2. Uses weighted random selection based on scores
3. Targets with better performance get proportionally more traffic

#### Default Thresholds

| Parameter | Default | Description |
|-----------|---------|-------------|
| Error threshold | 5% | Error rate that triggers weight penalty |
| Latency threshold | 500ms | p99 latency that triggers penalty |
| Min weight ratio | 10% | Minimum weight (fraction of original) |
| Max weight ratio | 200% | Maximum weight (fraction of original) |
| Adjustment interval | 10s | How often weights are recalculated |
| Min requests | 100 | Minimum requests before adjusting |

#### When to Use Adaptive

**Best for:**
- Heterogeneous backends with varying performance
- Services with unpredictable load patterns
- Environments where backend health fluctuates
- Gradual degradation scenarios

**Consider alternatives when:**
- All backends have identical performance (use `round_robin`)
- Session affinity is required (use `ip_hash` or `consistent_hash`)
- You need deterministic routing (use `weighted`)

#### Example: API with Variable Backend Performance

```kdl
upstream "api" {
    targets {
        target { address "api-1.internal:8080" weight=100 }
        target { address "api-2.internal:8080" weight=100 }
        target { address "api-3.internal:8080" weight=100 }
    }
    load-balancing "adaptive"
    health-check {
        type "http" {
            path "/health"
            expected-status 200
        }
        interval-secs 5
        unhealthy-threshold 3
    }
}
```

If `api-2` starts responding slowly, traffic automatically shifts to `api-1` and `api-3`. When `api-2` recovers, it gradually receives more traffic again.

### Maglev

```kdl
upstream "cache-cluster" {
    load-balancing "maglev"
}
```

Google's Maglev consistent hashing algorithm provides O(1) lookup with minimal disruption when backends are added or removed. Uses a permutation-based lookup table for fast, consistent routing.

#### How It Works

1. **Lookup Table**: Builds a 65,537-entry lookup table mapping hash values to backends
2. **Permutation Sequences**: Each backend generates a unique permutation for table population
3. **Minimal Disruption**: When backends change, only ~1/N keys are remapped (N = number of backends)
4. **Hash Key Sources**: Can hash on client IP, header value, cookie, or request path

#### When to Use Maglev

**Best for:**
- Large cache clusters requiring consistent routing
- Services where session affinity matters
- Minimizing cache invalidation during scaling
- High-throughput systems needing O(1) selection

**Comparison with `consistent_hash`:**
- Maglev: Better load distribution, O(1) lookup, more memory
- Consistent Hash: Ring-based, O(log N) lookup, less memory

### Peak EWMA

```kdl
upstream "api" {
    load-balancing "peak_ewma"
}
```

Twitter Finagle's Peak EWMA (Exponentially Weighted Moving Average) algorithm tracks latency and selects backends with the lowest predicted completion time.

#### How It Works

1. **EWMA Tracking**: Maintains exponentially weighted moving average of each backend's latency
2. **Peak Detection**: Uses the maximum of EWMA and recent latency to quickly detect spikes
3. **Load Penalty**: Penalizes backends with active connections
4. **Decay Time**: Old latency observations decay over time (default: 10 seconds)

#### Selection Algorithm

For each request, Peak EWMA:
1. Calculates `load_score = peak_latency × (1 + active_connections × penalty)`
2. Selects the backend with the lowest load score
3. Reports actual latency after request completes

#### When to Use Peak EWMA

**Best for:**
- Heterogeneous backends with varying performance
- Latency-sensitive applications
- Backends with unpredictable response times
- Services where slow backends should be avoided

**Consider alternatives when:**
- All backends have identical performance (use `round_robin`)
- Session affinity is required (use `maglev` or `consistent_hash`)

### Locality-Aware

```kdl
upstream "global-api" {
    load-balancing "locality_aware"
}
```

Prefers targets in the same zone or region as the proxy, falling back to other zones when local targets are unavailable.

#### Zone Configuration

Zones can be specified in target metadata or parsed from addresses:

```kdl
targets {
    target {
        address "10.0.1.1:8080"
        metadata { "zone" "us-east-1a" }
    }
    target {
        address "10.0.1.2:8080"
        metadata { "zone" "us-east-1b" }
    }
    target {
        address "10.0.2.1:8080"
        metadata { "zone" "us-west-2a" }
    }
}
```

#### Fallback Strategies

When no local targets are healthy:

| Strategy | Behavior |
|----------|----------|
| `round_robin` | Round-robin across all healthy targets (default) |
| `random` | Random selection from all healthy targets |
| `fail_local` | Return error if no local targets available |

#### When to Use Locality-Aware

**Best for:**
- Multi-region deployments
- Minimizing cross-zone latency
- Reducing data transfer costs
- Geographic data residency requirements

### Deterministic Subsetting

```kdl
upstream "large-cluster" {
    load-balancing "deterministic_subset"
}
```

For very large clusters (1000+ backends), limits each proxy instance to a deterministic subset of backends, reducing connection overhead while ensuring even distribution.

#### How It Works

1. **Subset Selection**: Each proxy uses a consistent hash to select its subset
2. **Deterministic**: Same proxy ID always selects the same subset
3. **Even Distribution**: Across all proxies, each backend receives roughly equal traffic
4. **Subset Size**: Default 10 backends per proxy (configurable)

#### When to Use Deterministic Subsetting

**Best for:**
- Very large backend pools (1000+ targets)
- Reducing connection overhead
- Limiting memory usage per proxy
- Services where full-mesh connectivity is impractical

**Trade-offs:**
- Each proxy only sees a subset of backends
- Subset changes when proxy restarts with different ID
- Less effective with small backend pools

### Weighted Least Connections

```kdl
upstream "mixed-capacity" {
    load-balancing "weighted_least_conn"
}
```

Combines weight with connection counting. Selects the backend with the lowest ratio of active connections to weight.

#### Selection Algorithm

```
score = active_connections / weight
```

A backend with weight 200 and 10 connections (score: 0.05) is preferred over a backend with weight 100 and 6 connections (score: 0.06).

#### Example: Mixed Capacity Backends

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
    route "default" {
        matches { path-prefix "/" }
        upstream "mixed-capacity"
    }
}

upstreams {
    // Large server can handle 2x traffic, medium is standard, small is half capacity
    upstream "mixed-capacity" {
        targets {
            target { address "large-server:8080" weight=200 }
            target { address "medium-server:8080" weight=100 }
            target { address "small-server:8080" weight=50 }
        }
        load-balancing "weighted_least_conn"
    }
}
```

#### When to Use Weighted Least Connections

**Best for:**
- Heterogeneous backend capacities
- Mixed old/new hardware
- Gradual capacity scaling
- Long-running requests with varying backend power

**Comparison with `least_connections`:**
- `least_connections`: Ignores weight, pure connection count
- `weighted_least_conn`: Accounts for backend capacity via weight

### Least Tokens Queued

```kdl
upstream "llm-backend" {
    load-balancing "least_tokens_queued"
}
```

Specialized algorithm for LLM/inference workloads. Selects the backend with the fewest estimated tokens currently being processed.

#### How It Works

1. **Token Estimation**: Parses request body to estimate input tokens
2. **Queue Tracking**: Tracks estimated tokens queued per backend
3. **Selection**: Routes to backend with lowest token queue
4. **Completion Tracking**: Updates queue when requests complete

#### When to Use Least Tokens Queued

**Best for:**
- LLM inference backends (OpenAI-compatible APIs)
- Services where request cost varies by input size
- GPU-bound workloads with token-based processing
- Balancing across heterogeneous inference hardware

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
            service "my.service.Name"
        }
        interval-secs 10
        timeout-secs 5
    }
}
```

Uses the standard [gRPC Health Checking Protocol](https://grpc.io/docs/guides/health-checking/) (`grpc.health.v1.Health`).

#### Service Name

The `service` field specifies which service to check:
- **Empty string `""`**: Checks overall server health
- **Service name**: Checks health of a specific service (e.g., `"my.package.MyService"`)

```kdl
// Check overall server health
type "grpc" {
    service ""
}

// Check specific service
type "grpc" {
    service "myapp.UserService"
}
```

#### Response Handling

| Status | Result |
|--------|--------|
| `SERVING` | Healthy |
| `NOT_SERVING` | Unhealthy |
| `UNKNOWN` | Unhealthy |
| `SERVICE_UNKNOWN` | Unhealthy |
| Connection failure | Unhealthy |

#### Example: gRPC Microservices

```kdl
upstream "user-service" {
    targets {
        target { address "user-svc-1.internal:50051" }
        target { address "user-svc-2.internal:50051" }
    }
    load-balancing "least_connections"
    health-check {
        type "grpc" {
            service "user.UserService"
        }
        interval-secs 5
        timeout-secs 3
        healthy-threshold 2
        unhealthy-threshold 2
    }
}
```

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
        client-cert "/etc/zentinel/certs/client.crt"
        client-key "/etc/zentinel/certs/client.key"
        ca-cert "/etc/zentinel/certs/backend-ca.crt"
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
            client-cert "/etc/zentinel/certs/zentinel-client.crt"
            client-key "/etc/zentinel/certs/zentinel-client.key"
            ca-cert "/etc/zentinel/certs/internal-ca.crt"
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

## Service Discovery

Instead of static targets, upstreams can discover backends dynamically from external sources.

### DNS Discovery

```kdl
upstream "api" {
    discovery "dns" {
        hostname "api.internal.example.com"
        port 8080
        refresh-interval 30
    }
}
```

Resolves A/AAAA records and uses all IPs as targets.

| Option | Default | Description |
|--------|---------|-------------|
| `hostname` | Required | DNS name to resolve |
| `port` | Required | Port for all discovered backends |
| `refresh-interval` | `30` | Seconds between DNS lookups |

### Consul Discovery

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
    route "default" {
        matches { path-prefix "/" }
        upstream "backend"
    }
}

upstreams {
    upstream "backend" {
        discovery "consul" {
            address "http://consul.internal:8500"
            service "backend-api"
            datacenter "dc1"
            only-passing #true
            refresh-interval 10
            tag "production"
        }
    }
}

```

Discovers backends from Consul's service catalog.

| Option | Default | Description |
|--------|---------|-------------|
| `address` | Required | Consul HTTP API address |
| `service` | Required | Service name in Consul |
| `datacenter` | None | Consul datacenter |
| `only-passing` | `true` | Only return healthy services |
| `refresh-interval` | `10` | Seconds between queries |
| `tag` | None | Filter by service tag |

### Kubernetes Discovery

Discover backends from Kubernetes Endpoints. Supports both in-cluster and kubeconfig authentication.

#### In-Cluster Configuration

When running inside Kubernetes, Zentinel automatically uses the pod's service account:

```kdl
upstream "k8s-backend" {
    discovery "kubernetes" {
        namespace "production"
        service "api-server"
        port-name "http"
        refresh-interval 10
    }
}
```

#### Kubeconfig File

For running outside the cluster or with custom credentials:

```kdl
upstream "k8s-backend" {
    discovery "kubernetes" {
        namespace "default"
        service "my-service"
        port-name "http"
        refresh-interval 10
        kubeconfig "~/.kube/config"
    }
}
```

| Option | Default | Description |
|--------|---------|-------------|
| `namespace` | Required | Kubernetes namespace |
| `service` | Required | Service name |
| `port-name` | None | Named port to use (uses first port if omitted) |
| `refresh-interval` | `10` | Seconds between endpoint queries |
| `kubeconfig` | None | Path to kubeconfig file (uses in-cluster if omitted) |

#### Kubeconfig Authentication Methods

Zentinel supports multiple authentication methods from kubeconfig:

**Token Authentication:**
```yaml
users:
- name: my-user
  user:
    token: eyJhbGciOiJSUzI1NiIs...
```

**Client Certificate:**
```yaml
users:
- name: my-user
  user:
    client-certificate-data: LS0tLS1C...
    client-key-data: LS0tLS1C...
```

**Exec-based (e.g., AWS EKS):**
```yaml
users:
- name: eks-user
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: aws
      args:
        - eks
        - get-token
        - --cluster-name
        - my-cluster
```

#### Feature Flag

Kubernetes discovery with kubeconfig requires the `kubernetes` feature:

```bash
cargo build --features kubernetes
```

### File-based Discovery

Discover backends from a simple text file. The file is watched for changes and backends are reloaded automatically.

```kdl
upstream "api" {
    discovery "file" {
        path "/etc/zentinel/backends/api-servers.txt"
        watch-interval 5
    }
}
```

| Option | Default | Description |
|--------|---------|-------------|
| `path` | Required | Path to the backends file |
| `watch-interval` | `5` | Seconds between file modification checks |

#### File Format

One backend per line with optional weight parameter:

```text
# Backend servers for API cluster
# Updated: 2026-01-11

10.0.1.1:8080
10.0.1.2:8080 weight=2
10.0.1.3:8080 weight=3

# Standby server (lower weight)
10.0.1.4:8080 weight=1
```

**Format rules:**
- Lines starting with `#` are comments
- Empty lines are ignored
- Format: `host:port` or `host:port weight=N`
- Hostnames are resolved via DNS
- Default weight is `1` if not specified

#### Use Cases

**External configuration management:**
```kdl
// Backends managed by Ansible/Puppet/Chef
upstream "backend" {
    discovery "file" {
        path "/etc/zentinel/backends/managed-by-ansible.txt"
        watch-interval 10
    }
}
```

**Integration with custom scripts:**
```bash
#!/bin/bash
# update-backends.sh - Run by cron or external system
consul catalog nodes -service=api | \
    awk '{print $2":8080"}' > /etc/zentinel/backends/api.txt
```

```kdl
upstream "api" {
    discovery "file" {
        path "/etc/zentinel/backends/api.txt"
        watch-interval 5
    }
}
```

**Manual failover control:**
```text
# Primary datacenter
10.0.1.1:8080 weight=10
10.0.1.2:8080 weight=10

# DR datacenter (uncomment during failover)
# 10.0.2.1:8080 weight=10
# 10.0.2.2:8080 weight=10
```

#### Hot Reload Behavior

File-based discovery automatically detects changes:

1. **Modification check**: File modification time is checked every `watch-interval` seconds
2. **Reload trigger**: When file is modified, backends are re-read
3. **Graceful update**: New backends are added, removed backends drain connections
4. **Cache fallback**: If file becomes temporarily unavailable, last known backends are used

#### File Permissions

Ensure Zentinel can read the backends file:

```bash
# Create directory
sudo mkdir -p /etc/zentinel/backends
sudo chown zentinel:zentinel /etc/zentinel/backends

# Create backends file
echo "10.0.1.1:8080" | sudo tee /etc/zentinel/backends/api.txt
sudo chmod 644 /etc/zentinel/backends/api.txt
```

### Static Discovery

Explicitly define backends (default behavior when `targets` is used):

```kdl
upstream "backend" {
    discovery "static" {
        backends "10.0.1.1:8080" "10.0.1.2:8080" "10.0.1.3:8080"
    }
}
```

### Discovery with Health Checks

Discovery works with health checks. Unhealthy discovered backends are temporarily removed:

```kdl
upstream "api" {
    discovery "dns" {
        hostname "api.example.com"
        port 8080
        refresh-interval 30
    }
    health-check {
        type "http" {
            path "/health"
            expected-status 200
        }
        interval-secs 10
        unhealthy-threshold 3
    }
}
```

### Discovery Caching

All discovery methods cache results and fall back to cached backends on failure:

- DNS resolution fails → use last known IPs
- Consul unavailable → use last known services
- Kubernetes API error → use last known endpoints
- File unreadable → use last known backends

This ensures resilience during control plane outages.

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
