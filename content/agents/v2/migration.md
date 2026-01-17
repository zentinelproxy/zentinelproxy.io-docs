+++
title = "Migration Guide (v1 to v2)"
weight = 6
+++

This guide helps you migrate from Agent Protocol v1 to v2. The v2 protocol offers significant improvements in performance, reliability, and observability while maintaining conceptual compatibility.

## Why Migrate?

| Improvement | v1 | v2 |
|-------------|----|----|
| **Latency** | ~50μs per request | ~10-20μs per request |
| **Throughput** | Single connection | Pooled connections (4x+ throughput) |
| **Reliability** | Basic timeouts | Circuit breakers, health tracking |
| **Streaming** | Limited | Full bidirectional streaming |
| **Observability** | Manual | Built-in Prometheus metrics |
| **NAT Traversal** | Not supported | Reverse connections |

---

## Quick Migration

### Minimal Change (Drop-in)

If you just want pooling benefits without code changes:

**Before (v1):**
```rust
use sentinel_agent_protocol::AgentClient;

let client = AgentClient::unix_socket(
    "proxy",
    "/var/run/agent.sock",
    Duration::from_secs(5),
).await?;

let response = client.send_event(EventType::RequestHeaders, &event).await?;
```

**After (v2):**
```rust
use sentinel_agent_protocol::v2::AgentPool;

let pool = AgentPool::new();
pool.add_agent("agent", "/var/run/agent.sock").await?;

let response = pool.send_request_headers("agent", &headers).await?;
```

The `AgentPool` automatically:
- Maintains 4 connections per agent
- Load balances requests
- Tracks health and circuit breaker state
- Exports Prometheus metrics

---

## Step-by-Step Migration

### 1. Update Dependencies

```toml
# Cargo.toml
[dependencies]
sentinel-agent-protocol = "0.3"  # v2 included
```

### 2. Import v2 Types

```rust
// Before
use sentinel_agent_protocol::{AgentClient, EventType, AgentEvent};

// After
use sentinel_agent_protocol::v2::{
    AgentPool,
    AgentPoolConfig,
    LoadBalanceStrategy,
    Decision,
};
```

### 3. Replace Client with Pool

**Before:**
```rust
// Create individual clients
let waf_client = AgentClient::unix_socket("proxy", "/run/waf.sock", timeout).await?;
let auth_client = AgentClient::grpc("http://localhost:50051", timeout).await?;

// Store clients somewhere
struct Clients {
    waf: AgentClient,
    auth: AgentClient,
}
```

**After:**
```rust
// Create single pool for all agents
let pool = AgentPool::new();

// Add agents (transport auto-detected)
pool.add_agent("waf", "/run/waf.sock").await?;
pool.add_agent("auth", "localhost:50051").await?;

// Pool is Clone + Send + Sync
let pool = Arc::new(pool);
```

### 4. Update Request Sending

**Before:**
```rust
let event = AgentEvent {
    event_type: EventType::RequestHeaders,
    request_id: req_id,
    method: method.to_string(),
    uri: uri.to_string(),
    headers: headers.clone(),
    // ...
};

let response = client.send_event(EventType::RequestHeaders, &event).await?;
```

**After:**
```rust
use sentinel_agent_protocol::v2::RequestHeadersEvent;

let event = RequestHeadersEvent {
    correlation_id: correlation_id.clone(),
    method: method.to_string(),
    uri: uri.to_string(),
    headers: headers.clone(),
    client_ip: client_ip.clone(),
    // ...
};

let response = pool.send_request_headers("waf", &event).await?;
```

### 5. Update Response Handling

**Before:**
```rust
match response.action {
    Action::Allow => { /* continue */ }
    Action::Block => {
        return Err(blocked_response(response.status_code));
    }
    Action::Redirect(url) => {
        return Ok(redirect_response(url));
    }
}
```

**After:**
```rust
match response.decision {
    Decision::Allow => { /* continue */ }
    Decision::Block { status, body, headers } => {
        return Err(blocked_response(status, body, headers));
    }
    Decision::Redirect { location, status } => {
        return Ok(redirect_response(location, status));
    }
    Decision::Modify { headers_to_add, headers_to_remove } => {
        apply_modifications(&mut request, headers_to_add, headers_to_remove);
    }
}
```

