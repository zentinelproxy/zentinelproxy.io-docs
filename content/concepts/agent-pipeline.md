+++
title = "Agent Pipeline"
weight = 6
updated = 2026-03-02
+++

Zentinel composes agents into per-route **pipelines** that inspect and modify traffic as it flows through the proxy. This page explains the pipeline model, chaining semantics, execution strategies, and performance trade-offs.

## Pipeline Model

An agent pipeline is an ordered sequence of filters attached to a route. Each filter is an independent processing unit — it may be a built-in filter (rate limiting, CORS, compression) or an **agent filter** that delegates to an external process. The route's `filters` block defines both the composition and the execution order.

```
               Incoming Request
                      │
                      ▼
             ┌────────────────┐
             │     Route      │
             │  "api-users"   │
             └───────┬────────┘
                     │
    ─────────────────┼───── Request Phase (top → bottom) ──────
                     │
          ┌──────────▼──────────┐
          │  rate-limit filter  │  Built-in
          └──────────┬──────────┘
                     │
          ┌──────────▼──────────┐
          │   auth agent filter │  → External agent (UDS/gRPC)
          └──────────┬──────────┘
                     │
          ┌──────────▼──────────┐
          │   WAF agent filter  │  → External agent (UDS/gRPC)
          └──────────┬──────────┘
                     │
          ┌──────────▼──────────┐
          │  compression filter │  Built-in
          └──────────┬──────────┘
                     │
    ─────────────────┼───── Forward to upstream ───────────────
                     │
                     ▼
              ┌────────────┐
              │  Upstream   │
              └──────┬─────┘
                     │
    ─────────────────┼───── Response Phase (bottom → top) ─────
                     │
          ┌──────────▼──────────┐
          │  compression filter │  Built-in
          └──────────┬──────────┘
                     │
          ┌──────────▼──────────┐
          │   WAF agent filter  │  → External agent
          └──────────┬──────────┘
                     │
          ┌──────────▼──────────┐
          │   auth agent filter │  → External agent
          └──────────┬──────────┘
                     │
          ┌──────────▼──────────┐
          │  rate-limit filter  │  Built-in
          └──────────┬──────────┘
                     │
                     ▼
               Client Response
```

Key properties:

- **Request phase** executes filters in declaration order (top → bottom).
- **Response phase** executes filters in reverse declaration order (bottom → top).
- Each agent filter communicates with its external agent process over UDS or gRPC.
- A filter can short-circuit the pipeline at any point (e.g., a block decision stops further processing).

## Chaining Semantics

When multiple agents participate in a pipeline, their decisions and mutations are aggregated according to deterministic rules.

### Decision Aggregation

Agents return one of three decisions: **allow**, **block**, or **redirect**. The pipeline uses **first-block-wins** semantics:

```
┌──────────────────────────────────────────────────────────────┐
│                   Decision Aggregation                        │
├──────────┬───────────┬───────────┬───────────────────────────┤
│ Agent 1  │ Agent 2   │ Agent 3   │ Pipeline Result            │
├──────────┼───────────┼───────────┼───────────────────────────┤
│ allow    │ allow     │ allow     │ allow                      │
│ allow    │ block     │ (skipped) │ block (from Agent 2)       │
│ allow    │ redirect  │ (skipped) │ redirect (from Agent 2)    │
│ block    │ (skipped) │ (skipped) │ block (from Agent 1)       │
└──────────┴───────────┴───────────┴───────────────────────────┘
```

The first non-allow decision terminates the pipeline. Remaining agents are not called.

### Mutation Accumulation

When agents mutate the request or response, mutations accumulate as the pipeline progresses:

| Mutation Type | Accumulation Rule |
|---------------|-------------------|
| **Header set** | Merged across agents; last writer wins for the same header name |
| **Header remove** | Union of all removals |
| **Body replacement** | Last writer wins (only the final body mutation applies) |
| **Audit metadata** | Deep-merged across all agents |
| **Response header set** | Merged; last writer wins per header name |

