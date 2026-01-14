+++
title = "Connection Pooling"
weight = 3
+++

This document covers the AgentPool connection pooling system, including load balancing strategies, health tracking, and circuit breakers.

## Overview

The `AgentPool` maintains multiple connections per agent for:

- **Higher throughput**: Parallel request processing
- **Lower latency**: Reduced connection overhead
- **Better reliability**: Automatic failover between connections
- **Smart routing**: Load-balanced request distribution

```
┌─────────────────────────────────────────────────────────────┐
│                        AgentPool                            │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   Agent: waf    │  │  Agent: auth    │                  │
│  │                 │  │                 │                  │
│  │  ┌───────────┐  │  │  ┌───────────┐  │                  │
│  │  │ Conn 1    │  │  │  │ Conn 1    │  │                  │
│  │  │ (gRPC)    │  │  │  │ (UDS)     │  │                  │
│  │  ├───────────┤  │  │  ├───────────┤  │                  │
│  │  │ Conn 2    │  │  │  │ Conn 2    │  │                  │
│  │  ├───────────┤  │  │  ├───────────┤  │                  │
│  │  │ Conn 3    │  │  │  │ Conn 3    │  │                  │
│  │  ├───────────┤  │  │  ├───────────┤  │                  │
│  │  │ Conn 4    │  │  │  │ Conn 4    │  │                  │
│  │  └───────────┘  │  │  └───────────┘  │                  │
│  │                 │  │                 │                  │
│  │  Health: OK     │  │  Health: OK     │                  │
│  │  In-flight: 12  │  │  In-flight: 8   │                  │
│  └─────────────────┘  └─────────────────┘                  │
│                                                             │
│  Load Balancer: LeastConnections                           │
│  Circuit Breaker: Enabled                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration

### Basic Setup

```rust
use sentinel_agent_protocol::v2::{AgentPool, AgentPoolConfig, LoadBalanceStrategy};
use std::time::Duration;

let config = AgentPoolConfig {
    connections_per_agent: 4,
    load_balance_strategy: LoadBalanceStrategy::LeastConnections,
    request_timeout: Duration::from_secs(30),
    connect_timeout: Duration::from_secs(5),
    health_check_interval: Duration::from_secs(10),
    circuit_breaker_threshold: 5,
    circuit_breaker_reset_timeout: Duration::from_secs(30),
};

let pool = AgentPool::with_config(config);
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `connections_per_agent` | 4 | Number of connections maintained per agent |
| `load_balance_strategy` | LeastConnections | How requests are distributed |
| `request_timeout` | 30s | Timeout for individual requests |
| `connect_timeout` | 5s | Timeout for establishing connections |
| `health_check_interval` | 10s | Interval between health checks |
| `circuit_breaker_threshold` | 5 | Failures before opening circuit |
| `circuit_breaker_reset_timeout` | 30s | Time before circuit resets |

---

## Load Balancing Strategies

### RoundRobin

Distributes requests evenly across all connections in rotation.

```rust
let config = AgentPoolConfig {
    load_balance_strategy: LoadBalanceStrategy::RoundRobin,
    ..Default::default()
};
```

**Behavior**:
```
Request 1 → Connection 1
Request 2 → Connection 2
Request 3 → Connection 3
Request 4 → Connection 4
Request 5 → Connection 1  (wraps around)
```

**Best for**: Uniform request processing times, simple distribution.

### LeastConnections

Routes to the connection with the fewest in-flight requests.

```rust
let config = AgentPoolConfig {
    load_balance_strategy: LoadBalanceStrategy::LeastConnections,
    ..Default::default()
};
```

**Behavior**:
```
Connection 1: 3 in-flight
Connection 2: 1 in-flight  ← Next request goes here
Connection 3: 4 in-flight
Connection 4: 2 in-flight
```

**Best for**: Variable request processing times, optimal latency.

### HealthBased

Prefers healthier connections based on recent error rates.

