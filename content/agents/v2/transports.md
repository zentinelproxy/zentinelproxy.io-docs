+++
title = "Transport Options"
weight = 4
+++

This document covers the three transport mechanisms available in Agent Protocol v2: gRPC, Unix Domain Sockets (UDS), and Reverse Connections.

## Transport Comparison

| Feature | gRPC | UDS Binary | Reverse Connection |
|---------|------|------------|-------------------|
| **Latency** | ~1.2ms | ~0.4ms | ~0.5ms |
| **Throughput** | 28K req/s | 45K req/s | 40K req/s |
| **TLS Support** | Yes | N/A (local) | Yes |
| **Cross-network** | Yes | No | Yes |
| **NAT Traversal** | No | No | Yes |
| **Max Message** | 10 MB | 16 MB | 16 MB |
| **Flow Control** | HTTP/2 | Manual | Manual |

---

## gRPC Transport

### Overview

gRPC over HTTP/2 is the best choice for:
- Remote agents across networks
- Agents requiring TLS encryption
- Language-agnostic implementations
- Complex streaming scenarios

### Client Setup

```rust
use sentinel_agent_protocol::v2::AgentClientV2;
use std::time::Duration;

// Basic connection
let client = AgentClientV2::connect(
    "waf-agent",
    "http://localhost:50051",
    Duration::from_secs(30),
).await?;

// With TLS
use sentinel_agent_protocol::v2::TlsConfig;

let tls_config = TlsConfig {
    ca_cert: Some("/path/to/ca.crt".into()),
    client_cert: Some("/path/to/client.crt".into()),
    client_key: Some("/path/to/client.key".into()),
    verify_server: true,
};

let client = AgentClientV2::connect_with_tls(
    "waf-agent",
    "https://waf.internal:50051",
    tls_config,
    Duration::from_secs(30),
).await?;
```

### Streaming Semantics

gRPC v2 uses bidirectional streaming for efficient request handling:

```
Proxy                                    Agent
  │                                        │
  │ ──── RequestHeaders (id=1) ──────────► │
  │ ──── RequestBodyChunk (id=1) ────────► │
  │                                        │
  │ ◄──── Decision (id=1) ──────────────── │
  │                                        │
  │ ──── RequestHeaders (id=2) ──────────► │  (pipelined)
  │ ──── CancelRequest (id=1) ───────────► │  (cancellation)
  │                                        │
```

---

## Unix Domain Socket (UDS) Transport

### Overview

UDS binary transport is the best choice for:
- Co-located agents on the same host
- Lowest possible latency requirements
- High-throughput local processing
- Simple deployment without TLS

### Wire Format

```
┌──────────────────┬──────────────────┬─────────────────────────────────┐
│ Length (4 bytes) │ Type (1 byte)    │ JSON Payload (variable length)  │
│ Big-endian u32   │ Message type ID  │ UTF-8 encoded                   │
└──────────────────┴──────────────────┴─────────────────────────────────┘
```

### Client Setup

```rust
use sentinel_agent_protocol::v2::AgentClientV2Uds;
use std::time::Duration;

let client = AgentClientV2Uds::connect(
    "auth-agent",
    "/var/run/sentinel/auth.sock",
    Duration::from_secs(30),
).await?;

// Query capabilities after handshake
let caps = client.capabilities();
println!("Agent: {}", caps.agent_name);
println!("Streaming: {}", caps.supports_streaming);
```

### Handshake Protocol

UDS connections begin with a handshake:

```
Proxy                                              Agent
  │                                                  │
  │ ──── Connect ────────────────────────────────► │
  │                                                  │
  │ ──── HandshakeRequest ─────────────────────────► │
  │      {                                           │
  │        protocol_version: 2,                      │
  │        client_name: "sentinel-proxy",            │
  │        supported_features: ["streaming", ...]    │
  │      }                                           │
  │                                                  │
  │ ◄──────────────────────── HandshakeResponse ─── │
  │      {                                           │
  │        protocol_version: 2,                      │
  │        agent_name: "auth-agent",                 │
  │        capabilities: { ... }                     │
  │      }                                           │
  │                                                  │
  │          (normal message flow)                   │
  │                                                  │
```

### Message Types

| Type ID | Name | Direction |
|---------|------|-----------|
| `0x01` | HandshakeRequest | Proxy → Agent |
| `0x02` | HandshakeResponse | Agent → Proxy |
| `0x10` | RequestHeaders | Proxy → Agent |
| `0x11` | RequestBodyChunk | Proxy → Agent |
| `0x12` | ResponseHeaders | Proxy → Agent |
| `0x13` | ResponseBodyChunk | Proxy → Agent |
| `0x20` | Decision | Agent → Proxy |
| `0x30` | CancelRequest | Proxy → Agent |
| `0x31` | CancelAll | Proxy → Agent |
| `0xF0` | Ping | Either |
| `0xF1` | Pong | Either |

### Binary Encoding (MessagePack)