```
Agent 1 sets:    X-User-Id: "user-123"
Agent 2 sets:    X-Threat-Score: "low", X-User-Id: "enriched-123"
Agent 3 sets:    X-Audit-Trail: "logged"

Final headers:   X-User-Id: "enriched-123"     ← Agent 2 overwrote Agent 1
                 X-Threat-Score: "low"          ← Agent 2
                 X-Audit-Trail: "logged"        ← Agent 3
```

### Per-Phase Independence

The pipeline runs independently for each event phase. An agent subscribes to the phases it cares about, and unsubscribed phases skip that agent entirely.

| Phase | Description | Typical Subscribers |
|-------|-------------|---------------------|
| `request_headers` | Incoming request headers and metadata | Auth, WAF, rate limiting |
| `request_body` | Request body chunks | WAF, content scanning, transformation |
| `response_headers` | Upstream response headers | Security headers, audit logging |
| `response_body` | Response body chunks | Content scanning, transformation, PII detection |

An agent that only subscribes to `request_headers` is never called during body or response phases, reducing pipeline cost for that request.

## Execution Strategies

Zentinel uses different execution strategies depending on the event phase to balance latency against correctness.

### Parallel Execution (Request Headers)

For the `request_headers` phase, all agent filters in the pipeline execute **in parallel**. Each agent receives the original, unmodified request headers and returns its decision independently.

```
                  Request Headers Arrive
                          │
              ┌───────────┼───────────┐
              │           │           │
              ▼           ▼           ▼
         ┌─────────┐ ┌─────────┐ ┌─────────┐
         │  Auth   │ │   WAF   │ │  Rate   │
         │  Agent  │ │  Agent  │ │  Limit  │
         │  (8ms)  │ │  (12ms) │ │  (3ms)  │
         └────┬────┘ └────┬────┘ └────┬────┘
              │           │           │
              └───────────┼───────────┘
                          │
                          ▼
                   Aggregate Results
                   Total: 12ms (not 23ms)
```

This makes pipeline latency **O(L)** where L is the latency of the slowest agent, not **O(N×L)** which would result from sequential execution.

### Sequential Execution (Body and Response Phases)

For `request_body`, `response_headers`, and `response_body` phases, agents execute **sequentially** in pipeline order. This is necessary because:

- Body mutations from one agent must be visible to the next.
- Response header mutations accumulate in order.
- Flow control (pause/resume) requires sequential coordination.

```
              Request Body Chunk Arrives
                        │
                        ▼
                  ┌───────────┐
                  │    WAF    │  Inspect body, may block
                  │   Agent   │
                  └─────┬─────┘
                        │
                        ▼
                  ┌───────────┐
                  │ Transform │  Modify body content
                  │   Agent   │
                  └─────┬─────┘
                        │
                        ▼
                  ┌───────────┐
                  │   Audit   │  Log body hash
                  │   Agent   │
                  └─────┬─────┘
                        │
                        ▼
                  Forward to upstream
```

### Strategy Summary

| Event Phase | Strategy | Rationale |
|-------------|----------|-----------|
| `request_headers` | Parallel | Agents inspect independently; no mutation dependencies |
| `request_body` | Sequential | Body mutations must chain; flow control |
| `response_headers` | Sequential | Header mutations accumulate in order |
| `response_body` | Sequential | Body mutations must chain; flow control |

## Per-Agent Isolation

Each agent in the pipeline operates with its own isolation boundaries, preventing one agent's failure from cascading through the system.

### Semaphore-Based Queue Isolation

