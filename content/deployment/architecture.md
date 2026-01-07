+++
title = "Deployment Architecture"
weight = 1
+++

This page explains Sentinel's deployment philosophy and why agents are managed externally.

## Why Sentinel Doesn't Manage Agents

A natural question: *"Why doesn't Sentinel just spawn and supervise agents itself?"*

We considered this approach but rejected it for several reasons:

### 1. Dataplane Stays Boring

Sentinel's core proxy must be predictable and stable. Adding process management would:
- Increase complexity and potential failure modes
- Create coupling between proxy and agent lifecycles
- Make the proxy harder to reason about under load

### 2. Blast Radius Isolation

With external agents:
- A crashing agent can't take down the proxy
- Memory leaks in agents don't affect proxy stability
- Agents can be restarted without proxy disruption

### 3. Independent Deployment

Teams often need to:
- Update WAF rules without touching the proxy
- Deploy new agent versions independently
- Roll back agents without affecting traffic

### 4. Leverage Existing Tools

Process supervision is a solved problem:
- **systemd** provides robust service management, resource limits, logging
- **Docker/K8s** add containerization, scaling, health checks
- Reinventing this would be worse than using battle-tested tools

## The Sentinel Model

```
┌──────────────────────────────────────────────────────────────────┐
│                        Host / Pod / VM                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐      ┌─────────────────┐                   │
│  │  Process        │      │  Process        │                   │
│  │  Supervisor     │      │  Supervisor     │                   │
│  │  (systemd/      │      │  (systemd/      │                   │
│  │   docker/k8s)   │      │   docker/k8s)   │                   │
│  └────────┬────────┘      └────────┬────────┘                   │
│           │                        │                             │
│           ▼                        ▼                             │
│  ┌─────────────────┐      ┌─────────────────┐                   │
│  │    Sentinel     │◄────►│   Auth Agent    │                   │
│  │    (proxy)      │ UDS  │   (process)     │                   │
│  │                 │      └─────────────────┘                   │
│  │                 │                                             │
│  │                 │      ┌─────────────────┐                   │
│  │                 │◄────►│   WAF Agent     │                   │
│  │                 │ gRPC │   (container)   │                   │
│  └─────────────────┘      └─────────────────┘                   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

Key points:
- Sentinel connects to agents, doesn't spawn them
- Each component has its own supervisor
- Failure in one component doesn't cascade
- Components can be updated independently

## Agent Lifecycle

### Connection Behavior

When Sentinel starts:
1. Reads agent configuration from `sentinel.kdl`
2. Attempts to connect to each configured agent
3. For missing agents, behavior depends on `failure-mode`:
   - `failure-mode "open"` — Requests proceed without agent
   - `failure-mode "closed"` — Requests blocked until agent available

### Health Checking

Sentinel monitors agent health for circuit breaking (not supervision):

```kdl
agent "auth" type="auth" {
    unix-socket "/run/sentinel/auth.sock"

    health-check {
        enabled #true
        interval-ms 5000
        timeout-ms 100
        healthy-threshold 2
        unhealthy-threshold 3
    }

    circuit-breaker {
        failure-threshold 5
        success-threshold 3
        timeout-seconds 30
    }
}
```

### Graceful Degradation

```
Agent Health States:

  HEALTHY ──────────────────────────────────────────────▶ Requests routed
     │                                                      to agent
     │ failures > threshold
     ▼
  UNHEALTHY ────────────────────────────────────────────▶ Circuit OPEN
     │                                                      (fail-open/closed)
     │ timeout expires
     ▼
  HALF-OPEN ────────────────────────────────────────────▶ Probe requests
     │                                                      sent to agent
     │ successes > threshold
     ▼
  HEALTHY ──────────────────────────────────────────────▶ Circuit CLOSED