```rust
let config = AgentPoolConfig {
    load_balance_strategy: LoadBalanceStrategy::HealthBased,
    ..Default::default()
};
```

**Behavior**:
```
Connection 1: Health 100%, Weight 1.0
Connection 2: Health 95%,  Weight 0.95
Connection 3: Health 80%,  Weight 0.80  (recent errors)
Connection 4: Health 100%, Weight 1.0

Weighted random selection favors healthy connections
```

**Best for**: Unreliable networks, degraded agent instances.

### Random

Random selection for simple distribution.

**Best for**: Testing, simple deployments.

---

## Health Tracking

### Connection Health

Each connection tracks:

- **Success rate**: Percentage of successful requests
- **Average latency**: Recent request latencies
- **Last error**: Most recent error and timestamp
- **State**: Healthy, Degraded, or Unhealthy

```rust
let health = pool.get_health("waf")?;

println!("Agent: {}", health.agent_name);
println!("Connections: {}", health.total_connections);
println!("Healthy: {}", health.healthy_connections);
println!("Success rate: {:.2}%", health.success_rate * 100.0);
println!("Avg latency: {:?}", health.average_latency);
```

### Health States

| State | Criteria | Behavior |
|-------|----------|----------|
| Healthy | Success rate > 95% | Normal routing |
| Degraded | Success rate 80-95% | Reduced weight in HealthBased |
| Unhealthy | Success rate < 80% | Minimal traffic, recovery checks |

---

## Circuit Breaker

### Overview

The circuit breaker prevents cascading failures by temporarily disabling unhealthy agents.

```
         ┌─────────┐
         │ Closed  │  Normal operation
         │ (Pass)  │
         └────┬────┘
              │ threshold failures
              ▼
         ┌─────────┐
         │  Open   │  Fail fast, no requests sent
         │ (Fail)  │
         └────┬────┘
              │ reset_timeout elapsed
              ▼
        ┌──────────┐
        │Half-Open │  Allow one test request
        │ (Test)   │
        └────┬─────┘
             │
    ┌────────┴────────┐
    │                 │
    ▼ success         ▼ failure
┌─────────┐      ┌─────────┐
│ Closed  │      │  Open   │
└─────────┘      └─────────┘
```

### States

| State | Behavior |
|-------|----------|
| **Closed** | Requests pass through normally |
| **Open** | Requests fail immediately with error |
| **Half-Open** | One request allowed to test recovery |

### Monitoring

```rust
let health = pool.get_health("waf")?;

match health.circuit_breaker_state {
    CircuitBreakerState::Closed => {
        // Normal operation
    }
    CircuitBreakerState::Open { opened_at } => {
        tracing::warn!("Circuit open since {:?}", opened_at);
    }
    CircuitBreakerState::HalfOpen => {
        tracing::info!("Circuit testing recovery");
    }
}
```

---

## Metrics

### Prometheus Export

```rust
let prometheus_output = pool.metrics_collector().export_prometheus();
```

Output:
```prometheus
# HELP agent_requests_total Total number of requests to agents
# TYPE agent_requests_total counter
agent_requests_total{agent="waf",decision="allow"} 15234
agent_requests_total{agent="waf",decision="block"} 423

# HELP agent_request_duration_seconds Request duration histogram
# TYPE agent_request_duration_seconds histogram
agent_request_duration_seconds_bucket{agent="waf",le="0.001"} 5234
agent_request_duration_seconds_bucket{agent="waf",le="0.005"} 12453

# HELP agent_connections_active Current number of active connections
# TYPE agent_connections_active gauge
agent_connections_active{agent="waf"} 4

# HELP agent_circuit_breaker_state Circuit breaker state (0=closed, 1=open)
# TYPE agent_circuit_breaker_state gauge
agent_circuit_breaker_state{agent="waf"} 0
```

---

## Best Practices

### 1. Size Your Pool Appropriately

```rust
// For high-throughput: more connections
let high_throughput = AgentPoolConfig {
    connections_per_agent: 8,
    ..Default::default()
};

// For low-latency: fewer connections, faster timeouts
let low_latency = AgentPoolConfig {
    connections_per_agent: 2,
    request_timeout: Duration::from_millis(100),
    ..Default::default()
};
```