Every agent filter has a configurable concurrency semaphore that limits how many in-flight requests it processes simultaneously. When the semaphore is full, new requests queue (up to a configurable depth) or trigger the filter's failure mode.

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent: WAF                                │
│                                                             │
│  Semaphore: 3/3 in-flight                                   │
│  ┌────────┐ ┌────────┐ ┌────────┐                           │
│  │ Req #1 │ │ Req #2 │ │ Req #3 │  ← Processing             │
│  └────────┘ └────────┘ └────────┘                           │
│                                                             │
│  Queue: 2 waiting (max 10)                                  │
│  ┌────────┐ ┌────────┐                                      │
│  │ Req #4 │ │ Req #5 │              ← Queued                │
│  └────────┘ └────────┘                                      │
│                                                             │
│  Req #6 arrives → queued (position 3)                       │
│  Req #14 arrives → queue full → fail-mode triggered         │
└─────────────────────────────────────────────────────────────┘
```

### Circuit Breakers

Each agent connection tracks health using lock-free atomics and implements the circuit breaker pattern:

```
  ┌──────────┐    error rate > threshold    ┌──────────┐
  │  Closed  │ ────────────────────────────▶│   Open   │
  │ (normal) │                              │ (reject) │
  └──────────┘                              └────┬─────┘
       ▲                                         │
       │                                    cooldown expires
       │         success                         │
       │    ┌────────────┐                       │
       └────│ Half-Open  │◀──────────────────────┘
            │  (probe)   │
            └────────────┘
```

- **Closed** — Normal operation. Errors are counted.
- **Open** — Agent is considered unhealthy. Requests skip it and apply the filter's failure mode.
- **Half-Open** — A single probe request is sent. Success returns to Closed; failure returns to Open.

Health state is checked via atomic loads (~10ns), adding negligible overhead to the hot path.

### Per-Filter Failure Modes

Each agent filter configures its own failure behavior independently:

| Failure Mode | Behavior | Use Case |
|--------------|----------|----------|
| `fail-open` | Allow request to continue | Non-critical agents (analytics, logging) |
| `fail-closed` | Block request with 503 | Critical security agents (auth, WAF) |

```kdl
filters {
    filter "auth" {
        agent "auth-agent"
        fail-mode "fail-closed"     // Auth failure = block
        timeout-ms 5000
    }

    filter "analytics" {
        agent "analytics-agent"
        fail-mode "fail-open"       // Analytics failure = continue
        timeout-ms 2000
    }
}
```

### Graceful Degradation

When an agent enters the Open circuit breaker state, the pipeline continues with the remaining healthy agents. This provides defense in depth — losing one layer does not disable the entire pipeline.

```
Pipeline with 3 agents:

