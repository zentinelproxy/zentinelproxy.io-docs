+++
title = "Architecture Overview"
weight = 1
+++

Sentinel is a security-first reverse proxy built on [Cloudflare's Pingora](https://github.com/cloudflare/pingora) framework. This page explains the high-level architecture and design philosophy.

## Design Philosophy

Sentinel follows four core principles:

### Sleepable Operations

No operational surprises at 3 AM:

- **Bounded resources** - Hard limits on memory, queues, connections
- **Deterministic timeouts** - Every operation has an explicit timeout
- **Graceful degradation** - Clear failure modes (fail-open/fail-closed)
- **Hot reload** - Configuration changes without restarts

### Security-First

Security decisions are explicit, not magical:

- **No hidden behavior** - All limits and policies are in configuration
- **Isolation by default** - Complex logic runs in external agents
- **Observable decisions** - Every security action is logged and traceable

### Minimal Dataplane

The proxy core stays boring and predictable:

- **Small surface area** - Core proxy does routing, load balancing, forwarding
- **Stable behavior** - No surprises under load or failure
- **Innovation at the edges** - Advanced features live in agents

### Production Correctness

Features ship only when they're production-ready:

- **Bounded and observable** - Every feature has limits and metrics
- **Testable** - Load tests, soak tests, regression gates
- **Rollback-safe** - Safe deployment and quick recovery

## High-Level Architecture

```
                                    ┌─────────────────────┐
                                    │   External Agents   │
                                    │  ┌───┐ ┌───┐ ┌───┐ │
                                    │  │WAF│ │Auth│ │...│ │
                                    │  └─┬─┘ └─┬─┘ └─┬─┘ │
                                    └────┼─────┼─────┼───┘
                                         │ UDS │     │
┌──────────┐     ┌──────────────────────┼─────┼─────┼────────────────┐
│          │     │                      │     │     │                │
│  Client  │────▶│   Sentinel Proxy     ▼     ▼     ▼                │
│          │     │  ┌─────────────────────────────────────────────┐  │
└──────────┘     │  │              Agent Manager                  │  │
                 │  └─────────────────────────────────────────────┘  │
                 │                        │                          │
                 │  ┌──────────┐    ┌─────┴─────┐    ┌────────────┐ │
                 │  │  Route   │───▶│  Request  │───▶│  Upstream  │ │
                 │  │ Matcher  │    │  Handler  │    │   Pool     │ │
                 │  └──────────┘    └───────────┘    └─────┬──────┘ │
                 │                                          │       │
                 └──────────────────────────────────────────┼───────┘
                                                            │
                                                            ▼
                                                   ┌────────────────┐
                                                   │    Upstream    │
                                                   │    Servers     │
                                                   └────────────────┘
```

## Core Components

### 1. Proxy Dataplane (Pingora)

The foundation is Cloudflare's Pingora library, providing:

- High-performance async HTTP handling
- Connection pooling to upstreams
- TLS termination
- HTTP/1.1 and HTTP/2 support
- Zero-copy buffer management

Sentinel extends Pingora with routing, load balancing, and agent coordination.

### 2. Route Matcher

Matches incoming requests to configured routes based on:

- Path (exact, prefix, regex)
- Host header
- HTTP method
- Request headers
- Query parameters

Routes are compiled at startup and cached for efficient matching.

### 3. Upstream Pool

Manages backend server connections:

- Multiple load balancing algorithms
- Active and passive health checking
- Circuit breakers for failure isolation
- Connection pooling and reuse

### 4. Agent Manager

Coordinates external agent processes:

- Connection pooling per agent
- Timeout enforcement
- Circuit breakers for agent failures
- Decision aggregation from multiple agents

### 5. Configuration System

Declarative configuration with:

- KDL format (human-friendly)
- Schema validation
- Hot reload without downtime
- Multi-file support

## Request Flow

```
1. Client Connection
   └─▶ Pingora accepts TCP connection
       └─▶ TLS handshake (if HTTPS)

2. Request Received
   └─▶ Parse HTTP request
       └─▶ Generate trace ID

3. Route Matching
   └─▶ Match against compiled routes
       └─▶ Select highest priority match

4. Agent Processing (if configured)
   └─▶ Send request to agents
       └─▶ Collect decisions (allow/block/redirect)
           └─▶ Apply header mutations

5. Request Handling
   ├─▶ Static: Serve file from disk
   ├─▶ Builtin: Health check, metrics
   └─▶ Proxy: Forward to upstream

6. Upstream Selection
   └─▶ Load balancer selects target
       └─▶ Health check filters unhealthy
           └─▶ Circuit breaker filters failing

7. Upstream Request
   └─▶ Connect to upstream (pooled)
       └─▶ Send request with modified headers
           └─▶ Retry on failure (if configured)

8. Response Processing
   └─▶ Add security headers
       └─▶ Agent response processing (optional)
           └─▶ Stream to client

9. Logging
   └─▶ Access log entry
       └─▶ Metrics update
           └─▶ Audit log (if security event)
```

## Extension Model

Sentinel's extension model keeps complexity out of the dataplane:

```
┌────────────────────────────────────────────────────────────────┐
│                        Dataplane (Rust)                        │
│  Fast, bounded, predictable. Handles 99% of requests quickly. │
└────────────────────────────────────────────────────────────────┘
                               │
                    Unix Domain Sockets
                          or gRPC
                               │
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│   WAF    │  │   Auth   │  │  Rate    │  │  Custom  │
│  Agent   │  │  Agent   │  │  Limit   │  │  Logic   │
│          │  │          │  │  Agent   │  │  Agent   │
│ (CRS)    │  │ (JWT)    │  │ (Redis)  │  │ (Lua)    │
└──────────┘  └──────────┘  └──────────┘  └──────────┘
     Any language, independent deployment, isolated failures
```

**Why external agents?**

| Concern | Dataplane | Agents |
|---------|-----------|--------|
| Crash isolation | Must not crash | Can crash safely |
| Deployment | Full restart | Independent update |
| Language | Rust only | Any language |
| Complexity | Minimal | Unlimited |
| Resources | Shared, bounded | Isolated |

## Failure Handling

### Circuit Breakers

Protect against cascading failures:

```
       Closed                    Open
    ┌─────────┐  failures    ┌─────────┐
    │ Normal  │─────────────▶│ Failing │
    │ traffic │  exceed      │ fast-   │
    └─────────┘  threshold   │ fail    │
         ▲                   └────┬────┘
         │                        │
         │    Half-Open           │ timeout
         │   ┌─────────┐          │
         └───│ Testing │◀─────────┘
             │ traffic │
             └─────────┘
```

### Failure Modes

Per-route configuration:

- **fail-closed** (default): Block request if agent fails
- **fail-open**: Allow request if agent fails

### Health Checking

- **Active**: Periodic HTTP/TCP probes
- **Passive**: Learn from real traffic failures
- **Recovery**: Gradual reintroduction after failures

## Observability

### Metrics (Prometheus)

- Request latency histograms (per route)
- Status code counters
- Upstream health status
- Agent latency and timeouts
- Circuit breaker state

### Logging (Structured JSON)

- **Access logs**: Request/response metadata
- **Error logs**: Failures with stack traces
- **Audit logs**: Security decisions

### Tracing

- Correlation IDs on all requests
- Distributed tracing support (OpenTelemetry)

## Configuration Lifecycle

```
┌──────────────┐
│  Config File │
│  (sentinel.  │
│   kdl)       │
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐
│    Parse     │────▶│   Validate   │
│    (KDL)     │     │   (Schema)   │
└──────────────┘     └──────┬───────┘
                            │
       ┌────────────────────┴────────────────────┐
       │                                         │
       ▼                                         ▼
┌──────────────┐                         ┌──────────────┐
│   Invalid    │                         │    Valid     │
│  (error +    │                         │  (apply)     │
│   keep old)  │                         └──────┬───────┘
└──────────────┘                                │
                                                ▼
                                         ┌──────────────┐
                                         │ Atomic Swap  │
                                         │ (ArcSwap)    │
                                         └──────┬───────┘
                                                │
                                                ▼
                                         ┌──────────────┐
                                         │ Drain Old    │
                                         │ (60s grace)  │
                                         └──────────────┘
```

## Next Steps

- [Component Design](../components/) - Deep dive into each component
- [Request Flow](../request-flow/) - Detailed request lifecycle
- [Pingora Foundation](../pingora/) - How Sentinel uses Pingora
