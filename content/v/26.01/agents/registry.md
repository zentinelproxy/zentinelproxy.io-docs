+++
title = "Agent Registry"
weight = 1
+++

Sentinel has a growing ecosystem of agents for security, traffic management, and custom logic. This page catalogs official agents maintained by the Sentinel team and community-contributed agents.

> **Browse the full registry at [sentinel.raskell.io/agents](https://sentinel.raskell.io/agents/)**

## Official Agents

Official agents are maintained by the Sentinel Core Team and follow strict quality, security, and compatibility standards.

### Stable

Production-ready agents with stable APIs.

| Agent | Version | Description | Events |
|-------|---------|-------------|--------|
| **Auth** | v0.1.0 | Authentication and authorization supporting JWT, API keys, OAuth, and custom providers | `request_headers` |
| **Denylist** | v0.1.0 | Block requests based on IP addresses, CIDR ranges, or custom patterns with real-time updates | `request_headers` |
| **Rate Limiter** | v0.1.0 | Token bucket rate limiting with configurable windows per route, IP, or custom keys | `request_headers` |

### Beta

Feature-complete but APIs may change.

| Agent | Version | Description | Events |
|-------|---------|-------------|--------|
| **AI Gateway** | v0.1.0 | LLM traffic control with prompt injection detection, PII filtering, and rate limiting | `request_headers`, `request_body` |
| **JS Scripting** | v0.1.0 | JavaScript-based custom logic using embedded V8 runtime | all |
| **Lua Scripting** | v0.1.0 | Embed custom Lua scripts for flexible request/response processing | all |
| **ModSecurity** | v0.1.0 | Full OWASP CRS support via libmodsecurity integration | `request_headers`, `request_body` |
| **WAF** | v0.1.0 | Native Rust web application firewall with SQL injection, XSS detection | `request_headers`, `request_body` |
| **WASM** | v0.1.0 | WebAssembly-based custom logic with sandboxed execution | `request_headers` |
| **WebSocket Inspector** | v0.1.0 | Deep inspection and filtering of WebSocket frames | `websocket_frame` |

### Planned

On the roadmap for future development.

| Agent | Description |
|-------|-------------|
| **Adaptive Shield** | Self-learning threat detection using edge ML |
| **Geo Filter** | Geographic IP-based request filtering |
| **LLM Guardian** | AI-powered threat analysis for intelligent traffic decisions |
| **Request Hold** | Pause suspicious requests for async verification |
| **Response Cache** | High-performance caching with TTL controls |
| **Telemetry** | Observability agent for analytics and logging |

## Built-in Reference Agents

The Sentinel repository includes reference implementations for testing and as templates:

### Echo Agent

A simple agent that echoes request metadata back as headers. Useful for testing and debugging.

```bash
# Run with Unix socket
sentinel-echo-agent --socket /tmp/echo.sock

# Run with gRPC
sentinel-echo-agent --grpc 0.0.0.0:50051
```

**Source:** [`agents/echo/`](https://github.com/raskell-io/sentinel/tree/main/agents/echo)

### Features

- Adds `X-Echo-*` headers with request metadata
- Returns correlation ID, method, path, client IP
- Supports verbose mode for additional debugging headers
- Works with both Unix socket and gRPC transports

## Community Agents

Community agents are created and maintained by the Sentinel community. They follow the agent protocol specification but are not officially supported.

> **No community agents registered yet.**
>
> Want to contribute? [Submit your agent](https://github.com/raskell-io/sentinel/issues/new?template=community-agent.md) to the registry!

### Submission Requirements

To submit a community agent:

1. Implement the [Agent Protocol](protocol/)
2. Include a `sentinel-agent.toml` manifest
3. Provide documentation and examples
4. Open an issue with the `community-agent` template

### Agent Manifest

Every agent should include a manifest file:

```toml
# sentinel-agent.toml
[agent]
name = "my-awesome-agent"
version = "0.1.0"
description = "Does awesome things with requests"
authors = ["Your Name <you@example.com>"]
license = "MIT OR Apache-2.0"
repository = "https://github.com/yourname/my-awesome-agent"

[protocol]
version = "1"
events = ["request_headers", "response_headers"]

[compatibility]
sentinel-proxy = ">=0.1.0"
sentinel-agent-protocol = "0.1"

[registry]
homepage = "https://example.com/my-agent"
documentation = "https://docs.example.com/my-agent"
keywords = ["sentinel", "agent", "awesome"]
categories = ["security"]  # security, traffic, observability, custom
```

## Agent Configuration

Configure agents in your `sentinel.kdl`:

```kdl
agents {
    // Official auth agent
    agent "auth" type="auth" {
        unix-socket "/var/run/sentinel/auth.sock"
        events "request_headers"
        timeout-ms 100
        failure-mode "closed"  // Block if agent fails
    }

    // Official WAF agent (gRPC)
    agent "waf" type="waf" {
        grpc "http://waf-service:50051"
        events "request_headers" "request_body"
        timeout-ms 200
        failure-mode "open"  // Allow if agent fails
        max-request-body-bytes 1048576  // 1MB
    }

    // Community or custom agent
    agent "custom-logic" type="custom" {
        grpc "http://localhost:50052"
        events "request_headers" "response_headers"
        timeout-ms 50
    }
}
```

## Agent Types

| Type | Description |
|------|-------------|
| `auth` | Authentication and authorization |
| `waf` | Web Application Firewall |
| `rate_limit` | Rate limiting and throttling |
| `custom` | Custom business logic |

The type is informational and used for metrics/logging. All agents use the same protocol.