Normal:     [Auth ✓] → [WAF ✓] → [Rate Limit ✓] → upstream
Degraded:   [Auth ✓] → [WAF ✗ fail-open] → [Rate Limit ✓] → upstream
Critical:   [Auth ✓] → [WAF ✗ fail-open] → [Rate Limit ✗ fail-closed] → 503
```

## Performance Characteristics

Agent pipelines add latency proportional to the number of agents and the transport used. Understanding these costs helps you design pipelines that meet your latency budget.

### IPC Cost Per Agent

| Transport | Typical Latency | Best For |
|-----------|----------------|----------|
| UDS (Unix Domain Socket) | ~50–200µs | Same-host agents, lowest latency |
| gRPC | ~200–500µs | Cross-host agents, language flexibility |

These numbers represent the round-trip IPC overhead, excluding agent processing time. See [Performance](../../agents/v2/performance/) for detailed benchmarks including serialization costs and throughput numbers.

### Pipeline Depth vs Latency

For the `request_headers` phase (parallel execution):

```
Pipeline     Agents    Parallel Latency    Notes
────────     ──────    ────────────────    ─────
Minimal      1 agent   ~100µs              Single agent overhead
Standard     3 agents  ~200µs              Bounded by slowest agent
Deep         5 agents  ~300µs              Marginal cost per agent is low
```

For sequential phases (body/response), latency scales linearly:

```
Pipeline     Agents    Sequential Latency    Notes
────────     ──────    ──────────────────    ─────
Minimal      1 agent   ~100µs                Single agent overhead
Standard     3 agents  ~400µs                Sum of all agent latencies
Deep         5 agents  ~700µs                Each agent adds its full cost
```

### The Out-of-Process Trade-off

Zentinel's agent model runs security logic in separate processes. This adds IPC cost but provides significant benefits:

| | In-Process (e.g., Wasm, Lua) | Out-of-Process (Agents) |
|--|-------------------------------|------------------------|
| **Latency** | ~1–10µs | ~50–500µs |
| **Isolation** | Crash can affect proxy | Crash is contained |
| **Deployment** | Requires proxy restart | Independent updates |
| **Language** | Limited (Wasm, Lua) | Any language |
| **Resource limits** | Shared with proxy | Separate memory/CPU |
| **Debugging** | Harder (embedded) | Standard tooling |
| **Scaling** | Scales with proxy | Scales independently |

For most security workloads, the 50–500µs overhead is negligible compared to the network latency of the upstream request (typically 5–50ms). The isolation and operational benefits outweigh the cost.

> **Note:** Zentinel also supports [WASM agents](/agents/wasm/) for cases where in-process latency is critical. WASM agents run inside the proxy process with Wasmtime sandboxing, offering a middle ground between pure in-process and out-of-process execution.

See [Comparison](../comparison/) for how Zentinel's agent overhead compares to Envoy ext_proc, HAProxy SPOE, and NGINX njs.

## Pipeline Patterns

These patterns illustrate common pipeline compositions for real-world use cases.

### Security Gateway

A standard security gateway that authenticates, inspects, and rate-limits traffic:

```kdl
route "api" {
    matches { path-prefix "/api/" }
    upstream "backend"

    filters {
        filter "rate-limit" {
            type "rate-limit"
            requests-per-second 100
            burst 20
        }

        filter "auth" {
            agent "auth-agent"
            fail-mode "fail-closed"
            timeout-ms 5000
        }

        filter "waf" {
            agent "waf-agent"
            fail-mode "fail-closed"
            timeout-ms 3000
        }
    }
}
```

**Pipeline behavior:** Rate limiting runs first (cheapest check). Auth validates credentials. WAF inspects request content. All three run in parallel during `request_headers`. If auth or WAF blocks, the request never reaches the upstream.

### API Gateway

An API gateway that authenticates, transforms requests, and logs for audit:

```kdl
route "partner-api" {
    matches {
        path-prefix "/partner/v2/"
        header "X-Partner-Key"
    }
    upstream "partner-service"

    filters {
        filter "auth" {
            agent "auth-agent"
            fail-mode "fail-closed"
            timeout-ms 5000
        }

        filter "transform" {
            agent "transform-agent"
            fail-mode "fail-closed"
            timeout-ms 2000
        }

        filter "audit" {
            agent "audit-logger-agent"
            fail-mode "fail-open"
            timeout-ms 1000
        }
    }
}
```

**Pipeline behavior:** Auth validates the partner key. Transform rewrites headers or body for the backend. Audit logs the request metadata. The audit agent is fail-open — a logging failure should never block a partner request.

### Observability Pipeline

A lightweight pipeline focused on traffic visibility:

```kdl
route "all-traffic" {
    matches { path-prefix "/" }
    upstream "backend"

    filters {
        filter "access-log" {
            agent "audit-logger-agent"
            fail-mode "fail-open"
            timeout-ms 1000
        }

        filter "analytics" {
            agent "analytics-agent"
            fail-mode "fail-open"
            timeout-ms 500
        }
    }
}
```

**Pipeline behavior:** Both agents are fail-open. The pipeline never blocks traffic — it only observes. If either agent is slow or down, requests continue unaffected.

### Defense in Depth

A multi-layered security pipeline for high-value endpoints:

```kdl
route "admin" {
    matches {
        path-prefix "/admin/"
        method "GET" "POST" "PUT" "DELETE"
    }
    upstream "admin-service"

    filters {
        filter "rate-limit" {
            type "rate-limit"
            requests-per-second 10
            burst 5
        }

        filter "ip-reputation" {
            agent "ip-reputation-agent"
            fail-mode "fail-closed"
            timeout-ms 3000
        }

        filter "auth" {
            agent "auth-agent"
            fail-mode "fail-closed"
            timeout-ms 5000
        }

        filter "waf" {
            agent "waf-agent"
            fail-mode "fail-closed"
            timeout-ms 3000
        }

        filter "content-scanner" {
            agent "content-scanner-agent"
            fail-mode "fail-closed"
            timeout-ms 5000
        }
    }
}
```

**Pipeline behavior:** Five layers of defense, all fail-closed. Rate limiting and IP reputation filter obvious abuse cheaply. Auth validates identity. WAF inspects headers. Content scanner inspects request bodies for malicious payloads. During `request_headers`, the agent filters run in parallel — the total overhead is bounded by the slowest agent (~5ms), not the sum of all agents.

## Configuration Reference

A complete configuration example showing a pipeline with listeners, routes, agents, upstreams, and filters:

```kdl
system {
    worker-threads 4
}