UDS supports MessagePack encoding for improved performance over JSON. Encoding is negotiated during the handshake.

**Enable in Cargo.toml:**

```toml
sentinel-agent-protocol = { version = "0.3", features = ["binary-uds"] }
```

**Handshake with encoding negotiation:**

```
Proxy                                              Agent
  │                                                  │
  │ ──── HandshakeRequest ─────────────────────────► │
  │      { supported_encodings: ["msgpack", "json"] }│
  │                                                  │
  │ ◄──────────────────────── HandshakeResponse ─── │
  │      { encoding: "msgpack" }                     │
  │                                                  │
  │          (subsequent messages use msgpack)       │
```

**Available encodings:**

| Encoding | Pros | Cons |
|----------|------|------|
| `json` | Human readable, always available | Larger payloads, slower |
| `msgpack` | Compact, fast serialization | Requires `binary-uds` feature |

### Zero-Copy Body Streaming

For large request/response bodies, use binary body chunk methods to avoid base64 encoding overhead:

```rust
use sentinel_agent_protocol::{BinaryRequestBodyChunkEvent, Bytes};

// Create binary body chunk (no base64)
let chunk = BinaryRequestBodyChunkEvent::new(
    "correlation-123",
    Bytes::from_static(b"raw binary data"),
    0,      // chunk_index
    false,  // is_last
);

// Send via UDS client
// - With MessagePack: raw bytes (most efficient)
// - With JSON: falls back to base64
client.send_request_body_chunk_binary(&chunk).await?;
```

**Performance comparison (1KB body chunk):**

| Method | Encoding | Serialized Size |
|--------|----------|-----------------|
| `send_request_body_chunk` | JSON + base64 | ~1,450 bytes |
| `send_request_body_chunk_binary` | MessagePack | ~1,050 bytes |

---

## Reverse Connections

### Overview

Reverse connections allow agents to connect to the proxy instead of the proxy connecting to agents. This enables:

- Agents behind NAT/firewalls
- Dynamic agent scaling
- Cloud-native deployments
- Zero-config agent discovery

### Architecture

```
Agent                          Proxy
  │                              │
  │ ──── TCP/UDS Connect ───────►│
  │                              │
  │ ──── RegistrationRequest ──►│
  │      - agent_id              │
  │      - capabilities          │
  │      - auth_token            │
  │                              │
  │ ◄── RegistrationResponse ───│
  │      - accepted              │
  │      - config                │
  │                              │
  │   (bidirectional protocol)   │
  │                              │
```

### Listener Setup

```rust
use sentinel_agent_protocol::v2::{
    ReverseConnectionListener,
    ReverseConnectionConfig,
};

let config = ReverseConnectionConfig {
    handshake_timeout: Duration::from_secs(10),
    max_connections_per_agent: 4,
    require_auth: true,
    allowed_agents: Some(vec!["waf-*".to_string(), "auth-agent".to_string()]),
};

// UDS listener for local agents
let listener = ReverseConnectionListener::bind_uds(
    "/var/run/sentinel/agents.sock",
    config,
).await?;

// TCP listener for remote agents
let listener = ReverseConnectionListener::bind_tcp(
    "0.0.0.0:9090",
    config,
).await?;
```

See [Reverse Connections](reverse-connections/) for detailed setup instructions.

---

## V2Transport Abstraction

The `V2Transport` enum provides a unified interface across all transport types:

```rust
use sentinel_agent_protocol::v2::V2Transport;

pub enum V2Transport {
    Grpc(AgentClientV2),
    Uds(AgentClientV2Uds),
    Reverse(ReverseConnectionClient),
}

// All transports support the same operations
impl V2Transport {
    pub async fn send_request_headers(&mut self, headers: &RequestHeaders)
        -> Result<Decision, AgentProtocolError>;
    pub async fn send_request_body_chunk(&mut self, chunk: &RequestBodyChunk)
        -> Result<Decision, AgentProtocolError>;
    pub async fn cancel_request(&mut self, request_id: u64)
        -> Result<(), AgentProtocolError>;
    pub fn is_healthy(&self) -> bool;
}
```

---

## Choosing a Transport

| Scenario | Recommended Transport |
|----------|----------------------|
| Same host, lowest latency | UDS Binary |
| Remote agent, needs TLS | gRPC |
| Agent behind NAT/firewall | Reverse Connection |
| Cloud-native, dynamic scaling | Reverse Connection |
| Cross-language agent | gRPC |
| Simple local deployment | UDS Binary |
| Mixed environment | AgentPool (auto-detect) |

### Auto-Detection in AgentPool

```rust
let pool = AgentPool::new();

// Transport is auto-detected from endpoint format
pool.add_agent("local", "/var/run/agent.sock").await?;   // → UDS
pool.add_agent("remote", "waf.internal:50051").await?;   // → gRPC
pool.add_agent("https", "https://waf.example.com").await?; // → gRPC+TLS
```
