+++
title = "Agents"
weight = 8
sort_by = "weight"
template = "section.html"
+++

Agents are the primary extension mechanism for Zentinel. They allow you to add custom logic, security policies, and integrations without modifying the core proxy.

## Protocol

Zentinel uses the **v2 agent protocol** for all agent communication:

| Feature | Details |
|---------|---------|
| **Transports** | UDS (binary), gRPC, Reverse Connections |
| **Connection Pooling** | Multiple connections per agent with load balancing (4 strategies) |
| **Streaming** | Full bidirectional streaming support |
| **Observability** | Built-in metrics export in Prometheus format |
| **Config Push** | Dynamic configuration updates |
| **Health Tracking** | Comprehensive health checks |
| **Flow Control** | Backpressure support |
| **Request Cancellation** | Cancel in-flight requests when clients disconnect |

See the [v2 protocol documentation](v2/) for full details.

---

## What Are Agents?

Agents are **external processes** that communicate with Zentinel over a well-defined protocol. When a request flows through Zentinel, configured agents receive events at key lifecycle points and can:

- **Inspect** request/response headers and bodies
- **Modify** headers, routing metadata, and more
- **Decide** to allow, block, redirect, or challenge requests
- **Log** audit information for observability

```
┌───────────────────────────────────────────────────────────────────────────┐
│                             Zentinel Proxy                                 │
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

Zentinel's architecture keeps the dataplane minimal and predictable:

| Benefit | Description |
|---------|-------------|
| **Isolation** | A buggy or crashing agent cannot take down the proxy |
| **Independent Deployment** | Update agents without restarting Zentinel |
| **Language Flexibility** | Write agents in any language with gRPC or Unix socket support |
| **Circuit Breakers** | Zentinel protects itself from slow or failing agents |
| **Horizontal Scaling** | Run agents as separate services for high availability |

## Transport Options

Agents can communicate with Zentinel via multiple transports:

| Transport | Protocol | Best For |
|-----------|----------|----------|
| **Unix Socket** | Binary + JSON | Local agents, lowest latency |
| **gRPC** | Protocol Buffers over HTTP/2 | High throughput, streaming, remote |
| **Reverse Connection** | Binary | NAT traversal, dynamic scaling |

## Quick Configuration Example

```kdl
agents {
    // Unix socket agent with pooling
    agent "auth-agent" type="auth" {
        unix-socket "/var/run/zentinel/auth.sock"
        connections 4
        events "request_headers"
        timeout-ms 100
        failure-mode "closed"
    }

    // gRPC agent
    agent "waf-agent" type="waf" {
        grpc "http://localhost:50051"
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

// Reverse connection listener
reverse-listener {
    path "/var/run/zentinel/agents.sock"
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

The easiest way to build a custom agent is with the **Zentinel Agent SDK**:

```rust
use zentinel_agent_protocol::v2::{AgentPool, AgentPoolConfig};

let pool = AgentPool::new();
pool.add_agent("my-agent", "/var/run/my-agent.sock").await?;

let response = pool.send_request_headers("my-agent", &headers).await?;
```

The SDK provides ergonomic wrappers around the protocol, handling connection management, health tracking, and metrics automatically.

## Documentation

### Protocol Reference

| Page | Description |
|------|-------------|
| [Protocol Specification](v2/protocol/) | Wire protocol, message types, streaming |
| [API Reference](v2/api/) | AgentPool, client, and server APIs |
| [Connection Pooling](v2/pooling/) | Load balancing and circuit breakers |
| [Transport Options](v2/transports/) | gRPC, UDS, and Reverse comparison |
| [Reverse Connections](v2/reverse-connections/) | NAT traversal setup |

### Legacy (Removed)

| Page | Description |
|------|-------------|
| [Protocol v1](v1/) | Historical v1 documentation (removed in 26.02_18) |