listeners {
    listener "https" {
        address "0.0.0.0:443"
        tls {
            cert-path "/etc/zentinel/certs/api.crt"
            key-path "/etc/zentinel/certs/api.key"
        }
    }
}

agents {
    agent "auth-agent" {
        socket "/var/run/zentinel/auth.sock"
        pool-size 4
        events "request_headers"
    }

    agent "waf-agent" {
        socket "/var/run/zentinel/waf.sock"
        pool-size 8
        events "request_headers" "request_body" "response_body"
    }

    agent "audit-agent" {
        socket "/var/run/zentinel/audit.sock"
        pool-size 2
        events "request_headers" "response_headers"
    }
}

routes {
    route "api" {
        priority 100

        matches {
            path-prefix "/api/"
            method "GET" "POST" "PUT" "DELETE"
        }

        upstream "api-backend"

        filters {
            filter "rate-limit" {
                type "rate-limit"
                requests-per-second 100
                burst 20
            }

            filter "auth" {
                agent "auth-agent"
                fail-mode "fail-closed"
                timeout-ms 5000
                max-concurrent 100
            }

            filter "waf" {
                agent "waf-agent"
                fail-mode "fail-closed"
                timeout-ms 3000
                max-concurrent 50
            }

            filter "headers" {
                type "headers"
                response {
                    set "X-Content-Type-Options" "nosniff"
                    set "X-Frame-Options" "DENY"
                }
            }

            filter "audit" {
                agent "audit-agent"
                fail-mode "fail-open"
                timeout-ms 1000
                max-concurrent 200
            }
        }
    }
}

upstreams {
    upstream "api-backend" {
        targets {
            target { address "10.0.1.1:8080" weight 5 }
            target { address "10.0.1.2:8080" weight 5 }
        }
        load-balancing "round_robin"
        health-check {
            path "/health"
            interval-secs 10
        }
    }
}
```

This configuration creates a pipeline where:

1. **Rate limiting** rejects excessive traffic (built-in, no IPC cost).
2. **Auth agent** validates credentials via UDS (fail-closed).
3. **WAF agent** inspects headers and body via UDS (fail-closed).
4. **Headers filter** adds security response headers (built-in).
5. **Audit agent** logs request/response metadata via UDS (fail-open).

During the `request_headers` phase, agents 2, 3, and 5 execute in parallel. During `request_body`, only the WAF agent runs (it's the only one subscribed). During `response_headers`, the audit agent captures the response metadata.

## Next Steps

- [Request Lifecycle](../request-flow/) — How requests traverse the full proxy lifecycle
- [Routing System](../routing/) — Route matching and priority rules
- [Filters Configuration](/configuration/filters/) — Complete filter type reference
- [Connection Pooling](/agents/v2/pooling/) — Agent connection management and load balancing
- [Performance](/agents/v2/performance/) — Detailed benchmarks and optimization profiles
- [Comparison](../comparison/) — How Zentinel's agent model compares to alternatives
