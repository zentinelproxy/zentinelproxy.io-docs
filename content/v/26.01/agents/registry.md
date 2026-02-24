+++
title = "Agent Registry"
weight = 1
updated = 2026-02-24
+++

Zentinel has a growing ecosystem of agents for security, traffic management, and custom logic. This page catalogs official agents maintained by the Zentinel team and community-contributed agents.

> **Browse the full registry at [zentinelproxy.io/agents](https://zentinelproxy.io/agents/)**

## Official Agents

Official agents are maintained by the Zentinel Core Team and follow strict quality, security, and compatibility standards. All bundled agents are distributed via `zentinel bundle install`.

### Core

| Agent | Version | Status | Description |
|-------|---------|--------|-------------|
| **WAF** | v0.3.0 | Stable | Pure Rust WAF with 285 detection rules, anomaly scoring, and API security |
| **Denylist** | v0.3.0 | Stable | Block requests based on IP addresses, CIDR ranges, or custom patterns with real-time updates |
| **Rate Limiter** | v0.3.0 | Deprecated | Token bucket rate limiting with configurable windows per route, IP, or custom keys |

### Security

| Agent | Version | Status | Description |
|-------|---------|--------|-------------|
| **ZentinelSec** | v0.3.0 | Stable | Pure Rust ModSecurity-compatible WAF with full OWASP CRS support — no C dependencies |
| **ModSecurity** | v0.3.0 | Stable | Full OWASP Core Rule Set (CRS) support via libmodsecurity with 800+ detection rules |
| **IP Reputation** | v0.4.0 | Stable | IP threat intelligence with AbuseIPDB integration, file-based blocklists, and Tor exit node detection |
| **Bot Management** | v0.4.0 | Stable | Comprehensive bot detection with multi-signal analysis, known bot verification, and behavioral tracking |
| **Content Scanner** | v0.4.0 | Stable | Malware scanning agent using ClamAV daemon for file upload protection |

### API Security

| Agent | Version | Status | Description |
|-------|---------|--------|-------------|
| **GraphQL Security** | v0.4.0 | Stable | Query depth limiting, complexity analysis, introspection control, and field-level authorization |
| **gRPC Inspector** | v0.4.0 | Stable | Method authorization, rate limiting, metadata inspection, and reflection control for gRPC services |
| **SOAP** | v0.4.0 | Stable | Envelope validation, WS-Security verification, operation control, and XXE prevention |
| **API Deprecation** | v0.4.0 | Stable | API lifecycle management with RFC 8594 Sunset headers, usage tracking, and automatic redirects |

### Protocol

| Agent | Version | Status | Description |
|-------|---------|--------|-------------|
| **WebSocket Inspector** | v0.4.0 | Stable | Content filtering, schema validation, and attack detection for WebSocket frames |
| **MQTT Gateway** | v0.4.0 | Stable | IoT protocol security with topic-based ACLs, client authentication, payload inspection, and QoS enforcement |

### Scripting

| Agent | Version | Status | Description |
|-------|---------|--------|-------------|
| **Lua** | v0.3.0 | Stable | Embed custom Lua scripts for flexible request/response processing |
| **JS** | v0.3.0 | Stable | JavaScript-based custom logic using the QuickJS engine |
| **WASM** | v0.3.0 | Stable | Execute custom Wasm modules for high-performance request/response processing in any language |

### Utility

| Agent | Version | Status | Description |
|-------|---------|--------|-------------|
| **Transform** | v0.4.0 | Stable | URL rewriting, header manipulation, and JSON body transforms |
| **Audit Logger** | v0.4.0 | Stable | Structured audit logging with PII redaction, multiple formats (JSON, CEF, LEEF), and compliance templates |
| **Mock Server** | v0.4.0 | Stable | Configurable stub responses with templating, latency simulation, and fault injection |
| **Chaos** | v0.4.0 | Stable | Controlled fault injection for resilience testing with flexible targeting and safety controls |
| **Image Optimization** | v0.1.0 | Stable | On-the-fly JPEG/PNG to WebP/AVIF conversion with content negotiation and filesystem caching |

### Identity

| Agent | Version | Status | Description |
|-------|---------|--------|-------------|
| **SPIFFE** | v0.3.0 | Stable | SPIFFE/SPIRE workload identity authentication for zero-trust service-to-service communication |

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

The Zentinel repository includes reference implementations for testing and as templates:

### Echo Agent

A simple agent that echoes request metadata back as headers. Useful for testing and debugging.

```bash
# Run with Unix socket
zentinel-echo-agent --socket /tmp/echo.sock

# Run with gRPC
zentinel-echo-agent --grpc 0.0.0.0:50051
```

**Source:** [`agents/echo/`](https://github.com/zentinelproxy/zentinel/tree/main/agents/echo)

### Features

- Adds `X-Echo-*` headers with request metadata
- Returns correlation ID, method, path, client IP
- Supports verbose mode for additional debugging headers
- Works with both Unix socket and gRPC transports

## Community Agents

Community agents are created and maintained by the Zentinel community. They follow the agent protocol specification but are not officially supported.

> **No community agents registered yet.**
>
> Want to contribute? [Submit your agent](https://github.com/zentinelproxy/zentinel/issues/new?template=community-agent.md) to the registry!

### Submission Requirements

To submit a community agent:

1. Implement the [Agent Protocol](protocol/)
2. Include a `zentinel-agent.toml` manifest
3. Provide documentation and examples
4. Open an issue with the `community-agent` template

### Agent Manifest

Every agent should include a manifest file:

```toml
# zentinel-agent.toml
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
zentinel-proxy = ">=0.1.0"
zentinel-agent-protocol = "0.1"

[registry]
homepage = "https://example.com/my-agent"
documentation = "https://docs.example.com/my-agent"
keywords = ["zentinel", "agent", "awesome"]
categories = ["security"]  # security, traffic, observability, custom
```

## Agent Configuration

Configure agents in your `zentinel.kdl`:

```kdl
agents {
    // Official auth agent
    agent "auth" type="auth" {
        unix-socket "/var/run/zentinel/auth.sock"
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