### 6. Add Error Handling for New Error Types

```rust
use sentinel_agent_protocol::v2::AgentProtocolError;

match pool.send_request_headers("waf", &event).await {
    Ok(response) => handle_response(response),

    // New in v2: Circuit breaker open
    Err(AgentProtocolError::CircuitBreakerOpen { agent_id }) => {
        tracing::warn!("Circuit open for {}, applying fallback", agent_id);
        apply_fallback_policy()
    }

    // New in v2: Flow control
    Err(AgentProtocolError::FlowControlPaused { agent_id }) => {
        tracing::warn!("Agent {} paused, request rejected", agent_id);
        apply_fallback_policy()
    }

    // Existing errors still work
    Err(AgentProtocolError::Timeout) => {
        apply_fallback_policy()
    }

    Err(e) => {
        tracing::error!("Agent error: {}", e);
        apply_fallback_policy()
    }
}
```

---

## Configuration Migration

### KDL Configuration

**Before (v1):**
```kdl
agents {
    agent "waf" type="waf" {
        unix-socket "/var/run/waf.sock"
        timeout-ms 100
        failure-mode "open"
    }
}
```

**After (v2):**
```kdl
agents {
    agent "waf" type="waf" {
        unix-socket "/var/run/waf.sock"
        protocol-version 2           // Enable v2
        connections 4                // Connection pool size
        timeout-ms 100
        failure-mode "open"

        // New v2 options
        circuit-breaker {
            failure-threshold 5
            reset-timeout-seconds 30
        }
    }
}
```

### Rust Configuration

**Before:**
```rust
let client = AgentClient::unix_socket(
    "proxy",
    socket_path,
    Duration::from_millis(100),
).await?;
```

**After:**
```rust
let config = AgentPoolConfig {
    connections_per_agent: 4,
    load_balance_strategy: LoadBalanceStrategy::LeastConnections,
    request_timeout: Duration::from_millis(100),
    circuit_breaker_threshold: 5,
    circuit_breaker_reset_timeout: Duration::from_secs(30),
    ..Default::default()
};

let pool = AgentPool::with_config(config);
pool.add_agent("waf", socket_path).await?;
```

---

## Feature-by-Feature Migration

### Body Streaming

**Before (v1):**
```rust
// Send body as single event
let body_event = AgentEvent {
    event_type: EventType::RequestBody,
    body: Some(full_body),
    ..
};
client.send_event(EventType::RequestBody, &body_event).await?;
```

**After (v2):**
```rust
// Stream body in chunks
for (i, chunk) in body_chunks.enumerate() {
    let is_last = i == body_chunks.len() - 1;

    let chunk_event = RequestBodyChunkEvent {
        correlation_id: correlation_id.clone(),
        data: chunk,
        chunk_index: i as u32,
        is_last,
        ..Default::default()
    };

    pool.send_request_body_chunk("waf", &chunk_event).await?;
}
```

### Health Checks

**Before (v1):**
```rust
// Manual health check
match client.ping().await {
    Ok(_) => { /* healthy */ }
    Err(_) => { /* unhealthy, handle manually */ }
}
```

**After (v2):**
```rust
// Automatic health tracking
let health = pool.get_health("waf")?;

println!("Healthy connections: {}/{}",
    health.healthy_connections,
    health.total_connections);
println!("Success rate: {:.1}%", health.success_rate * 100.0);
println!("Circuit breaker: {:?}", health.circuit_breaker_state);
```

### Metrics

**Before (v1):**
```rust
// Manual metrics collection
metrics::counter!("agent_requests_total").increment(1);
let start = Instant::now();
let result = client.send_event(...).await;
metrics::histogram!("agent_request_duration").record(start.elapsed());
```

