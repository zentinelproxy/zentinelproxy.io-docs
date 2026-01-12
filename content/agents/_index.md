+++
title = "Agents"
weight = 8
sort_by = "weight"
template = "section.html"
+++

Agents are the primary extension mechanism for Sentinel. They allow you to add custom logic, security policies, and integrations without modifying the core proxy.

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
          UDS           gRPC           gRPC           HTTP
```

## Why External Agents?

Sentinel's architecture keeps the dataplane minimal and predictable:

| Benefit | Description |
|---------|-------------|
| **Isolation** | A buggy or crashing agent cannot take down the proxy |
| **Independent Deployment** | Update agents without restarting Sentinel |
| **Language Flexibility** | Write agents in any language with HTTP, gRPC, or Unix socket support |
| **Circuit Breakers** | Sentinel protects itself from slow or failing agents |
| **Horizontal Scaling** | Run agents as separate services for high availability |

## Transport Options

Agents can communicate with Sentinel via three transport mechanisms:

| Transport | Protocol | Best For |
|-----------|----------|----------|
| **Unix Socket** | Length-prefixed JSON | Local agents, lowest latency |
| **gRPC** | Protocol Buffers over HTTP/2 | High throughput, streaming, binary data |
| **HTTP** | JSON over HTTP/1.1 or HTTP/2 | Simplicity, any language, easy debugging |

## Request Lifecycle

```
Request arrives
     │
     ▼
┌────────────────────┐
│ Route Matching     │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐     ┌─────────────────┐
│ REQUEST_HEADERS    │────▶│ Agent Decision  │──▶ BLOCK/REDIRECT?
└────────┬───────────┘     └─────────────────┘
         │ ALLOW
         ▼
┌────────────────────┐     ┌─────────────────┐
│ REQUEST_BODY       │────▶│ Agent Inspection│──▶ BLOCK?
│ (if configured)    │     └─────────────────┘
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Forward to Upstream│
└────────┬───────────┘
         │
         ▼
┌────────────────────┐     ┌─────────────────┐
│ RESPONSE_HEADERS   │────▶│ Agent Mutation  │
│ (optional)         │     └─────────────────┘
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Send Response      │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐     ┌─────────────────┐
│ REQUEST_COMPLETE   │────▶│ Agent Logging   │
│ (audit/log)        │     └─────────────────┘
└────────────────────┘
```

## Quick Configuration Example

```kdl
agents {
    // Unix socket agent (local, lowest latency)
    agent "auth-agent" type="auth" {
        unix-socket "/var/run/sentinel/auth.sock"
        events "request_headers"
        timeout-ms 100
        failure-mode "closed"
    }

    // gRPC agent (high throughput, streaming)
    agent "waf-agent" type="waf" {
        grpc "http://localhost:50051"
        events "request_headers" "request_body"
        timeout-ms 200
        failure-mode "open"
        circuit-breaker {
            failure-threshold 5
            timeout-seconds 30
        }
    }

    // HTTP agent (simple, any language)
    agent "policy-agent" type="custom" {
        http "http://localhost:8080/agent"
        events "request_headers"
        timeout-ms 150
        failure-mode "open"
    }
}

routes {
    route "api" {
        matches { path-prefix "/api/" }
        upstream "backend"
        agents "auth-agent" "waf-agent" "policy-agent"
    }
}
```

## Building Your Own Agent

The easiest way to build a custom agent is with the **Sentinel Agent SDK**:

```rust
use sentinel_agent_sdk::prelude::*;

struct MyAgent;

#[async_trait]
impl Agent for MyAgent {
    async fn on_request(&self, request: &Request) -> Decision {
        if request.path_starts_with("/admin") {
            Decision::deny().with_body("Forbidden")
        } else {
            Decision::allow()
        }
    }
}
```

The SDK provides ergonomic wrappers around the protocol, handling connection management, CLI parsing, and logging automatically.

## Documentation

| Page | Description |
|------|-------------|
| [Agent Registry](registry/) | Official and community agents |
| [Events & Hooks](events/) | Request lifecycle events agents can handle |
| [Building Agents](building/) | How to create your own agent (SDK and low-level) |
| [Transport Protocols](transports/) | Unix sockets and gRPC connectivity |
| [Protocol Specification](protocol/) | Wire protocol and message formats |