```

## Deployment Patterns

### Pattern 1: Co-located (Same Host)

Best for: Single-server deployments, development

```
┌─────────────────────────────────────────┐
│              Single Host                │
│  ┌──────────┐  ┌──────────┐            │
│  │ Sentinel │──│ Agent 1  │ (UDS)      │
│  │          │  └──────────┘            │
│  │          │  ┌──────────┐            │
│  │          │──│ Agent 2  │ (UDS)      │
│  └──────────┘  └──────────┘            │
└─────────────────────────────────────────┘
```

### Pattern 2: Sidecar (Same Pod/Container Group)

Best for: Kubernetes, Docker Compose

```
┌─────────────────────────────────────────┐
│                  Pod                    │
│  ┌──────────┐  ┌──────────┐            │
│  │ Sentinel │──│ Agent    │ (localhost)│
│  │          │  │ sidecar  │            │
│  └──────────┘  └──────────┘            │
└─────────────────────────────────────────┘
```

### Pattern 3: Service (Remote)

Best for: Shared agents, high availability, scaling

```
┌──────────────┐        ┌──────────────────────┐
│   Sentinel   │        │   Agent Service      │
│   Pod 1      │───────▶│   (3 replicas)       │
├──────────────┤  gRPC  │   ┌────┐ ┌────┐     │
│   Sentinel   │───────▶│   │ R1 │ │ R2 │ ... │
│   Pod 2      │        │   └────┘ └────┘     │
└──────────────┘        └──────────────────────┘
```

## Configuration Reference

### Agent Connection

```kdl
agents {
    // Unix socket (local)
    agent "auth" type="auth" {
        unix-socket "/run/sentinel/auth.sock"
        timeout-ms 100
        failure-mode "closed"
    }

    // gRPC (local or remote)
    agent "waf" type="waf" {
        grpc "http://waf-service:50051"
        timeout-ms 200
        failure-mode "open"
    }
}
```

### Failure Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `"closed"` | Block requests when agent unavailable | Security-critical (auth, WAF) |
| `"open"` | Allow requests when agent unavailable | Non-critical (logging, metrics) |

### Timeouts

```kdl
agent "auth" type="auth" {
    unix-socket "/run/sentinel/auth.sock"

    // Per-request timeout
    timeout-ms 100

    // Connection settings
    connect-timeout-ms 1000

    // Retry on transient failures
    retry {
        attempts 2
        backoff-ms 10
    }
}
```

## Best Practices

### 1. Always Configure Failure Modes

```kdl
// Good: Explicit failure handling
agent "auth" type="auth" {
    unix-socket "/run/sentinel/auth.sock"
    failure-mode "closed"  // Security: fail closed
}

agent "metrics" type="custom" {
    grpc "http://localhost:50052"
    failure-mode "open"  // Observability: fail open
}
```

### 2. Set Appropriate Timeouts

```kdl
// Auth should be fast
agent "auth" { timeout-ms 50 }

// WAF inspecting bodies needs more time
agent "waf" { timeout-ms 200 }

// External services need buffer
agent "external" { timeout-ms 500 }
```

### 3. Use Circuit Breakers

Prevent cascade failures when agents are degraded:

```kdl
agent "auth" type="auth" {
    unix-socket "/run/sentinel/auth.sock"

    circuit-breaker {
        failure-threshold 5      // Open after 5 failures
        success-threshold 3      // Close after 3 successes
        timeout-seconds 30       // Try again after 30s
    }
}
```

### 4. Monitor Agent Health

Export metrics for alerting:

```
# HELP sentinel_agent_health Agent health status
# TYPE sentinel_agent_health gauge
sentinel_agent_health{agent="auth"} 1
sentinel_agent_health{agent="waf"} 0

# HELP sentinel_agent_latency_seconds Agent call latency
# TYPE sentinel_agent_latency_seconds histogram
sentinel_agent_latency_seconds_bucket{agent="auth",le="0.01"} 9823
sentinel_agent_latency_seconds_bucket{agent="auth",le="0.05"} 9901
```