### 2. Choose the Right Load Balancer

| Scenario | Recommended Strategy |
|----------|---------------------|
| Uniform workload | RoundRobin |
| Variable latency | LeastConnections |
| Unreliable agents | HealthBased |
| Testing | Random |

### 3. Graceful Shutdown

```rust
async fn shutdown(pool: &AgentPool) {
    // Cancel all in-flight requests
    for agent_name in pool.agent_names() {
        if let Err(e) = pool.cancel_all(&agent_name).await {
            tracing::error!("Failed to cancel requests for {}: {}", agent_name, e);
        }
    }

    // Wait for connections to drain
    tokio::time::sleep(Duration::from_secs(5)).await;
}
```

---

## Protocol Metrics

The `AgentPool` includes built-in protocol-level metrics for detailed monitoring.

### Accessing Metrics

```rust
// Get metrics instance
let metrics = pool.protocol_metrics();

// Get point-in-time snapshot
let snapshot = metrics.snapshot();

// Export to Prometheus format
let prometheus_text = metrics.to_prometheus("agent_protocol");
```

### Available Metrics

| Type | Metric | Description |
|------|--------|-------------|
| Counter | `requests_total` | Total requests sent |
| Counter | `responses_total` | Total responses received |
| Counter | `timeouts_total` | Requests that timed out |
| Counter | `connection_errors_total` | Connection failures |
| Counter | `flow_control_rejections_total` | Requests rejected due to flow control |
| Gauge | `in_flight_requests` | Current in-flight requests |
| Gauge | `healthy_connections` | Number of healthy connections |
| Gauge | `paused_connections` | Number of paused connections |
| Histogram | `serialization_time_us` | Serialization latency (μs) |
| Histogram | `request_duration_us` | End-to-end request latency (μs) |

### Prometheus Export

```rust
let prometheus = pool.protocol_metrics().to_prometheus("agent_protocol");
```

Output:
```prometheus
# HELP agent_protocol_requests_total Total requests sent
# TYPE agent_protocol_requests_total counter
agent_protocol_requests_total 12345

# HELP agent_protocol_request_duration_us Request duration histogram
# TYPE agent_protocol_request_duration_us histogram
agent_protocol_request_duration_us_bucket{le="100"} 5234
agent_protocol_request_duration_us_bucket{le="500"} 10453
agent_protocol_request_duration_us_bucket{le="+Inf"} 12345
```

---

## Connection Affinity

For streaming requests, body chunks should be routed to the same connection as the initial headers.

### Automatic Affinity

When `send_request_headers` is called, the pool stores the selected connection for the correlation_id:

```rust
// Headers sent to connection A
let response = pool.send_request_headers("waf", &headers).await?;

// Body chunks automatically routed to connection A
pool.send_request_body_chunk("waf", &chunk1).await?;
pool.send_request_body_chunk("waf", &chunk2).await?;
```

### Manual Cleanup

After a request completes, clear the affinity mapping:

```rust
// Clear affinity for a specific correlation_id
pool.clear_correlation_affinity("correlation-123");

// Check current affinity count
let count = pool.correlation_affinity_count();
```

---

## Performance Optimizations

The `AgentPool` is optimized for high-throughput, low-latency operation:

- **Lock-free agent lookup**: Uses `DashMap` for O(1) concurrent reads
- **Cached health state**: Atomic reads avoid async I/O in hot path
- **Synchronous connection selection**: No `.await` during selection
- **Atomic timestamp tracking**: `AtomicU64` instead of `RwLock<Instant>`

| Operation | Latency | Sync Points |
|-----------|---------|-------------|
| Agent lookup | ~100ns | 0 (lock-free) |
| Connection selection | ~1μs | 1 (try_read) |
| Health check (cached) | ~10ns | 0 (atomic) |

**Total hot-path sync points per request:** 2
