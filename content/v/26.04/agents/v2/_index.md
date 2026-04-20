+++
title = "Protocol v2 (Current)"
weight = 10
sort_by = "weight"
+++

Agent Protocol v2 is the recommended protocol for new agent deployments. It provides enhanced features for production environments.

## Key Features

| Feature | Description |
|---------|-------------|
| **Connection Pooling** | Maintain multiple connections per agent with load balancing |
| **Multiple Transports** | gRPC, Binary UDS, and Reverse Connections |
| **Request Cancellation** | Cancel in-flight requests when clients disconnect |
| **Reverse Connections** | Agents connect to proxy (NAT traversal) |
| **Enhanced Observability** | Built-in metrics export in Prometheus format |
| **Config Push** | Push configuration updates to capable agents |

## Documentation

| Page | Description |
|------|-------------|
| [Protocol Specification](protocol/) | Wire protocol, message types, and streaming |
| [API Reference](api/) | AgentPool, client, and server APIs |
| [Connection Pooling](pooling/) | Load balancing and circuit breakers |
| [Transport Options](transports/) | gRPC, UDS, and Reverse comparison |
| [Reverse Connections](reverse-connections/) | NAT traversal and agent-initiated connections |
| [Performance Benchmarks](performance/) | Latency, throughput, and optimization results |
| [Migration Guide](migration/) | Historical v1 → v2 migration notes (v1 removed in 26.02_18) |

## Quick Start

```rust
use zentinel_agent_protocol::v2::{AgentPool, AgentPoolConfig, LoadBalanceStrategy};
use std::time::Duration;

let config = AgentPoolConfig {
    connections_per_agent: 4,
    load_balance_strategy: LoadBalanceStrategy::LeastConnections,
    request_timeout: Duration::from_secs(30),
    ..Default::default()
};

let pool = AgentPool::with_config(config);

// Add agents (transport auto-detected)
pool.add_agent("waf", "localhost:50051").await?;       // gRPC
pool.add_agent("auth", "/var/run/auth.sock").await?;   // UDS
```

## Features

| Feature | Details |
|---------|---------|
| Transport | UDS (binary), gRPC, Reverse Connections |
| Connection pooling | Yes (4 strategies) |
| Bidirectional streaming | Full support |
| Metrics export | Prometheus format |
| Config push | Yes |
| Health tracking | Comprehensive |
| Flow control | Yes |
| Request cancellation | Yes |