**After (v2):**
```rust
// Automatic metrics export
let prometheus_output = pool.metrics_collector().export_prometheus();
// Expose via /metrics endpoint

// Or get snapshot for custom handling
let snapshot = pool.protocol_metrics().snapshot();
println!("Total requests: {}", snapshot.requests_total);
println!("In-flight: {}", snapshot.in_flight_requests);
```

---

## Agent-Side Migration

If you maintain custom agents, update the server implementation:

### gRPC Agents

The protobuf definitions are compatible. Update to support new message types:

```protobuf
// New message types in v2
message RequestHeadersEvent {
    string correlation_id = 1;
    string method = 2;
    string uri = 3;
    map<string, StringList> headers = 4;
    // ...
}

message RequestBodyChunkEvent {
    string correlation_id = 1;
    bytes data = 2;
    bool is_last = 3;
    uint32 chunk_index = 4;
    // ...
}
```

### UDS Agents

V2 UDS uses binary MessagePack encoding for better performance:

```rust
// Server handshake response includes encoding negotiation
let handshake = HandshakeResponse {
    agent_id: "my-agent".to_string(),
    supported_encodings: vec!["msgpack", "json"],
    capabilities: Capabilities {
        handles_request_body: true,
        handles_response_body: false,
        supports_streaming: true,
        max_concurrent_requests: Some(100),
    },
};
```

---

## Rollback Plan

If you need to rollback to v1:

1. **Keep v1 client code** in a feature flag during migration
2. **Monitor metrics** during rollout
3. **Gradual rollout** using traffic splitting

```rust
#[cfg(feature = "agent-v2")]
async fn send_to_agent(event: &Event) -> Result<Response> {
    pool.send_request_headers("waf", event).await
}

#[cfg(not(feature = "agent-v2"))]
async fn send_to_agent(event: &Event) -> Result<Response> {
    client.send_event(EventType::RequestHeaders, event).await
}
```

---

## Compatibility Notes

### Wire Protocol

- v2 UDS uses length-prefixed MessagePack (or JSON with negotiation)
- v2 gRPC uses updated protobuf messages
- v1 agents cannot connect to v2 pool (and vice versa)

### Breaking Changes

| Change | Migration |
|--------|-----------|
| `AgentClient` → `AgentPool` | Use pool pattern |
| `send_event()` → `send_request_headers()` | Update method calls |
| `Action` → `Decision` | Update response handling |
| `EventType` enum removed | Use typed methods |
| Request ID → Correlation ID | Use string correlation IDs |

### Deprecated (Still Working)

| Deprecated | Replacement |
|------------|-------------|
| `AgentClient` (v1) | `AgentPool` (v2) |
| JSON-only UDS | MessagePack UDS |
| Manual health checks | Automatic health tracking |

---

## Troubleshooting

### "Connection refused" after migration

Ensure the agent supports v2 protocol. Check handshake:

```bash
# Test UDS connection
echo '{"type":"handshake","version":2}' | nc -U /var/run/agent.sock
```

### Circuit breaker keeps opening

Tune thresholds for your error rates:

```rust
let config = AgentPoolConfig {
    circuit_breaker_threshold: 10,  // More tolerant
    circuit_breaker_reset_timeout: Duration::from_secs(10),  // Faster recovery
    ..Default::default()
};
```

### Higher latency than expected

Check connection pool size and load balancing:

```rust
// For low-latency workloads
let config = AgentPoolConfig {
    connections_per_agent: 2,  // Fewer connections
    load_balance_strategy: LoadBalanceStrategy::LeastConnections,
    ..Default::default()
};
```

### Memory usage increased

Large bodies may need mmap buffers:

```toml
[dependencies]
sentinel-agent-protocol = { version = "0.3", features = ["mmap-buffers"] }
```

---

## Next Steps

After migration:

1. **Enable metrics export** - Add `/metrics` endpoint for Prometheus
2. **Configure alerts** - Set up alerts for circuit breaker state
3. **Tune pool size** - Adjust `connections_per_agent` based on load testing
4. **Consider reverse connections** - For agents behind NAT/firewalls

See also:
- [API Reference](../api/)
- [Connection Pooling](../pooling/)
- [Transport Options](../transports/)
