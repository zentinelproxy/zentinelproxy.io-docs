+++
title = "Agents"
weight = 8
sort_by = "weight"
template = "section.html"
+++

Agents are the primary extension mechanism for Sentinel. They allow you to add custom logic, security policies, and integrations without modifying the core proxy.

## Protocol Versions

Sentinel supports two protocol versions for agent communication:

| Version | Status | Recommendation |
|---------|--------|----------------|
| [**v2 (Current)**](v2/) | Recommended | Use for new deployments |
| [**v1 (Legacy)**](v1/) | Supported | Existing agents, simple use cases |

### v2 Features

Protocol v2 introduces significant enhancements:

- **Connection Pooling** - Multiple connections per agent with load balancing
- **Multiple Transports** - gRPC, Binary UDS, and Reverse Connections
- **Request Cancellation** - Cancel in-flight requests when clients disconnect
- **Reverse Connections** - Agents connect to proxy (NAT traversal)
- **Enhanced Observability** - Built-in metrics export in Prometheus format

### Version Comparison

| Feature | v1 | v2 |
|---------|----|----|
| Transport | UDS (JSON), gRPC | UDS (binary), gRPC, Reverse |
| Connection pooling | No | Yes (4 strategies) |
| Bidirectional streaming | Limited | Full support |
| Metrics export | No | Prometheus format |
| Config push | No | Yes |
| Health tracking | Basic | Comprehensive |
| Flow control | No | Yes |
| Request cancellation | No | Yes |

---

## What Are Agents?

Agents are **external processes** that communicate with Sentinel over a well-defined protocol. When a request flows through Sentinel, configured agents receive events at key lifecycle points and can:

- **Inspect** request/response headers and bodies
- **Modify** headers, routing metadata, and more
- **Decide** to allow, block, redirect, or challenge requests
- **Log** audit information for observability

```
┌───────────────────────────────────────────────────────────────────────────┐
│                             Sentinel Proxy                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                          Agent Manager                               │  │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐        │  │
│  │  │   Auth    │  │ RateLimit │  │    WAF    │  │  Policy   │        │  │
│  │  │  Client   │  │  Client   │  │  Client   │  │  Client   │        │  │
│  │  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘        │  │
│  └────────┼──────────────┼──────────────┼──────────────┼──────────────┘  │
└───────────┼──────────────┼──────────────┼──────────────┼─────────────────┘
            │              │              │              │
            ▼              ▼              ▼              ▼
     ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
     │ Auth Agent │ │ RateLimit  │ │ WAF Agent  │ │  Policy    │
     │  (local)   │ │   Agent    │ │  (remote)  │ │  Agent     │
     └────────────┘ └────────────┘ └────────────┘ └────────────┘
          UDS           gRPC           gRPC         Reverse
```

## Why External Agents?

Sentinel's architecture keeps the dataplane minimal and predictable:

| Benefit | Description |
|---------|-------------|
| **Isolation** | A buggy or crashing agent cannot take down the proxy |
| **Independent Deployment** | Update agents without restarting Sentinel |
| **Language Flexibility** | Write agents in any language with gRPC or Unix socket support |
| **Circuit Breakers** | Sentinel protects itself from slow or failing agents |
| **Horizontal Scaling** | Run agents as separate services for high availability |

## Transport Options

Agents can communicate with Sentinel via multiple transports:

| Transport | Protocol | Best For |
|-----------|----------|----------|
| **Unix Socket (v2)** | Binary + JSON | Local agents, lowest latency |
| **Unix Socket (v1)** | Length-prefixed JSON | Legacy agents |
| **gRPC** | Protocol Buffers over HTTP/2 | High throughput, streaming, remote |
| **Reverse Connection** | Binary (v2 only) | NAT traversal, dynamic scaling |

## Quick Configuration Example

```kdl
agents {
    // v2 Unix socket agent with pooling
    agent "auth-agent" type="auth" {
        unix-socket "/var/run/sentinel/auth.sock"
        protocol-version 2
        connections 4
        events "request_headers"
        timeout-ms 100
        failure-mode "closed"
    }

    // v2 gRPC agent
    agent "waf-agent" type="waf" {
        grpc "http://localhost:50051"
        protocol-version 2
        connections 4
        events "request_headers" "request_body"
        timeout-ms 200
        failure-mode "open"
        circuit-breaker {
            failure-threshold 5
            timeout-seconds 30
        }
    }
}

// v2 reverse connection listener
reverse-listener {
    path "/var/run/sentinel/agents.sock"
    max-connections-per-agent 4
    handshake-timeout "10s"
}

routes {
    route "api" {
        matches { path-prefix "/api/" }
        upstream "backend"
        agents "auth-agent" "waf-agent"
    }
}
```

## Building Your Own Agent

The easiest way to build a custom agent is with the **Sentinel Agent SDK**:

```rust
use sentinel_agent_protocol::v2::{AgentPool, AgentPoolConfig};

// v2 with connection pooling
let pool = AgentPool::new();
pool.add_agent("my-agent", "/var/run/my-agent.sock").await?;

let response = pool.send_request_headers("my-agent", &headers).await?;
```

The SDK provides ergonomic wrappers around the protocol, handling connection management, health tracking, and metrics automatically.

## Documentation

### Protocol v2 (Recommended)

| Page | Description |
|------|-------------|
| [Protocol Specification](v2/protocol/) | Wire protocol, message types, streaming |
| [API Reference](v2/api/) | AgentPool, client, and server APIs |
| [Connection Pooling](v2/pooling/) | Load balancing and circuit breakers |
| [Transport Options](v2/transports/) | gRPC, UDS, and Reverse comparison |
| [Reverse Connections](v2/reverse-connections/) | NAT traversal setup |
| [Migration Guide](v2/migration/) | Migrate from v1 to v2 |

### Protocol v1 (Legacy)

| Page | Description |
|------|-------------|
| [Protocol Specification](v1/protocol/) | Wire protocol and message formats |
| [Events & Hooks](v1/events/) | Request lifecycle events |
| [Building Agents](v1/building/) | How to create agents |
| [Transport Protocols](v1/transports/) | Unix sockets and gRPC |
| [Agent Registry](v1/registry/) | Official and community agents |
